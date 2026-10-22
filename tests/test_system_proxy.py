import socket,ssl,threading,unittest
from unittest.mock import patch
import system_proxy as proxy
import tls_transport as tls
from test_tls_retry import RetryTests

class ProxyParsingTests(unittest.TestCase):
    def test_only_explicit_loopback_http_proxy_is_selected(self):
        for value in ['127.0.0.1:7890','http://127.0.0.1:7890','http=127.0.0.1:7890;https=127.0.0.1:7891','localhost:7890','[::1]:7890']:
            self.assertIsNotNone(proxy.parse_local_proxy(value),value)
        self.assertEqual(proxy.parse_local_proxy('http=127.0.0.1:7890;https=127.0.0.1:7891'),('127.0.0.1',7891))
        for value in ['remote.example:7890','192.168.1.1:7890','user:password@127.0.0.1:7890','socks=127.0.0.1:7890','socks5://127.0.0.1:7890','127.0.0.1:0','127.0.0.1:7890\r\nInjected: yes']:
            self.assertIsNone(proxy.parse_local_proxy(value),value)

class ProxyTlsTests(RetryTests):
    def proxy_server(self,status=200):
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(3)
        self.addCleanup(listener.close)
        requests=[];done=threading.Event()
        def serve():
            try:
                with listener.accept()[0] as raw:
                    raw.settimeout(3);header=b''
                    while not header.endswith(b'\r\n\r\n'):
                        data=raw.recv(1)
                        if not data:return
                        header+=data
                    requests.append(header)
                    raw.sendall(f'HTTP/1.1 {status} Test\r\n\r\n'.encode())
                    if status==200:
                        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                        context.load_cert_chain(str(self.cert),str(self.key))
                        with context.wrap_socket(raw,server_side=True) as conn:conn.recv(1)
            except OSError:pass
            finally:done.set()
        thread=threading.Thread(target=serve,daemon=True);thread.start()
        self.addCleanup(lambda:thread.join(4))
        return ('127.0.0.1',listener.getsockname()[1]),requests,done
    def test_proxy_tunnel_preserves_pool_port_and_certificate_verification(self):
        endpoint,requests,done=self.proxy_server();events=[]
        with patch.object(tls,'get_system_proxy',return_value=endpoint),patch.dict(tls.TRUSTED_CERTIFICATES,{'pool.example':self.policy}):
            with tls.open_tls_socket('pool.example',443,3,on_progress=lambda stage,**values:events.append(stage)) as conn:
                self.assertEqual(conn.xmr_pool_port,443)
                self.assertEqual(conn.xmr_route,'system_proxy')
                self.assertEqual(conn.getpeername()[1],endpoint[1])
        self.assertTrue(done.wait(1))
        self.assertEqual(requests,[b'CONNECT pool.example:443 HTTP/1.1\r\nHost: pool.example:443\r\n\r\n'])
        self.assertIn('PROXY',events)
    def test_wrong_pin_through_proxy_still_fails_closed(self):
        endpoint,_,done=self.proxy_server()
        with patch.object(tls,'get_system_proxy',return_value=endpoint),patch.dict(tls.TRUSTED_CERTIFICATES,{'pool.example':{**self.policy,'sha256':'00'*32}}):
            with self.assertRaises(ssl.SSLCertVerificationError):tls.open_tls_socket('pool.example',443,3)
        self.assertTrue(done.wait(1))
    def test_proxy_authentication_denial_does_not_fall_back_to_direct(self):
        endpoint,requests,done=self.proxy_server(407)
        with patch.object(tls,'get_system_proxy',return_value=endpoint):
            with self.assertRaises(PermissionError):tls.open_tls_socket('pool.example',443,3)
        self.assertTrue(done.wait(1));self.assertEqual(len(requests),1)

if __name__=='__main__':unittest.main()
