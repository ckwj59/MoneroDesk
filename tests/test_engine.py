import json
import os
import socket
import threading
import unittest
from unittest.mock import patch
import engine

WALLET='4'+'1'*94
BLOB='0b0b98bea7e805e0010a2126d287a2a0cc833d312cb786385a7c2f9de69d25537f584a9bc9977b00000000666fd8753bf61a8631f12984e3fd44f4014eca629276817b56f32e9b68bd82f416'
SEED=(b'test key 000'+bytes(20)).hex()
def job(ident='test', seed=SEED):
    return dict(algo='rx/0',job_id=ident,blob=BLOB,seed_hash=seed,target='ffffffff')

class ProtocolTests(unittest.TestCase):
    def test_job_rejects_untrusted_fields(self):
        for field,value in [('algo','rx/wow'),('algo',None),('seed_hash','00'),('target','00000000'),
                            ('blob','ab'),('job_id',''),('nonce_offset',40),('nicehash',True)]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                engine.Job.parse({**job(),field:value})

    def test_nonce_and_target_boundary(self):
        j=engine.Job.parse(job())
        changed=j.candidate(0x12345678)
        self.assertEqual(changed[39:43],bytes.fromhex('78563412'))
        self.assertEqual(changed[:39],j.blob[:39])
        self.assertEqual(changed[43:],j.blob[43:])
        self.assertTrue(j.accepts((j.target-1).to_bytes(32,'little')))
        self.assertFalse(j.accepts(j.target.to_bytes(32,'little')))
        with self.assertRaises(ValueError):j.candidate(2**32)

    def test_nonce_partitions_never_overlap_at_wrap(self):
        workers=engine.CpuWorkers(None,1)
        workers.origin=2**32-10
        nonces=workers.next_batch()+workers.next_batch()
        self.assertEqual(len(set(nonces)),64)
        workers.used=2**32-2
        self.assertEqual(len(workers.next_batch()),2)
        self.assertIsNone(workers.next_batch())

    def test_wire_fragmentation_and_size_limit(self):
        first,second=socket.socketpair()
        wire=engine.Wire.__new__(engine.Wire);wire.sock=first;wire.buffer=bytearray()
        first.settimeout(.02)
        try:
            second.sendall(b'{"id":')
            self.assertIsNone(wire.receive())
            second.sendall(b'1}\n{"id":2}\n')
            self.assertEqual(wire.receive()['id'],1)
            self.assertEqual(wire.receive()['id'],2)
            wire.buffer=bytearray(b'x'*(engine.MAX_MESSAGE+1))
            with self.assertRaises(ValueError):wire.receive()
        finally:first.close();second.close()


class NativeIntegrationTests(unittest.TestCase):
    def test_vm_tries_large_page_scratchpad_then_falls_back(self):
        rx=engine.RandomX.__new__(engine.RandomX)
        rx.flags=10;rx.cache=object();rx.dataset=None
        rx.lib=type('Lib',(),{})()
        calls=[]
        def create(flags,cache,dataset):
            calls.append(flags)
            return None if len(calls)==1 else 123
        rx.lib.randomx_create_vm=create
        self.assertEqual(rx.vm(),123)
        self.assertEqual(calls,[11,10])

    def test_upstream_known_answers(self):
        engine.self_test()

    def test_real_hash_submission_job_and_seed_switch(self):
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(30)
        rx=engine.RandomX();miner=engine.Miner(rx,1,False)
        server_errors=[];received=[]
        def server():
            try:
                conn,_=listener.accept()
                with conn:
                    conn.settimeout(60)
                    stream=conn.makefile('rwb',buffering=0)
                    login=json.loads(stream.readline())
                    self.assertEqual(login['method'],'login')
                    stream.write((json.dumps({'id':1,'result':{'id':'session-test','job':job()}})+'\n').encode())
                    verifier=engine.RandomX();vm=None
                    try:
                        verifier.prepare(bytes.fromhex(SEED));vm=verifier.vm()
                        while len(received)<3:
                            msg=json.loads(stream.readline())
                            self.assertEqual(msg['method'],'submit')
                            params=msg['params'];current=engine.Job.parse(job('seed-next' if len(received)>1 else ('next' if len(received)>0 else 'test'), ('ab'*32) if len(received)>1 else SEED))
                            if params['job_id']!=current.id:
                                # Already in-flight old shares may be acknowledged, but no
                                # old work is accepted as proof of the new generation.
                                stream.write((json.dumps({'id':msg['id'],'result':{'status':'OK'}})+'\n').encode());continue
                            digest=verifier.hash(vm,current.blob[:39]+bytes.fromhex(params['nonce'])+current.blob[43:])
                            self.assertEqual(digest.hex(),params['result'])
                            self.assertTrue(current.accepts(digest))
                            received.append(params)
                            stream.write((json.dumps({'id':msg['id'],'result':{'status':'OK'}})+'\n').encode())
                            if len(received)==1:
                                stream.write((json.dumps({'method':'job','params':job('next')})+'\n').encode())
                            elif len(received)==2:
                                verifier.lib.randomx_destroy_vm(vm);vm=None
                                verifier.prepare(bytes.fromhex('ab'*32));vm=verifier.vm()
                                stream.write((json.dumps({'method':'job','params':job('seed-next','ab'*32)})+'\n').encode())
                            else:
                                miner.stop()
                    finally:
                        if vm:verifier.lib.randomx_destroy_vm(vm)
                        verifier.close()
            except BaseException as exc:
                server_errors.append(exc);miner.stop()
            finally:listener.close()
        thread=threading.Thread(target=server);thread.start()
        try:miner.session('127.0.0.1',listener.getsockname()[1],WALLET,False,90)
        except InterruptedError:
            if server_errors:raise server_errors[0]
            raise
        finally:miner.stop();thread.join(timeout=65)
        self.assertFalse(thread.is_alive())
        if server_errors:raise server_errors[0]
        self.assertEqual(len(received),3)
        self.assertIsNone(rx.cache)
        self.assertIsNone(miner.workers)

if __name__=='__main__':unittest.main(verbosity=2)
