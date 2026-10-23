import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import xmrig_bridge


class DummyChild:
    returncode = None

    @staticmethod
    def poll():
        return None


class BridgeTests(unittest.TestCase):
    def test_config_has_loopback_only_authenticated_api_and_no_dev_fee(self):
        config = {'donate-level': 0, 'pools': [{'user': 'public-wallet'}], 'http': {'enabled': False}}
        secured = xmrig_bridge.secure_config(json.dumps(config), 40123, 'test-token')
        self.assertEqual(secured['donate-level'], 0)
        self.assertFalse(secured['autosave'])
        self.assertFalse(secured['watch'])
        self.assertEqual(secured['http'], {
            'enabled': True, 'host': '127.0.0.1', 'port': 40123,
            'access-token': 'test-token', 'restricted': False,
        })

    def test_config_rejects_nonzero_xmrig_donation(self):
        with self.assertRaisesRegex(ValueError, 'donation'):
            xmrig_bridge.secure_config(json.dumps({'donate-level': 1}), 40123, 'test-token')

    def test_backend_rates_are_separated_by_xmrig_backend_type(self):
        rates = xmrig_bridge.backend_rates([
            {'type': 'cpu', 'hashrate': [9001.5, 8800, 8500]},
            {'type': {'name': 'cuda'}, 'hashrate': [330.25, 320, 300]},
            {'type': 'opencl', 'hashrate': []},
        ])
        self.assertEqual(rates, {'cpu': 9001.5, 'cuda': 330.25, 'opencl': None})

    def test_config_update_uses_authenticated_loopback_api(self):
        received = []

        class Handler(BaseHTTPRequestHandler):
            def do_PUT(self):
                received.append((self.path, self.headers.get('Authorization'),
                                 json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(204)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            xmrig_bridge.apply_config(server.server_port, 'secret-token',
                                      json.dumps({'donate-level': 0, 'pools': [{'user': 'new-wallet'}]}),
                                      DummyChild(), timeout=1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(len(received), 1)
        path, auth, payload = received[0]
        self.assertEqual(path, '/2/config')
        self.assertEqual(auth, 'Bearer secret-token')
        self.assertEqual(payload['pools'][0]['user'], 'new-wallet')
        self.assertEqual(payload['http']['host'], '127.0.0.1')


if __name__ == '__main__':
    unittest.main()
