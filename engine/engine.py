"""Independent experimental CPU miner. No XMRig subprocess or source imports.

Protocol/controller code is original to this project. RandomX is a separately
licensed upstream algorithm library. Only explicit rx/0 pool jobs are supported.
"""
from __future__ import annotations

import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import secrets
import socket
import ssl
import sys
import threading
import time
from dataclasses import dataclass
from collections import deque

BASE = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
MAX_MESSAGE = 65536
POLL_INTERVAL = 0.05
NONCE_OFFSET = 39


def event(kind, **values):
    print(json.dumps({'event': kind, **values}, ensure_ascii=False), flush=True)


def decode_hex(value, name, lengths=None):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[0-9a-fA-F]{2})+', value):
        raise ValueError(f'{name}: invalid hexadecimal string')
    data = bytes.fromhex(value)
    if lengths and len(data) not in lengths:
        raise ValueError(f'{name}: unsupported size')
    return data


@dataclass(frozen=True)
class Job:
    id: str
    blob: bytes
    seed: bytes
    target: int

    @classmethod
    def parse(cls, obj):
        if not isinstance(obj, dict) or obj.get('algo') != 'rx/0':
            raise ValueError('Only explicitly identified rx/0 jobs are supported')
        ident = obj.get('job_id')
        if not isinstance(ident, str) or not 1 <= len(ident) <= 256:
            raise ValueError('Missing or invalid job_id')
        blob = decode_hex(obj.get('blob'), 'blob')
        if not 43 <= len(blob) <= 512:
            raise ValueError('Unsupported Monero hashing blob length')
        # Standard Monero pool jobs put the four-byte nonce at offset 39.
        # Reject proxy/NiceHash extension layouts rather than overwriting them.
        if obj.get('nicehash') or obj.get('nonce_offset', NONCE_OFFSET) != NONCE_OFFSET:
            raise ValueError('Unsupported nonce layout')
        seed = decode_hex(obj.get('seed_hash'), 'seed_hash', (32,))
        target = decode_hex(obj.get('target'), 'target', (4, 8))
        compact = int.from_bytes(target, 'little')
        if compact == 0:
            raise ValueError('Zero share target')
        # Conservative full-width target: rounding can discard a boundary share,
        # but cannot admit a hash above the advertised compact threshold.
        full_target = compact << (256 - 8 * len(target))
        return cls(ident, blob, seed, full_target)

    def candidate(self, nonce):
        if not 0 <= nonce < 2**32:
            raise ValueError('Nonce outside uint32 range')
        return self.blob[:NONCE_OFFSET] + nonce.to_bytes(4, 'little') + self.blob[NONCE_OFFSET+4:]

    def accepts(self, digest):
        return len(digest) == 32 and int.from_bytes(digest, 'little') < self.target


