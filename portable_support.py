"""Native platform helpers; Linux ports require native engine builds and device testing."""
import os
import platform
from pathlib import Path
import signal
import struct
import subprocess
import sys
import threading
import time

IS_WINDOWS = sys.platform == 'win32'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

def native_arch(machine=None, bits=None):
    machine=(machine or platform.machine()).lower()
    bits=bits or struct.calcsize('P')*8
    if machine in ('amd64','x86_64','x64','i386','i486','i586','i686','x86'):
        return 'x64' if bits==64 else 'x86'
    if machine in ('aarch64','arm64','armv8l'): return 'armv8' if bits==64 else 'armv7'
    if machine.startswith('arm'): return 'armv7'
    if machine.startswith('riscv'): return 'riscv64' if bits==64 else 'riscv32'
    return machine

def platform_id():
    return ('windows' if IS_WINDOWS else sys.platform)+'-'+native_arch()

def engine_name():
    return 'XMR-Engine.exe' if IS_WINDOWS else 'xmr-engine'

def cuda_files():
    return ('xmr-randomx-cuda.dll',) if IS_WINDOWS else ('libxmr-cuda.so',)

def linux_hardware(result, proc=Path('/proc'), system=Path('/sys')):
    try:
        info=(proc/'cpuinfo').read_text()
        for label in ('model name','Hardware','uarch','Processor'):
            line=next((line for line in info.splitlines() if line.split(':')[0].strip()==label),None)
            if line: result['cpu']=line.split(':',1)[1].strip();break
    except OSError: pass
    try:
        for cache in (system/'devices/system/cpu/cpu0/cache').glob('index*'):
            if (cache/'level').read_text().strip()=='3':
                size=(cache/'size').read_text().strip().upper()
                result['l3']=int(size[:-1])*({'K':1024,'M':1024**2}.get(size[-1],1))
    except (OSError,ValueError): pass
    try:
        reply=subprocess.run(['lspci'],capture_output=True,text=True,timeout=5)
        result['gpu']=[line.split(': ',1)[-1] for line in reply.stdout.splitlines() if any(label in line for label in ('VGA compatible controller','3D controller','Display controller'))]
    except (OSError,subprocess.TimeoutExpired): pass
    return result

def validate_native_manifest(manifest):
    target=manifest.get('target')
    # Historical shipped binaries are Windows x64 only.
    target=target or 'windows-x64'
    if target!=platform_id():
        raise ValueError('Engine target '+target+' does not match '+platform_id()+'. Build/install the matching native package.')

class LinuxMinerJob:
    def __init__(self,process): self.process=process
    def close(self):
        if self.process.poll() is None: self.process.terminate()

def supervise(parent_pid, command):
    """Separate watchdog exits the owned engine if its UI parent disappears."""
    import psutil
    parent=psutil.Process(parent_pid)
    created=parent.create_time()
    child=subprocess.Popen(command,stdin=subprocess.DEVNULL)
    stopped=threading.Event()
    def stop(*unused):
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=3)
            except subprocess.TimeoutExpired: child.kill()
        stopped.set()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    try:
        while child.poll() is None:
            try:
                if not parent.is_running() or parent.create_time()!=created or parent.status()==psutil.STATUS_ZOMBIE:
                    stop();break
            except psutil.NoSuchProcess: stop();break
            stopped.wait(.25)
        return child.wait()
    finally: stop()

if __name__=='__main__':
    raise SystemExit(supervise(int(sys.argv[1]),sys.argv[2:]))
