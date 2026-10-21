# Native CPU builds: Windows and Linux

Current verified release: Windows x64. Other targets below require native builds and hardware validation; they are not prebuilt or certified by this project.

| OS | CPU | Current status |
|---|---|---|
| Windows | x64 | Shipped executable, CPU test and RTX 5070 CUDA loading tested |
| Windows | x86 | Native build entry provided; untested, 32-bit address-space limits may prevent RandomX startup |
| Windows | ARMv8 / ARM64 | Native build entry provided; native Python, MSVC and ARM64 dependencies required; untested |
| Windows | ARMv7, RISC-V | No release target provided; no general desktop build environment assumed |
| Linux | x86, x64 | Source UI / native build entry provided; not tested on Linux here |
| Linux | ARMv7 | Experimental native build; untested; 32-bit address-space and memory constraints apply |
| Linux | ARMv8 / AArch64 | Source UI / native build entry provided; untested |
| Linux | RISC-V 64 | Source UI / native build entry provided; untested |
| Linux | RISC-V 32 | No validated release target; experimental upstream/compiler compatibility required |

XMRig upstream lists x86/x64/ARMv7/ARMv8/RISC-V CPU backends: https://github.com/xmrig/xmrig
Upstream engine support is not proof that this GUI and every OS/CPU combination works.

## Linux build on the target device

Install a native C/C++ compiler, CMake, Python 3.10+, Python Tk, OpenSSL, libuv and hwloc development libraries. For Debian/Ubuntu these are normally `build-essential cmake python3 python3-venv python3-tk libssl-dev libuv1-dev libhwloc-dev`. Package names vary by distribution. A graphical session is needed for the Tk interface.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-native.txt
python build_native.py --output "$HOME/MoneroDesk-native-build" --jobs 2
"$HOME/MoneroDesk-native-build/MoneroDesk/start.sh"
```

Use a new output directory. The builder never overwrites an existing install or private settings. It builds on the current architecture; it does not turn an x64 binary into ARM/RISC-V.

Windows: use native Python, CMake, MSVC and an XMRig dependency root built for the same architecture:

```powershell
python build_native.py --output C:\MoneroDesk-native-build --deps C:\native-xmrig-deps
```

The engine manifest records its native platform. A mismatched target is rejected before launch. The Linux source interface uses a separate watchdog to stop its owned miner when the UI exits. Linux whole-system power readings remain unavailable unless a verified whole-system meter integration is added; no guessed readings are shown.

CPU mining is the default. CUDA/OpenCL still need compatible hardware and drivers. The Windows CUDA DLL bundle is Windows x64 only and cannot be copied into Linux or ARM builds. A matching Linux plugin/runtime bundle is required for Linux CUDA. No Linux GPU runtime bundle is supplied yet.

GPU efficiency: RandomX favors CPUs. Simultaneous CPU/GPU mining may lower CPU and total hashrate because of shared power, cooling or bandwidth. Compare steady measurements before enabling GPU.