class RandomX:
    """One shared immutable cache/dataset, one VM per worker. Native calls release GIL."""
    def __init__(self, path=None):
        path = Path(path or BASE / ('randomx.dll' if os.name == 'nt' else 'librandomx.so')).resolve()
        manifest_path = path.parent / 'randomx-manifest.json'
        metadata = json.loads(manifest_path.read_text(encoding='utf-8'))
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata['sha256']:
            raise ValueError('RandomX library integrity check failed')
        self.lib = C.CDLL(str(path))
        signatures = {
            'randomx_get_flags': (C.c_uint, []),
            'randomx_alloc_cache': (C.c_void_p, [C.c_uint]),
            'randomx_init_cache': (None, [C.c_void_p, C.c_void_p, C.c_size_t]),
            'randomx_release_cache': (None, [C.c_void_p]),
            'randomx_alloc_dataset': (C.c_void_p, [C.c_uint]),
            'randomx_dataset_item_count': (C.c_ulong, []),
            'randomx_init_dataset': (None, [C.c_void_p, C.c_void_p, C.c_ulong, C.c_ulong]),
            'randomx_release_dataset': (None, [C.c_void_p]),
            'randomx_create_vm': (C.c_void_p, [C.c_uint, C.c_void_p, C.c_void_p]),
            'randomx_destroy_vm': (None, [C.c_void_p]),
            'randomx_calculate_hash': (None, [C.c_void_p, C.c_void_p, C.c_size_t, C.c_void_p]),
        }
        for name, (result, args) in signatures.items():
            fn = getattr(self.lib, name)
            fn.restype, fn.argtypes = result, args
        # Base flags exclude V2; large-page allocation is attempted separately.
        self.flags = self.lib.randomx_get_flags() & (2 | 8 | 32 | 64)
        self.cache = self.dataset = None
        self.seed = None
        self.large_pages = False
        self.batch_lib = None
        batch_path=path.parent/'xmr-cpu-batch.dll'
        if batch_path.exists():
            meta=json.loads((path.parent/'cpu-manifest.json').read_text(encoding='utf-8'))
            if hashlib.sha256(batch_path.read_bytes()).hexdigest()!=meta['sha256']:
                raise ValueError('CPU batch library integrity check failed')
            self.batch_lib=C.CDLL(str(batch_path))
            self.batch_lib.xmr_cpu_batch.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t,C.c_void_p,C.c_size_t]
            self.batch_lib.xmr_cpu_batch.restype=C.c_int

    @staticmethod
    def enable_large_pages():
        if os.name!='nt':return True
        from ctypes import wintypes as W
        class Luid(C.Structure):_fields_=[('low',W.DWORD),('high',W.LONG)]
        class Privileges(C.Structure):_fields_=[('count',W.DWORD),('luid',Luid),('attributes',W.DWORD)]
        adv=C.WinDLL('advapi32',use_last_error=True);kernel=C.WinDLL('kernel32',use_last_error=True)
        adv.OpenProcessToken.argtypes=[W.HANDLE,W.DWORD,C.POINTER(W.HANDLE)]
        adv.LookupPrivilegeValueW.argtypes=[W.LPCWSTR,W.LPCWSTR,C.POINTER(Luid)]
        adv.AdjustTokenPrivileges.argtypes=[W.HANDLE,W.BOOL,C.POINTER(Privileges),W.DWORD,C.c_void_p,C.c_void_p]
        kernel.GetCurrentProcess.restype=W.HANDLE;kernel.CloseHandle.argtypes=[W.HANDLE]
        token=W.HANDLE()
        if not adv.OpenProcessToken(kernel.GetCurrentProcess(),0x28,C.byref(token)):return False
        try:
            privileges=Privileges();privileges.count=1;privileges.attributes=2
            if not adv.LookupPrivilegeValueW(None,'SeLockMemoryPrivilege',C.byref(privileges.luid)):return False
            C.set_last_error(0)
            return bool(adv.AdjustTokenPrivileges(token,False,C.byref(privileges),0,None,None) and C.get_last_error()==0)
        finally:kernel.CloseHandle(token)

    def prepare(self, seed, fast=False, cancelled=lambda: False):
        if seed == self.seed and bool(self.dataset) == fast:
            return
        self.close()
        started=time.monotonic()
        allow_large=self.enable_large_pages()
        cache_flags=self.flags & (8 | 32 | 64)
        self.cache = self.lib.randomx_alloc_cache(cache_flags|1) if allow_large else None
        if not self.cache:self.cache=self.lib.randomx_alloc_cache(cache_flags)
        if not self.cache:
            raise MemoryError('RandomX cache allocation failed')
        try:
            key = C.create_string_buffer(seed)
            self.lib.randomx_init_cache(self.cache, key, len(seed))
            if cancelled():
                raise InterruptedError('Stopped during cache preparation')
            if fast:
                self.dataset = self.lib.randomx_alloc_dataset(1) if allow_large else None
                self.large_pages=bool(self.dataset)
                if not self.dataset:self.dataset=self.lib.randomx_alloc_dataset(0)
                if not self.dataset:
                    raise MemoryError('RandomX dataset allocation failed (~2.1 GiB required)')
                total = self.lib.randomx_dataset_item_count()
                from concurrent.futures import ThreadPoolExecutor
                chunk=262144;progress=0;lock=threading.Lock();last_percent=-10
                def initialize(first):
                    nonlocal progress,last_percent
                    if cancelled():raise InterruptedError('Stopped during dataset preparation')
                    amount=min(chunk,total-first)
                    self.lib.randomx_init_dataset(self.dataset,self.cache,first,amount)
                    with lock:
                        progress+=amount;percent=round(100*progress/total)
                        if percent>=last_percent+10:
                            last_percent=percent;event('preparing',percent=percent)
                with ThreadPoolExecutor(max_workers=min(8,os.cpu_count() or 1)) as pool:
                    for _ in pool.map(initialize,range(0,total,chunk)):pass
            self.seed = seed
            event('prepared',seconds=round(time.monotonic()-started,2),dataset_large_pages=self.large_pages,
                  native_batches=bool(self.batch_lib))
        except BaseException:
            self.close()
            raise

    def vm(self):
        if not self.cache:
            raise RuntimeError('RandomX cache is not prepared')
        flags=self.flags | (4 if self.dataset else 0)
        # Large-page dataset allocation and large-page VM scratchpads are
        # independent RandomX allocations. Always try the latter; the previous
        # dataset-only gate silently disabled scratchpad large pages whenever
        # the ~2 GiB dataset fell back to ordinary pages.
        vm=self.lib.randomx_create_vm(flags|1,self.cache,self.dataset)
        if not vm:vm = self.lib.randomx_create_vm(flags, self.cache, self.dataset)
        if not vm:
            raise MemoryError('RandomX worker VM allocation failed')
        return vm

    def hash(self, vm, data):
        source = C.create_string_buffer(data)
        result = C.create_string_buffer(32)
        self.lib.randomx_calculate_hash(vm, source, len(data), result)
        return result.raw

    def hash_batch(self,vm,job,nonces):
        if not self.batch_lib:return [self.hash(vm,job.candidate(n)) for n in nonces]
        source=C.create_string_buffer(job.blob);ids=(C.c_uint32*len(nonces))(*nonces)
        output=C.create_string_buffer(len(nonces)*32)
        if not self.batch_lib.xmr_cpu_batch(vm,source,len(job.blob),ids,len(nonces),output,len(nonces)*32):
            raise RuntimeError('Native CPU batch failed')
        raw=output.raw
        return [raw[i:i+32] for i in range(0,len(raw),32)]

    def close(self):
        # Caller must join all workers before freeing shared memory.
        if self.dataset:
            self.lib.randomx_release_dataset(self.dataset)
            self.dataset = None
        if self.cache:
            self.lib.randomx_release_cache(self.cache)
            self.cache = None
        self.large_pages=False
        self.seed = None


