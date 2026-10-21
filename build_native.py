"""Build on the target CPU/OS. Does not claim that cross compilation is runtime validation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from portable_support import IS_WINDOWS,native_arch,platform_id,engine_name

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--deps',type=Path,help='Native architecture XMRig dependency root (especially Windows)')
    parser.add_argument('--jobs',type=int,default=2)
    args=parser.parse_args()
    if sys.platform not in ('win32','linux'): parser.error('Targets are Windows and Linux.')
    if IS_WINDOWS and native_arch() not in ('x86','x64','armv8'): parser.error('No Windows ARMv7 or RISC-V release target is provided.')
    root=Path(__file__).resolve().parent;out=args.output.resolve()
    if out==root or root in out.parents: parser.error('Choose an output outside the source directory.')
    if out.exists(): parser.error('Output must be a new directory, to preserve existing settings.')
    out.mkdir(parents=True);source=out/'build-source';source.mkdir()
    with zipfile.ZipFile(root/'source/xmrig-6.26.0-modified.zip') as z:
        for name in z.namelist():
            if not (source/name).resolve().is_relative_to(source): raise ValueError('Invalid source archive path')
        z.extractall(source)
    command=['cmake','-S',str(source/'xmrig-6.26.0'),'-B',str(out/'build'),'-DCMAKE_BUILD_TYPE=Release','-DWITH_MSR=OFF','-DWITH_OPENCL=ON','-DWITH_CUDA=ON']
    if args.deps: command+=['-DXMRIG_DEPS='+str(args.deps.resolve())]
    if IS_WINDOWS: command+=['-A',{'x86':'Win32','x64':'x64','armv8':'ARM64'}[native_arch()]]
    subprocess.run(command,check=True)
    subprocess.run(['cmake','--build',str(out/'build'),'--config','Release','--parallel',str(max(1,args.jobs))],check=True)
    binary=out/'build'/('Release' if IS_WINDOWS else '')/engine_name()
    app=out/'MoneroDesk';(app/'engine').mkdir(parents=True)
    for name in ('app.py','portable_support.py','app.png','app.ico','LICENSE','requirements-native.txt','COMPATIBILITY.md'):
        shutil.copy2(root/name,app/name)
    for name in ('flags','locales','licenses'): shutil.copytree(root/name,app/name)
    shutil.copy2(binary,app/'engine'/engine_name())
    (app/'engine'/engine_name()).chmod(0o755)
    (app/'engine/manifest.json').write_text(json.dumps({'target':platform_id(),'version':'6.26.0-custom','developer_donation':0,'sha256':hashlib.sha256(binary.read_bytes()).hexdigest()},indent=2))
    if IS_WINDOWS:
        (app/'Start.cmd').write_text('@echo off\r\ncd /d "%~dp0"\r\npython app.py\r\n')
    else:
        launcher=app/'start.sh'
        launcher.write_text('#!/bin/sh\nset -eu\ncd -- "$(dirname -- "$0")"\nexec python3 app.py\n')
        launcher.chmod(0o755)
    print('Built native engine and source UI at',app)
    print('Install requirements-native.txt in your virtual environment and run the launcher. GPU plugins require a matching native bundle; Windows DLLs cannot run on Linux.')

if __name__=='__main__': main()
