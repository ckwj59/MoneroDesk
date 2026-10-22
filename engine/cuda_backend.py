"""CUDA RandomX worker for the independent engine; no XMRig engine/plugins."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import queue
import threading
import engine

class CudaBackend:
    def __init__(self,root=None,batch=1024):
        root=Path(root) if root else engine.BASE
        path=root/'xmr-randomx-cuda.dll'
        manifest=json.loads((root/'cuda-manifest.json').read_text(encoding='utf-8'))
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['sha256']:
            raise ValueError('CUDA library integrity verification failed')
        if batch<32 or batch>1024 or batch%32:raise ValueError('Invalid CUDA batch')
        self.lib=C.CDLL(str(path.resolve()))
        self.lib.xmr_cuda_create.argtypes=[C.c_int,C.c_void_p,C.c_size_t,C.c_uint]
        self.lib.xmr_cuda_create.restype=C.c_void_p
        self.lib.xmr_cuda_hash.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t]
        self.lib.xmr_cuda_hash.restype=C.c_int
        self.lib.xmr_cuda_free.argtypes=[C.c_void_p]
        self.lib.xmr_cuda_cancel.argtypes=[C.c_void_p,C.c_int]
        self.lib.xmr_cuda_error.restype=C.c_char_p
        self.batch=batch;self.context=None;self.seed=None

    def prepare(self,rx):
        if self.context and self.seed==rx.seed:return
        self.close()
        if not rx.dataset:raise ValueError('CUDA requires the full RandomX dataset')
        rx.lib.randomx_get_dataset_memory.argtypes=[C.c_void_p]
        rx.lib.randomx_get_dataset_memory.restype=C.c_void_p
        self.context=self.lib.xmr_cuda_create(0,rx.lib.randomx_get_dataset_memory(rx.dataset),
                                             rx.lib.randomx_dataset_item_count()*64,self.batch)
        if not self.context:raise RuntimeError(self.lib.xmr_cuda_error().decode())
        self.seed=rx.seed

    def hashes(self,job,nonces):
        if len(nonces)!=self.batch:raise ValueError('CUDA nonce batch length mismatch')
        initial=b''.join(hashlib.blake2b(job.candidate(n),digest_size=64).digest() for n in nonces)
        source=C.create_string_buffer(initial);output=C.create_string_buffer(self.batch*32)
        status=self.lib.xmr_cuda_hash(self.context,source,len(initial),output,self.batch*32)
        if status==2:raise InterruptedError('GPU job cancelled')
        if not status:
            raise RuntimeError(self.lib.xmr_cuda_error().decode())
        raw=output.raw
        return [raw[i:i+32] for i in range(0,len(raw),32)]

    def close(self):
        if self.context:self.lib.xmr_cuda_free(self.context)
        self.context=self.seed=None

class HybridWorkers(engine.CpuWorkers):
    def __init__(self,rx,count,backend):
        super().__init__(rx,max(1,count))
        self.count=count;self.backend=backend;self.gpu_hashes=0

    def start(self,job):
        self.backend.prepare(self.rx)
        self.backend.lib.xmr_cuda_cancel(self.backend.context,0)
        super().start(job)
        def work():
            vm=None
            try:
                # Only verification of GPU candidates uses the CPU; CPU mining
                # can be disabled independently, and is reported separately.
                vm=self.rx.vm()
                checked=False
                while not self.stop_event.is_set():
                    nonces=self.next_batch(self.backend.batch)
                    if nonces is None or len(nonces)!=self.backend.batch:break
                    digests=self.backend.hashes(job,nonces)
                    if self.stop_event.is_set():break
                    if not checked:
                        if digests[0]!=self.rx.hash(vm,job.candidate(nonces[0])):
                            raise RuntimeError('GPU runtime hash self-check failed')
                        checked=True
                    with self.lock:self.gpu_hashes+=len(nonces)
                    for nonce,digest in zip(nonces,digests):
                        if job.accepts(digest):
                            if self.rx.hash(vm,job.candidate(nonce))!=digest:
                                raise RuntimeError('GPU candidate failed CPU verification; nothing submitted')
                            try:self.shares.put_nowait((nonce,digest))
                            except queue.Full:raise RuntimeError('Share queue overflow')
            except BaseException as exc:
                if not (isinstance(exc,InterruptedError) and self.stop_event.is_set()):self.errors.put(exc)
                self.stop_event.set()
            finally:
                if vm:self.rx.lib.randomx_destroy_vm(vm)
        thread=threading.Thread(target=work,name='XMR-CUDA-0')
        self.threads.append(thread);thread.start()

    def stop(self):
        self.stop_event.set()
        if self.backend.context:self.backend.lib.xmr_cuda_cancel(self.backend.context,1)
        super().stop()
