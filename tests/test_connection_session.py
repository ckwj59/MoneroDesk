import ssl,unittest
from unittest.mock import MagicMock,patch
import engine

class ConnectionSessionTests(unittest.TestCase):
    def test_transient_connection_retries_once_before_login(self):
        miner=engine.Miner(MagicMock(),1,True)
        wire=MagicMock()
        def event(kind,**values):
            if kind=='connecting':miner.stop_event.set()
        with patch.object(engine,'Wire',side_effect=[ConnectionError('timeout'),wire]) as connect,patch.object(engine,'event',side_effect=event),patch.object(miner.stop_event,'wait',return_value=False):
            miner.session('pool.hashvault.pro',443,'4'+'1'*94)
        self.assertEqual(connect.call_count,2)
        self.assertEqual(wire.send.call_count,1)
        self.assertEqual(wire.send.call_args.args[0]['method'],'login')
        wire.close.assert_called_once()
    def test_certificate_failure_never_retries(self):
        miner=engine.Miner(MagicMock(),1,True)
        with patch.object(engine,'Wire',side_effect=ssl.SSLCertVerificationError('changed')) as connect:
            with self.assertRaises(ssl.SSLCertVerificationError):miner.session('pool.hashvault.pro',443,'4'+'1'*94)
        self.assertEqual(connect.call_count,1)
    def test_keepalive_is_not_counted_as_a_share(self):
        miner=engine.Miner(MagicMock(),1,True)
        clock=[0];reply=[];wire=MagicMock();events=[]
        reply.append({'id':1,'result':{'id':'session','extensions':['keepalive']}})
        def receive():
            clock[0]+=10
            return reply.pop(0) if reply else None
        def send(message):
            if message['method']=='keepalived':
                self.assertEqual(message['params'],{'id':'session'})
                reply.append({'id':message['id'],'result':{'status':'KEEPALIVED'}})
        def event(kind,**values):
            events.append(kind)
            if kind=='keepalive':miner.stop_event.set()
        wire.receive.side_effect=receive;wire.send.side_effect=send
        with patch.object(engine,'Wire',return_value=wire),patch.object(engine.time,'monotonic',side_effect=lambda:clock[0]),patch.object(engine,'event',side_effect=event):
            miner.session('custom.example',443,'4'+'1'*94,True,100)
        self.assertIn('keepalive',events)
        self.assertNotIn('share',events)
        self.assertEqual((miner.accepted,miner.rejected),(0,0))
        wire.close.assert_called_once()

if __name__=='__main__':unittest.main()
