import contextlib
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import engine
import legacy_bridge as bridge
import solo

WALLET='4'+'1'*94
AUTHOR='8'+'1'*94
# major/minor varints, five-byte timestamp, previous hash and nonce.
BLOB=(bytes.fromhex('1010d286da8006')+bytes(32)+bytes(4)+bytes.fromhex('ab'*32+'01')).hex()
SEED='ab'*32

def template():
    return {'status':'OK','untrusted':False,'blockhashing_blob':BLOB,
            'blocktemplate_blob':BLOB+'1234567890','seed_hash':SEED,
            'difficulty':1,'difficulty_top64':0}

def config(wallet=WALLET,host='one.example'):
    return {'cpu':{'enabled':True,'rx/0':[-1]},'cuda':{'enabled':False},
            'opencl':{'enabled':False},'pools':[{'url':host+':443','user':wallet,'tls':True,'daemon':False}]}

class SoloTests(unittest.TestCase):
    def test_varints_headers_and_difficulty(self):
        t=solo.Template.parse(template())
        self.assertEqual(t.offset,39)
        self.assertEqual(bytes.fromhex(t.submit_blob(0x12345678))[39:43],bytes.fromhex('78563412'))
        self.assertEqual(t.job.target,1<<256)
        for values in [{'untrusted':True},{'difficulty':0},{'difficulty':-1},
                       {'difficulty_top64':2**64},{'blocktemplate_blob':'ff'+BLOB[2:]},
                       {'seed_hash':'00'}]:
            with self.subTest(values=values),self.assertRaises(ValueError):solo.Template.parse({**template(),**values})
        large=solo.Template.parse({**template(),'difficulty':1,'difficulty_top64':1})
        self.assertEqual(large.job.target,((1<<256)-1)//((1<<64)+1)+1)

    def test_real_randomx_solo_candidate_and_cleanup(self):
        rx=engine.RandomX();verify=engine.RandomX();stop=threading.Event();submitted=[]
        verify.prepare(bytes.fromhex(SEED));vm=verify.vm()
        class MockRpc:
            def call(self,method,params):
                if method=='get_block_template':return template()
                selftest.assertEqual(method,'submit_block')
                block=bytes.fromhex(params[0]);nonce=int.from_bytes(block[39:43],'little')
                current=solo.Template.parse(template())
                digest=verify.hash(vm,current.job.candidate(nonce))
                selftest.assertTrue(current.job.accepts(digest))
                selftest.assertEqual(block[:39],bytes.fromhex(BLOB)[:39])
                selftest.assertEqual(block[43:],bytes.fromhex(template()['blocktemplate_blob'])[43:])
                submitted.append(params[0]);stop.set();return {'status':'OK'}
        selftest=self
        try:solo.session(rx,'localhost',18081,WALLET,1,False,stop,MockRpc())
        finally:verify.lib.randomx_destroy_vm(vm);verify.close()
        self.assertEqual(len(submitted),1)
        self.assertIsNone(rx.cache)

class BridgeTests(unittest.TestCase):
    def test_cpu_cuda_config_and_explicit_opencl_rejection(self):
        parsed=bridge.Config.parse(config())
        self.assertEqual(parsed.wallet,WALLET)
        value=config();value['cuda']['enabled']=True
        self.assertTrue(bridge.Config.parse(value).cuda)
        value['cpu']['enabled']=False
        self.assertEqual(bridge.Config.parse(value).threads,0)
        value=config();value['opencl']['enabled']=True
        with self.assertRaisesRegex(ValueError,'not implemented'):bridge.Config.parse(value)

    def test_wallet_pool_reload_stops_before_start(self):
        stop=threading.Event();events=[];running=[];errors=[]
        class FakeMiner:
            def __init__(self,c):self.config=c;self.stop_event=threading.Event();self.accepted=self.rejected=0
            def stop(self):self.stop_event.set()
            def session(self,host,port,wallet,tls):
                if running:errors.append('old worker still alive')
                running.append(wallet);events.append(('start',host,wallet))
                self.stop_event.wait(5)
                running.remove(wallet);events.append(('stop',host,wallet))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'miner.json';path.write_text(json.dumps(config()))
            def run():
                try:bridge.run(path,stop,FakeMiner)
                except BaseException as exc:errors.append(exc)
            thread=threading.Thread(target=run);thread.start()
            try:
                for wallet,host in [(AUTHOR,'one.example'),(WALLET,'two.example')]:
                    deadline=time.monotonic()+3
                    while not running and time.monotonic()<deadline:time.sleep(.01)
                    before=len(events)
                    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(config(wallet,host)));temp.replace(path)
                    deadline=time.monotonic()+3
                    while len(events)<before+2 and time.monotonic()<deadline:time.sleep(.01)
                    self.assertGreaterEqual(len(events),before+2)
            finally:stop.set();thread.join(timeout=5)
        self.assertFalse(thread.is_alive());self.assertFalse(errors,errors)
        self.assertEqual(events,[('start','one.example',WALLET),('stop','one.example',WALLET),
                                 ('start','one.example',AUTHOR),('stop','one.example',AUTHOR),
                                 ('start','two.example',WALLET),('stop','two.example',WALLET)])

if __name__=='__main__':unittest.main(verbosity=2)
