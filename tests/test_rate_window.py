import dataclasses,time,unittest
from unittest.mock import patch
import engine

class RateWindowTests(unittest.TestCase):
    def test_frequent_jobs_do_not_reset_hashrate_window(self):
        template={'algo':'rx/0','job_id':'first','blob':'00'*76,'seed_hash':'ab'*32,'target':'01000000'}
        class Rx:
            seed=None;dataset=None
            def prepare(self,seed,*args):self.seed=seed
            def vm(self):return object()
            def hash(self,vm,data):time.sleep(.001);return b'\xff'*32
            def hash_batch(self,vm,job,nonces):return [self.hash(vm,job.candidate(n)) for n in nonces]
            def close(self):pass
            class lib:
                @staticmethod
                def randomx_destroy_vm(vm):pass
        class Wire:
            def __init__(self,*args):self.login=True;self.last=0;self.number=0
            def send(self,obj):pass
            def close(self):pass
            def receive(self):
                if self.login:
                    self.login=False;self.last=time.monotonic()
                    return {'id':1,'result':{'id':'test','job':template}}
                time.sleep(.005)
                if time.monotonic()-self.last>.03:
                    self.number+=1;self.last=time.monotonic()
                    return {'method':'job','params':{**template,'job_id':str(self.number)}}
                return None
        events=[];miner=engine.Miner(Rx());miner.report_interval=.08
        with patch.object(engine,'Wire',Wire),patch.object(engine,'event',side_effect=lambda kind,**kw:events.append((kind,kw))):
            miner.session('localhost',3333,'4'+'1'*94,False,.35)
        rates=[data['cpu_hs'] for kind,data in events if kind=='hashrate']
        self.assertGreaterEqual(len(rates),2)
        self.assertTrue(all(rate>0 for rate in rates),rates)

if __name__=='__main__':unittest.main()
