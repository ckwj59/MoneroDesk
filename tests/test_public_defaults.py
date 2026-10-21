"""Offline checks: this test never starts a miner or sends a network request."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import tkinter as tk
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('app',ROOT/'app.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
assert a.valid_wallet(a.BENEFICIARY)
manifest=json.loads((ROOT/'engine/manifest.json').read_text(encoding='utf8'))
assert manifest['developer_donation']==0
assert hashlib.sha256((ROOT/'engine/xmrig.exe').read_bytes()).hexdigest()==manifest['sha256']
(ROOT/'build').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=ROOT/'build') as d:
 a.DATA=Path(d)
 root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda *args:errors.append(args)
 with patch.object(a.App,'refresh_power'),patch.object(a.App,'refresh_money'),patch.object(a.App,'query_pool'):
  ui=a.App(root)
  assert ui.wallet.get()=='' and a.valid_wallet(a.BENEFICIARY) and ui.share.get()
  assert ui.mode.get()=='pool' and ui.cpu_enabled.get() and not ui.gpu_enabled.get()
  a.verify_gpu_bundle(ROOT/'engine')
  assert not ui.proc and not ui.checking and ui.total==0 and ui.allocation_elapsed==0
  ui.save()
  saved=json.loads((a.DATA/'settings.json').read_text(encoding='utf8'))
  assert saved['wallet']=='' and a.valid_wallet(a.BENEFICIARY) and saved['share'] is True
  root.update();assert not errors,errors;ui.close()
print('PASS: blank main address, visible author recipient, allocation enabled, manual start, clean counters, settings privacy, engine integrity')