class CpuWorkers:
    def __init__(self, rx, count):
        if not 1 <= count <= (os.cpu_count() or 1):
            raise ValueError('Thread count exceeds detected logical CPUs')
        self.rx, self.count = rx, count
        self.stop_event = threading.Event()
        self.shares = queue.Queue(maxsize=128)
        self.errors = queue.Queue()
        self.lock = threading.Lock()
        self.threads = []
        self.hashes = self.used = 0
        self.origin = secrets.randbits(32)
        # Larger native batches reduce Python/lock hand-offs around RandomX.
        # On Windows, prefer one logical CPU per physical core before placing
        # remaining workers on SMT siblings. Pinning every logical CPU showed
        # no benefit in local tests, so full-thread runs remain scheduler-managed.
        self.batch_size=max(32,min(256,count*8))
        self.affinity=None
        if os.name=='nt' and count < (os.cpu_count() or 1):
            try:
                from cpu_topology import cpu_order
                order=cpu_order()
                if len(order)>=count:
                    self.affinity=order[:count]
            except (OSError, AttributeError, ImportError):
                pass

    def next_batch(self,requested=32):
        with self.lock:
            if self.used >= 2**32:
                return None
            amount = min(requested, 2**32-self.used)
            start = self.used
            self.used += amount
        return [(self.origin + n) & 0xffffffff for n in range(start, start+amount)]

    def start(self, job):
        def work(index):
            vm = None
            try:
                if self.affinity and index<len(self.affinity):
                    try:
                        from cpu_topology import pin_current
                        pin_current(self.affinity[index])
                    except (OSError, AttributeError, ImportError):
                        pass  # Affinity is only a hint; never fail mining over it.
                vm = self.rx.vm()
                while not self.stop_event.is_set():
                    nonces = self.next_batch(self.batch_size)
                    if nonces is None:
                        break
                    digests=self.rx.hash_batch(vm,job,nonces)
                    with self.lock:self.hashes+=len(nonces)
                    for nonce,digest in zip(nonces,digests):
                        if self.stop_event.is_set():
                            break
                        if job.accepts(digest):
                            try:
                                self.shares.put_nowait((nonce, digest))
                            except queue.Full:
                                # Never block worker shutdown on a slow pool.
                                self.errors.put(RuntimeError('Share queue overflow; stopping session'))
                                self.stop_event.set()
            except BaseException as exc:
                self.errors.put(exc)
                self.stop_event.set()
            finally:
                if vm:
                    self.rx.lib.randomx_destroy_vm(vm)
        self.threads = [threading.Thread(target=work,args=(i,),name=f'XMR-CPU-{i}') for i in range(self.count)]
        for thread in self.threads:
            thread.start()

    def stop(self):
        self.stop_event.set()
        for thread in self.threads:
            thread.join()
        self.threads.clear()


