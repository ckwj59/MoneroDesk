"""Supervise the bundled XMRig binary and apply live settings over loopback API."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import queue
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

BASE = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
MAX_CONFIG = 1024 * 1024
OUTPUT_LOCK = threading.Lock()
STOP = object()


def emit(line):
    data = (str(line).rstrip('\r\n') + '\n').encode('utf-8', errors='replace')
    with OUTPUT_LOCK:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()


def verify_xmrig():
    binary = BASE / ('xmrig.exe' if os.name == 'nt' else 'xmrig')
    metadata = json.loads((BASE / 'xmrig-manifest.json').read_text(encoding='utf-8'))
    actual = hashlib.sha256(binary.read_bytes()).hexdigest()
    if actual != metadata.get('sha256'):
        raise ValueError('Bundled XMRig integrity check failed')
    if metadata.get('version') != '6.26.0-custom':
        raise ValueError('Unexpected XMRig runtime version')
    return binary


def choose_loopback_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def secure_config(payload, port, token):
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError('Miner configuration must be a JSON object')
    if value.get('donate-level') != 0 or value.get('donate-over-proxy', 0) != 0:
        raise ValueError('XMRig developer donation must remain disabled')
    value['autosave'] = False
    value['watch'] = False
    value['http'] = {
        'enabled': True,
        'host': '127.0.0.1',
        'port': port,
        'access-token': token,
        'restricted': False,
    }
    return value


def api_request(port, token, method, payload=None, timeout=1.5):
    url = f'http://127.0.0.1:{port}/2/config' if method == 'PUT' else f'http://127.0.0.1:{port}/2/backends'
    data = None if payload is None else json.dumps(payload, separators=(',', ':')).encode('utf-8')
    request = urllib.request.Request(url, data=data, method=method, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/json',
        **({'Content-Type': 'application/json'} if data is not None else {}),
    })
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        body = response.read(1024 * 1024)
        return response.status, body


def apply_config(port, token, config, child, timeout=15):
    """Retry only startup races; reject API errors instead of pretending applied."""
    deadline = time.monotonic() + timeout
    last_error = None
    body = secure_config(config, port, token)
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError(f'XMRig exited with code {child.returncode} before config update')
        try:
            status, _ = api_request(port, token, 'PUT', body)
            if status not in (200, 204):
                raise RuntimeError(f'XMRig API returned HTTP {status}')
            return
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'XMRig API rejected config update: HTTP {exc.code}') from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            time.sleep(0.25)
    raise TimeoutError(f'XMRig local API did not accept config update: {last_error}')


def backend_rates(backends):
    result = {'cpu': None, 'cuda': None, 'opencl': None}
    if not isinstance(backends, list):
        return result
    for backend in backends:
        if not isinstance(backend, dict):
            continue
        kind = backend.get('type', '')
        if isinstance(kind, dict):
            kind = kind.get('name', kind.get('id', ''))
        kind = str(kind).lower()
        key = 'cpu' if 'cpu' in kind else 'cuda' if 'cuda' in kind else 'opencl' if 'opencl' in kind else None
        if key is None:
            continue
        rates = backend.get('hashrate')
        rate = rates[0] if isinstance(rates, list) and rates else None
        result[key] = float(rate) if isinstance(rate, (int, float)) and rate >= 0 else None
    return result


def _read_input(channel, messages):
    try:
        for line in channel:
            if len(line) > MAX_CONFIG:
                messages.put(('error', 'Configuration line exceeds the size limit'))
                return
            if line.strip():
                messages.put(('config', line))
    except (OSError, ValueError) as exc:
        messages.put(('error', str(exc)))
    finally:
        messages.put(('eof', STOP))


def _forward_output(child, done):
    try:
        for line in iter(child.stdout.readline, b''):
            emit(line.decode('utf-8', errors='replace'))
    finally:
        done.set()
        if child.stdout:
            child.stdout.close()


def _report_rates(port, token, child, stop_event):
    while not stop_event.wait(1):
        if child.poll() is not None:
            return
        try:
            _, body = api_request(port, token, 'GET')
            rates = backend_rates(json.loads(body))
            for name, value in rates.items():
                shown = 'n/a' if value is None else f'{value:.2f}'
                emit(f'backend-rate {name} {shown} H/s')
            total = sum(value for value in rates.values() if value is not None)
            emit(f'speed 10s/60s/15m {total:.2f} n/a n/a H/s')
        except (OSError, ValueError, urllib.error.URLError):
            # Native XMRig logs remain available; a missed sample is not a mining failure.
            continue


def run(input_stream=None, binary=None, popen=subprocess.Popen):
    binary = Path(binary or verify_xmrig())
    messages = queue.Queue()
    child = None
    rates_stop = threading.Event()
    output_done = threading.Event()
    port = choose_loopback_port()
    token = secrets.token_urlsafe(32)
    session_dir = tempfile.TemporaryDirectory(prefix='xmr-runtime-')
    config_path = Path(session_dir.name) / 'miner.json'
    source = input_stream or sys.stdin.buffer
    threading.Thread(target=_read_input, args=(source, messages), name='XMR-config-reader', daemon=True).start()
    output_thread = None
    rates_thread = None
    return_code = 0
    try:
        while True:
            try:
                kind, payload = messages.get(timeout=0.2)
            except queue.Empty:
                if child and child.poll() is not None:
                    return_code = child.returncode or 0
                    break
                continue
            if kind == 'eof':
                break
            if kind == 'error':
                raise ValueError(payload)
            if kind != 'config':
                continue
            parsed = secure_config(payload, port, token)
            if child is None:
                config_path.write_text(json.dumps(parsed, separators=(',', ':')), encoding='utf-8')
                child = popen([str(binary), '--config=' + str(config_path)], cwd=str(BASE),
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                              bufsize=0)
                output_thread = threading.Thread(target=_forward_output, args=(child, output_done),
                                                 name='XMRig-output', daemon=True)
                output_thread.start()
                rates_thread = threading.Thread(target=_report_rates, args=(port, token, child, rates_stop),
                                                name='XMRig-rates', daemon=True)
                rates_thread.start()
                emit('XMR | XMRig 6.26.0 CPU/GPU engine started; local control API bound to 127.0.0.1')
            else:
                apply_config(port, token, payload, child)
                emit('XMR | configuration applied through authenticated loopback API')
    finally:
        rates_stop.set()
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        if child and child.poll() is not None:
            return_code = child.returncode or return_code
        if rates_thread:
            rates_thread.join(timeout=2)
        if output_thread:
            output_thread.join(timeout=2)
        session_dir.cleanup()
    return return_code


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    if len(sys.argv) != 2 or sys.argv[1] != '--config-stdin':
        print('Usage: XMR-Engine.exe --config-stdin', file=sys.stderr)
        return 2
    try:
        return run()
    except Exception as exc:
        emit('XMR ERROR | ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
