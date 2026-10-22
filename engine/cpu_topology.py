"""Optional per-worker affinity, constrained to the process's allowed CPUs."""
import ctypes as C
import os

def cpu_order():
    if os.name!='nt':return sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else []
    if (os.cpu_count() or 1)>64:return []  # Do not truncate multi-group systems.
    kernel=C.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=C.c_void_p
    kernel.GetProcessAffinityMask.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.POINTER(C.c_size_t)]
    allowed=C.c_size_t();system=C.c_size_t()
    if not kernel.GetProcessAffinityMask(kernel.GetCurrentProcess(),C.byref(allowed),C.byref(system)):return []
    size=C.c_ulong();kernel.GetLogicalProcessorInformation(None,C.byref(size))
    if not size.value:return []
    buf=C.create_string_buffer(size.value)
    if not kernel.GetLogicalProcessorInformation(buf,C.byref(size)):return []
    cores=[]
    for offset in range(0,size.value,32):
        mask=int.from_bytes(buf.raw[offset:offset+8],'little')&allowed.value
        if int.from_bytes(buf.raw[offset+8:offset+12],'little')==0 and mask:
            cores.append([i for i in range(64) if mask&(1<<i)])
    return [core[0] for core in cores]+[i for core in cores for i in core[1:]]

def pin_current(cpu):
    if os.name!='nt':
        if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,{cpu});return True
        return False
    kernel=C.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentThread.restype=C.c_void_p
    kernel.SetThreadAffinityMask.argtypes=[C.c_void_p,C.c_size_t]
    kernel.SetThreadAffinityMask.restype=C.c_size_t
    return bool(kernel.SetThreadAffinityMask(kernel.GetCurrentThread(),1<<cpu))
