from pathlib import Path
import ast, hashlib, json, zipfile
root = Path(__file__).resolve().parents[1]
dist = root/'dist/XMR'
author = '48Rd53h2a9aT1wYnMF6VtVZab189WPVR5jgVf6UedT4iRiLNX91MoA5GydXdu5oMVeSZZCv1H86wKR91V6bBZXCu4LpLusv'
source = (root/'app.py').read_text(encoding='utf-8')
ast.parse(source)
assert author in source
assert 'self.wallet = tk.StringVar()' in source
assert 'self.share = tk.BooleanVar(value=True)' in source
assert len(list((root/'locales').glob('*.json'))) == 18
def verify_xmrig_payload(directory, require_bridge):
    xmrig = json.loads((directory/'xmrig-manifest.json').read_text(encoding='utf-8-sig'))
    assert hashlib.sha256((directory/'xmrig.exe').read_bytes()).hexdigest() == xmrig['sha256']
    gpu = json.loads((directory/'gpu-manifest.json').read_text(encoding='utf-8-sig'))['files']
    for filename,digest in gpu.items():
        assert hashlib.sha256((directory/filename).read_bytes()).hexdigest() == digest, filename
    if require_bridge:
        bridge = json.loads((directory/'manifest.json').read_text(encoding='utf-8-sig'))
        assert bridge['developer_donation'] == 0
        assert hashlib.sha256((directory/'XMR-Engine.exe').read_bytes()).hexdigest() == bridge['sha256']

verify_xmrig_payload(root/'engine', False)
verify_xmrig_payload(dist/'engine', True)
assert (dist/'app.py').read_bytes() == (root/'app.py').read_bytes()
gpu = json.loads((root/'engine/gpu-manifest.json').read_text())['files']
for filename, digest in gpu.items():
    assert hashlib.sha256((root/'engine'/filename).read_bytes()).hexdigest() == digest
installer = root/'downloads/XMR-CPU-GPU-Windows-x64-Setup.exe'
expected_hash = (root/'downloads/SHA256SUMS.txt').read_text(encoding='ascii').split()[0]
assert hashlib.sha256(installer.read_bytes()).hexdigest() == expected_hash
with zipfile.ZipFile(installer) as archive:
    assert archive.testzip() is None
    manifest = json.loads(archive.read('payload-manifest.json'))
    for name, digest in manifest.items():
        assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
    assert not any('data' in Path(name).parts for name in archive.namelist())
    assert archive.read('app.py') == (dist/'app.py').read_bytes()
    assert archive.read('XMR.exe') == (dist/'XMR.exe').read_bytes()
    for filename in ['XMR-Engine.exe','xmrig.exe','xmrig-cuda.dll','nvrtc64_120_0.dll',
                     'nvrtc-builtins64_129.dll','xmrig-manifest.json','gpu-manifest.json','manifest.json']:
        assert archive.read('engine/'+filename) == (dist/'engine'/filename).read_bytes()
    assert archive.read('source/xmrig-6.26.0-modified.zip') == (dist/'source/xmrig-6.26.0-modified.zip').read_bytes()
    assert archive.read('licenses/xmrig-GPL-3.0.txt') == (dist/'licenses/xmrig-GPL-3.0.txt').read_bytes()
assert (root/'source/xmrig-6.26.0-modified.zip').is_file()
assert (root/'licenses/xmrig-GPL-3.0.txt').is_file()
print('PASS: blank main address, disclosed allocation, XMRig/GPU hashes, matching GPL source and installer payload')
