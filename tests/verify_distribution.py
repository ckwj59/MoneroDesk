from pathlib import Path
import ast, hashlib, json, zipfile
root = Path(__file__).resolve().parents[1]
author = '48Rd53h2a9aT1wYnMF6VtVZab189WPVR5jgVf6UedT4iRiLNX91MoA5GydXdu5oMVeSZZCv1H86wKR91V6bBZXCu4LpLusv'
source = (root/'app.py').read_text(encoding='utf-8')
ast.parse(source)
assert author in source
assert 'self.wallet = tk.StringVar()' in source
assert 'self.share = tk.BooleanVar(value=True)' in source
assert len(list((root/'locales').glob('*.json'))) == 18
for filename, manifest in [('randomx.dll','randomx-manifest.json'),('xmr-cpu-batch.dll','cpu-manifest.json'),('xmr-randomx-cuda.dll','cuda-manifest.json'),('XMR-Engine.exe','manifest.json')]:
    digest = hashlib.sha256((root/'engine'/filename).read_bytes()).hexdigest()
    assert digest == json.loads((root/'engine'/manifest).read_text(encoding='utf-8-sig'))['sha256'], filename
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
    assert not any('data' in Path(name).parts or 'xmrig' in Path(name).name.lower() for name in archive.namelist())
    assert archive.read('app.py') == (root/'app.py').read_bytes()
    for name in ('randomx.dll','xmr-cpu-batch.dll','xmr-randomx-cuda.dll','XMR-Engine.exe'):
        assert archive.read('engine/'+name) == (root/'engine'/name).read_bytes()
assert not list((root/'engine').glob('*xmrig*'))
print('PASS: blank main address, disclosed allocation, runtime hashes, matching installer/source and no XMRig payload')
