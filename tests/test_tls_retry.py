import hashlib,socket,ssl,threading,time,tempfile,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
import tls_transport as tls

class RetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        base=Path(cls.temp.name);cls.cert=base/'cert.pem';cls.key=base/'key.pem'
        subprocess.run([r'C:\Program Files\Git\usr\bin\openssl.exe','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(cls.key),'-out',str(cls.cert),'-days','1','-subj','/CN=localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        pem=cls.cert.read_text()
        cls.policy={'pem':pem,'sha256':hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()}
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def server(self,tls_mode=True):
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(3)
        self.addCleanup(listener.close)
        ended=threading.Event();received=[]
        def serve():
            try:
                with listener.accept()[0] as raw:
                    raw.settimeout(3)
                    if tls_mode:
                        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                        context.minimum_version=ssl.TLSVersion.TLSv1_2
                        context.load_cert_chain(str(self.cert),str(self.key))
                        with context.wrap_socket(raw,server_side=True) as secure:received.append(secure.recv(1))
                    else:
                        while raw.recv(4096):pass
            except OSError:pass
            finally:ended.set()
        thread=threading.Thread(target=serve,daemon=True);thread.start()
        self.addCleanup(lambda:thread.join(4))
        return listener.getsockname()[1],ended,received
    def test_stalled_port_does_not_block_verified_port_and_loser_closes(self):
        stalled,ended,_=self.server(False);good,_,_=self.server()
        with patch.dict(tls.TRUSTED_CERTIFICATES,{'localhost':self.policy}),patch.object(tls,'_candidate_ports',return_value=[stalled,good]):
            started=time.monotonic()
            with tls.open_tls_socket('localhost',stalled,2) as conn:
                self.assertEqual(conn.getpeername()[1],good)
                self.assertIn(conn.version(),('TLSv1.2','TLSv1.3'))
                self.assertLess(time.monotonic()-started,1.5)
            self.assertTrue(ended.wait(1),'Losing connection leaked')
    def test_pin_change_fails_before_application_data(self):
        port,ended,received=self.server()
        with patch.dict(tls.TRUSTED_CERTIFICATES,{'localhost':{**self.policy,'sha256':'00'*32}}):
            with self.assertRaises(ssl.SSLCertVerificationError):tls.open_tls_socket('localhost',port,2)
        self.assertTrue(ended.wait(1));self.assertFalse(any(received))
    def test_total_deadline_and_tls_stage_diagnostic(self):
        port,ended,_=self.server(False)
        started=time.monotonic()
        with self.assertRaisesRegex(ConnectionError,'TLS:Timeout'):tls.open_tls_socket('localhost',port,.2)
        self.assertLess(time.monotonic()-started,1)
        self.assertTrue(ended.wait(1))
    def test_candidates_stay_in_selected_pool(self):
        self.assertEqual(tls._candidate_ports('gulf.moneroocean.stream',20001),[20001,443,20128])
        self.assertEqual(tls._candidate_ports('custom.example',4443),[4443])
        self.assertEqual(tls._candidate_ports('pool.hashvault.pro',443),[443])
    def test_dns_failure_is_identified(self):
        with patch.object(tls,'get_system_proxy',return_value=None),patch.object(tls.socket,'getaddrinfo',side_effect=socket.gaierror('not found')):
            with self.assertRaisesRegex(ConnectionError,'DNS resolution failed'):tls.open_tls_socket('missing.invalid',443,.2)

if __name__=='__main__':unittest.main()