class Wire:
    def __init__(self, host, port, tls=True):
        connect_started=time.monotonic()
        if tls:
            from tls_transport import open_tls_socket
            self.sock = open_tls_socket(host, port, timeout=12,
                on_progress=lambda stage,**values:event('connection_phase',stage=stage,**values))
            event('tls_verified',host=host,version=self.sock.version(),cipher=self.sock.cipher()[0],
                    port=getattr(self.sock,'xmr_pool_port',self.sock.getpeername()[1]),
                    address=getattr(self.sock,'xmr_pool_address',self.sock.getpeername()[0]),requested_port=port,
                    route=getattr(self.sock,'xmr_route','direct'),
                  certificate_sha256=hashlib.sha256(self.sock.getpeercert(binary_form=True)).hexdigest(),
                  connect_seconds=round(time.monotonic()-connect_started,3))
        else:
            if host.lower() not in ('127.0.0.1','localhost','::1'):
                raise ValueError('Remote mining requires verified TLS; plaintext is allowed only for loopback tests')
            self.sock = socket.create_connection((host, port), timeout=12)
        self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
        self.sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        self.sock.settimeout(POLL_INTERVAL)
        self.buffer = bytearray()

    def send(self, obj):
        data = json.dumps(obj, separators=(',', ':'), allow_nan=False).encode() + b'\n'
        if len(data) > MAX_MESSAGE:
            raise ValueError('Outbound message too large')
        # Only the session thread writes; no interleaved JSON from workers.
        self.sock.settimeout(10)
        try:
            self.sock.sendall(data)
        finally:
            self.sock.settimeout(POLL_INTERVAL)

    def receive(self):
        if len(self.buffer) > MAX_MESSAGE:
            raise ValueError('Pool message exceeds 64 KiB')
        if b'\n' not in self.buffer:
            try:
                data = self.sock.recv(4096)
            except socket.timeout:
                return None
            if not data:
                raise ConnectionError('Pool closed the connection')
            self.buffer.extend(data)
        if len(self.buffer) > MAX_MESSAGE:
            raise ValueError('Pool message exceeds 64 KiB')
        if b'\n' not in self.buffer:
            return None
        line, _, rest = self.buffer.partition(b'\n')
        self.buffer = bytearray(rest)
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError('Pool message must be a JSON object')
        return obj

    def close(self):
        self.sock.close()


