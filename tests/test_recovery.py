import queue,unittest
from unittest.mock import patch
import engine

WALLET='4'+'1'*94
JOB={'algo':'rx/0','job_id':'job1','blob':'00'*76,'seed_hash':'ab'*32,'target':'01000000'}

class Rx:
    seed=None
    dataset=None
    def __init__(self):self.prepares=0;self.closes=0
    def prepare(self,seed,*args):
        if self.seed==seed and self.dataset:return
        self.seed=seed;self.dataset=True;self.prepares+=1
    def close(self):self.closes+=1

class Workers:
    def __init__(self,*args):
        self.hashes=0;self.shares=queue.Queue();self.errors=queue.Queue();self.stopped=False
    def start(self,job):pass
    def stop(self):self.stopped=True

class RecoveryTests(unittest.TestCase):
    def test_delayed_keepalive_does_not_stop_active_job_stream(self):
        rx=Rx();miner=engine.Miner(rx,1,True);miner.worker_factory=Workers
        clock=[0];sent=[];events=[]
        class Wire:
            def __init__(self,*args):self.first=True
            def send(self,message):sent.append(message)
            def close(self):pass
            def receive(self):
                clock[0]+=10
                if self.first:
                    self.first=False
                    return {'id':1,'result':{'id':'session','job':JOB}}
                return {'method':'job','params':JOB}
        with patch.object(engine,'Wire',Wire),patch.object(engine.time,'monotonic',side_effect=lambda:clock[0]),patch.object(engine,'event',side_effect=lambda kind,**kw:events.append(kind)):
            miner.session('gulf.moneroocean.stream',20128,WALLET,True,150)
        self.assertIn('connection_warning',events)
        self.assertNotIn('reconnecting',events)
        self.assertEqual((miner.accepted,miner.rejected),(0,0))
        self.assertTrue(any(m['method']=='keepalived' for m in sent))
        self.assertEqual(rx.closes,1)

    def test_silent_connection_recovers_and_reuses_seed_dataset(self):
        rx=Rx();miner=engine.Miner(rx,1,True);workers=[];connections=[];clock=[0];events=[]
        def factory(*args):
            w=Workers();workers.append(w);return w
        miner.worker_factory=factory
        class Wire:
            def __init__(self,*args):
                if connections:self.assert_stopped()
                self.index=len(connections);connections.append(self);self.first=True
            def assert_stopped(self):
                assert workers[-1].stopped,'old worker survived reconnect'
            def send(self,message):pass
            def close(self):pass
            def receive(self):
                clock[0]+=10
                if self.first:
                    self.first=False
                    return {'id':1,'result':{'id':'session'+str(self.index),'job':JOB}}
                if self.index==1:miner.stop()
                return None
        def event(kind,**values):events.append(kind)
        def wait(delay):clock[0]+=delay;return False
        with patch.object(engine,'Wire',Wire),patch.object(engine.time,'monotonic',side_effect=lambda:clock[0]),patch.object(engine,'event',side_effect=event),patch.object(miner.stop_event,'wait',side_effect=wait):
            miner.session('gulf.moneroocean.stream',20128,WALLET,True,400)
        self.assertEqual(len(connections),2)
        self.assertIn('reconnecting',events)
        self.assertEqual(rx.prepares,1,'unchanged seed rebuilt dataset')
        self.assertEqual(rx.closes,1)
        self.assertTrue(all(w.stopped for w in workers))

    def test_authentication_error_is_fatal_without_retry(self):
        rx=Rx();miner=engine.Miner(rx,1,True);connections=[]
        class Wire:
            def __init__(self,*args):connections.append(self)
            def send(self,message):pass
            def close(self):pass
            def receive(self):return {'id':1,'error':{'message':'IP temporarily banned'}}
        with patch.object(engine,'Wire',Wire),patch.object(engine,'event'):
            with self.assertRaises(PermissionError):miner.session('gulf.moneroocean.stream',20128,WALLET)
        self.assertEqual(len(connections),1)

    def test_unacknowledged_share_is_never_replayed_after_reconnect(self):
        rx=Rx();miner=engine.Miner(rx,1,True);connections=[];events=[]
        class ShareWorkers(Workers):
            def start(self,job):self.shares.put((1,b'\x00'*32))
        miner.worker_factory=ShareWorkers
        class Wire:
            def __init__(self,*args):self.index=len(connections);connections.append(self);self.sent=[];self.first=True
            def send(self,message):self.sent.append(message)
            def close(self):pass
            def receive(self):
                if self.first:
                    self.first=False
                    return {'id':1,'result':{'id':'session','job':JOB}}
                raise ConnectionResetError('lost response')
        def event(kind,**values):
            events.append((kind,values))
            if kind=='connecting' and len(connections)==2:miner.stop()
        with patch.object(engine,'Wire',Wire),patch.object(engine,'event',side_effect=event),patch.object(miner.stop_event,'wait',return_value=False):
            miner.session('pool.hashvault.pro',443,WALLET)
        self.assertEqual([m['method'] for m in connections[0].sent],['login','submit'])
        self.assertEqual([m['method'] for m in connections[1].sent],['login'])
        self.assertEqual(miner.accepted,0)
        self.assertIn(('unconfirmed_shares',{'count':1,'replayed':False}),events)

    def test_stop_cancels_retry_delay(self):
        miner=engine.Miner(Rx(),1,True);events=[]
        def event(kind,**values):
            events.append(kind)
            if kind=='reconnecting':miner.stop()
        with patch.object(engine,'Wire',side_effect=ConnectionResetError()),patch.object(engine,'event',side_effect=event),patch.object(miner.stop_event,'wait',side_effect=lambda delay:miner.stop_event.is_set()):
            miner.session('pool.hashvault.pro',443,WALLET)
        self.assertEqual(events.count('reconnecting'),1)

    def test_backoff_grows_instead_of_hammering_pool(self):
        miner=engine.Miner(Rx(),1,True);delays=[]
        def event(kind,**values):
            if kind=='reconnecting':
                delays.append(values['delay_seconds'])
                if len(delays)==4:miner.stop()
        with patch.object(engine,'Wire',side_effect=ConnectionResetError()),patch.object(engine,'event',side_effect=event),patch.object(engine.secrets,'randbelow',return_value=0),patch.object(miner.stop_event,'wait',side_effect=lambda delay:miner.stop_event.is_set()):
            miner.session('pool.hashvault.pro',443,WALLET)
        self.assertEqual(delays,[2,4,8,16])

    def test_accepted_totals_survive_reconnect_without_duplicate_submission(self):
        rx=Rx();miner=engine.Miner(rx,1,True);connections=[]
        class ShareWorkers(Workers):
            def start(self,job):self.shares.put((1,b'\x00'*32))
        miner.worker_factory=ShareWorkers
        class Wire:
            def __init__(self,*args):
                self.sent=[];self.responses=[{'id':1,'result':{'id':'session'+str(len(connections)),'job':{**JOB,'job_id':str(len(connections))}}}]
                connections.append(self)
            def send(self,message):
                self.sent.append(message)
                if message['method']=='submit':self.responses.append({'id':message['id'],'result':{'status':'OK'}})
            def close(self):pass
            def receive(self):
                if self.responses:return self.responses.pop(0)
                raise ConnectionResetError('test disconnect')
        def event(kind,**values):
            if kind=='share' and values['total_accepted']==2:miner.stop()
        with patch.object(engine,'Wire',Wire),patch.object(engine,'event',side_effect=event),patch.object(miner.stop_event,'wait',return_value=False):
            miner.session('pool.hashvault.pro',443,WALLET)
        self.assertEqual(miner.accepted,2)
        self.assertEqual(len(connections),2)
        self.assertTrue(all(sum(m['method']=='submit' for m in w.sent)==1 for w in connections))
        self.assertEqual(rx.prepares,1)

if __name__=='__main__':unittest.main()