class Miner:
    def __init__(self, rx, threads=1, fast=False):
        self.rx, self.threads, self.fast = rx, threads, fast
        self.stop_event = threading.Event()
        self.workers = None
        self.accepted = self.rejected = 0
        self.retain_context = False
        self.report_interval = 1
        self.worker_factory = CpuWorkers
        self.login_difficulty = None
        self.reconnect_initial = 2
        self.reconnect_max = 60
        self.successful_login = False
        self.session_progress = False

    def stop(self):
        self.stop_event.set()

    def session(self, host, port, wallet, tls=True, max_seconds=None):
        started=time.monotonic()
        retain=self.retain_context
        failures=0
        # The shared seed dataset remains immutable across transient network
        # failures. Stop/join the old workers before starting a new session.
        self.retain_context=True
        try:
            while not self.stop_event.is_set():
                remaining=None if max_seconds is None else max_seconds-(time.monotonic()-started)
                if remaining is not None and remaining<=0:return
                self.successful_login=self.session_progress=False
                try:
                    return self._session_once(host,port,wallet,tls,remaining)
                except (ssl.SSLCertVerificationError,PermissionError):raise
                except OSError as exc:
                    if not tls:raise
                    if self.stop_event.is_set():return
                    if self.session_progress:failures=0
                    failures+=1
                    delay=min(self.reconnect_max,self.reconnect_initial*2**min(failures-1,6))
                    # Small jitter prevents synchronized restart loops; the
                    # total wait is capped and immediately cancellable.
                    delay=min(self.reconnect_max,delay*(1+secrets.randbelow(101)/1000))
                    if max_seconds is not None:
                        delay=min(delay,max(0,max_seconds-(time.monotonic()-started)))
                    event('reconnecting',host=host,attempt=failures,delay_seconds=round(delay,2),reason=str(exc))
                    if self.stop_event.wait(delay):return
        finally:
            self.retain_context=retain
            if not retain:self.rx.close()

    def _session_once(self, host, port, wallet, tls=True, max_seconds=None):
        if not re.fullmatch(r'[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{95}', wallet):
            raise ValueError('Enter a 95-character standard/subaddress Monero payout address')
        # Retry only pre-login transient transport failures. Never repeat an
        # authentication failure or trust a replacement certificate.
        for attempt in range(2):
            if self.stop_event.is_set():raise InterruptedError('Connection cancelled')
            try:
                wire = Wire(host, port, tls)
                break
            except ssl.SSLCertVerificationError:raise
            except OSError as exc:
                if not tls or attempt==1:raise
                event('connection_retry',host=host,attempt=attempt+2,delay_seconds=1,
                      reason=str(exc))
                if self.stop_event.wait(1):raise InterruptedError('Connection cancelled')
        sequence = 1
        pending = {}
        session_id = None
        heartbeat_id = None
        heartbeat_sent = 0
        heartbeat_warned = False
        keepalive = host.lower().rstrip('.')=='gulf.moneroocean.stream'
        last_heartbeat = time.monotonic()
        job = None
        last_rx = started = last_rate = time.monotonic()
        previous_hashes = 0
        completed_hashes = 0
        completed_gpu_hashes = previous_gpu_hashes = 0
        rate_samples=deque()
        login=wallet
        if self.login_difficulty is not None:
            if host!='gulf.moneroocean.stream' or type(self.login_difficulty) is not int or not 1<=self.login_difficulty<=10**9:
                raise ValueError('Unsupported fixed difficulty request')
            login+='+'+str(self.login_difficulty)
        try:
            wire.send({'id': 1, 'jsonrpc': '2.0', 'method': 'login', 'params': {
                'login': login, 'pass': 'x', 'agent': 'XMR-Independent/0.2', 'algo': ['rx/0']}})
        except BaseException:
            wire.close()
            raise
        event('connecting', host=host, tls=tls, threads=self.threads)
        try:
            while not self.stop_event.is_set():
                now = time.monotonic()
                if max_seconds is not None and now-started >= max_seconds:
                    break
                if session_id is None and now-started>20:
                    raise TimeoutError('Pool login response timed out')
                if now-last_rx > 120:
                    raise TimeoutError('No pool messages for 120 seconds')
                message = wire.receive()
                if message is not None:
                    last_rx = time.monotonic()
                    new_job = None
                    if message.get('id') == 1:
                        result = message.get('result')
                        if message.get('error') or not isinstance(result, dict):
                            raise PermissionError(f'Pool login failed: {message.get("error")}')
                        session_id = result.get('id')
                        if not isinstance(session_id, str) or not 1 <= len(session_id) <= 256:
                            raise ValueError('Invalid mining session id')
                        self.successful_login=True
                        if result.get('extensions') and 'nicehash' in result['extensions']:
                            raise ValueError('NiceHash nonce layout is not supported')
                        if 'keepalive' in (result.get('extensions') or []):keepalive=True
                        new_job = result.get('job')
                    elif heartbeat_id is not None and message.get('id')==heartbeat_id:
                        result=message.get('result')
                        if message.get('error') or not isinstance(result,dict) or result.get('status') not in ('KEEPALIVED','OK'):
                            raise ConnectionError('Pool keepalive failed')
                        heartbeat_id=None
                        self.session_progress=True
                        event('keepalive',status='OK')
                    elif message.get('method') == 'job':
                        if session_id is None:
                            raise ValueError('Job arrived before successful login')
                        new_job = message.get('params')
                    elif message.get('id') in pending:
                        pending.pop(message['id'])
                        result = message.get('result')
                        accepted = not message.get('error') and isinstance(result, dict) and result.get('status') == 'OK'
                        if accepted:
                            self.accepted += 1
                            self.session_progress=True
                        else:
                            self.rejected += 1
                        event('share', accepted=accepted, total_accepted=self.accepted,
                              total_rejected=self.rejected, error=message.get('error'))
                        if message.get('error') and any(word in str(message['error']).lower() for word in ('banned','blocked')):
                            raise PermissionError(f'Pool access restricted: {message["error"]}')
                    if new_job is not None:
                        incoming = Job.parse(new_job)
                        if incoming != job:
                            # No stale VMs or shares survive a job/seed transition.
                            if self.workers:
                                self.workers.stop()
                                completed_hashes += self.workers.hashes
                                completed_gpu_hashes += getattr(self.workers,'gpu_hashes',0)
                            self.workers = None
                            if self.rx.seed != incoming.seed or bool(self.rx.dataset) != self.fast:
                                event('preparing', percent=0)
                            self.rx.prepare(incoming.seed, self.fast, self.stop_event.is_set)
                            if self.stop_event.is_set():
                                break
                            first_job = job is None
                            job = incoming
                            self.workers = self.worker_factory(self.rx, self.threads)
                            self.workers.start(job)
                            if first_job:
                                last_rate = time.monotonic()
                                rate_samples.append((last_rate,0,0))
                            event('job', job_id=job.id, mode='fast' if self.fast else 'light',difficulty=round(2**256/job.target,2))
                            if not first_job:self.session_progress=True
                if self.workers:
                    if not self.workers.errors.empty():
                        raise self.workers.errors.get()
                    while not self.workers.shares.empty():
                        nonce, digest = self.workers.shares.get_nowait()
                        if len(pending) >= 128:
                            raise ConnectionError('Too many unacknowledged shares')
                        sequence += 1
                        wire.send({'id': sequence, 'jsonrpc': '2.0', 'method': 'submit', 'params': {
                            'id': session_id, 'job_id': job.id, 'nonce': nonce.to_bytes(4, 'little').hex(),
                            'result': digest.hex()}})
                        pending[sequence] = time.monotonic()
                    if time.monotonic()-last_rate >= self.report_interval:
                        current = completed_hashes + self.workers.hashes
                        current_gpu = completed_gpu_hashes + getattr(self.workers,'gpu_hashes',0)
                        sampled=time.monotonic()
                        rate_samples.append((sampled,current,current_gpu))
                        while len(rate_samples)>2 and rate_samples[1][0]<=sampled-10:
                            rate_samples.popleft()
                        first,cpu_start,gpu_start=rate_samples[0]
                        window=max(sampled-first,.001)
                        event('hashrate', cpu_hs=round((current-cpu_start)/window, 2),
                              gpu_hs=round((current_gpu-gpu_start)/window,2),
                              window_seconds=round(window,3),refresh_seconds=self.report_interval,
                              accepted=self.accepted, rejected=self.rejected)
                        previous_gpu_hashes = current_gpu
                        previous_hashes, last_rate = current, time.monotonic()
                if pending and time.monotonic()-min(pending.values()) > 60:
                    raise TimeoutError('Pool did not acknowledge a submitted share')
                now=time.monotonic()
                if heartbeat_id is not None and now-heartbeat_sent>30:
                    if not heartbeat_warned:
                        event('connection_warning',reason='Keepalive reply delayed; monitoring pool traffic',
                              idle_seconds=round(now-last_rx,1))
                        heartbeat_warned=True
                    # A missing optional RPC response alone is not proof that
                    # the transport is dead. New jobs and share replies count
                    # as activity; the 120-second receive deadline still
                    # detects a silent connection and triggers recovery.
                    if now-last_rx<90:
                        heartbeat_id=None
                        last_heartbeat=now
                if keepalive and session_id and heartbeat_id is None and now-last_heartbeat>=30:
                    sequence+=1
                    wire.send({'id':sequence,'jsonrpc':'2.0','method':'keepalived','params':{'id':session_id}})
                    heartbeat_id=sequence
                    heartbeat_warned=False
                    heartbeat_sent=last_heartbeat=time.monotonic()
        finally:
            if self.workers:
                self.workers.stop()
                self.workers = None
            wire.close()
            if pending:event('unconfirmed_shares',count=len(pending),replayed=False)
            if not self.retain_context:
                self.rx.close()
            event('stopped', accepted=self.accepted, rejected=self.rejected)


def self_test(fast=False):
    vectors = [
        (b'This is a test', '639183aae1bf4c9a35884cb46b09cad9175f04efd7684e7262a0ac1c2f0b4e3f'),
        (b'Lorem ipsum dolor sit amet', '300a0adb47603dedb42228ccb2b211104f4da45af709cd7547cd049e9489c969'),
    ]
    rx = RandomX()
    vm = None
    try:
        rx.prepare(b'test key 000', fast)
        vm = rx.vm()
        for data, expected in vectors:
            actual = rx.hash(vm, data).hex()
            if actual != expected:
                raise RuntimeError(f'RandomX known-answer test failed: {actual}')
        event('self_test', passed=True, vectors=len(vectors), mode='fast' if fast else 'light')
    finally:
        if vm:
            rx.lib.randomx_destroy_vm(vm)
        rx.close()


def main():
    parser = argparse.ArgumentParser(description='XMR independent CPU engine — experimental; no XMRig')
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--host')
    parser.add_argument('--port', type=int, default=443)
    parser.add_argument('--wallet')
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--fast', action='store_true', help='Allocate full ~2.1 GiB dataset')
    parser.add_argument('--plain', action='store_true', help='Explicitly use unencrypted Stratum')
    parser.add_argument('--seconds', type=int)
    args = parser.parse_args()
    if args.self_test:
        self_test(args.fast)
        return
    if not args.host or not args.wallet or not 1 <= args.port <= 65535:
        parser.error('--host and --wallet are required; port must be valid')
    if not 1 <= args.threads <= (os.cpu_count() or 1):
        parser.error('--threads exceeds detected logical CPU count')
    if args.seconds is not None and args.seconds <= 0:
        parser.error('--seconds must be positive')
    miner = Miner(RandomX(), args.threads, args.fast)
    # Control pipe accepts a single explicit stop command; no code evaluation.
    def controls():
        for line in sys.stdin:
            if line.strip() == 'stop':
                miner.stop()
                break
    threading.Thread(target=controls, daemon=True).start()
    try:
        miner.session(args.host, args.port, args.wallet, not args.plain, args.seconds)
    except KeyboardInterrupt:
        miner.stop()
    except InterruptedError:
        pass
    except Exception as exc:
        event('error', message=str(exc))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
