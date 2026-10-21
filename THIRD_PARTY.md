# Third-party notices

- XMRig 6.26.0: GPL-3.0; upstream https://github.com/xmrig/xmrig . Default/minimum donation levels changed from 1 to 0; per-backend hashrate log lines added in src/core/Miner.cpp; CUDA and OpenCL enabled at build time, MSR disabled. Modified complete source and rebuild instructions are in source/.
- XMRig static dependencies: libuv 1.51.0, OpenSSL 3.0.16, hwloc 2.12.1. See source/DEPENDENCIES.md and licenses/.
- Python 3.11.9, psutil 7.2.2, PyCryptodome 3.23.0, PyInstaller 6.21.0: notices in licenses/.
- Country flag PNGs retrieved from https://flagcdn.com/ (Flagpedia country flag assets). Flags identify language presets and do not imply exclusive language usage.
- app.ico and app.png are the application artwork. Monero/XMRig and pool names remain their respective owners' names. No official endorsement is claimed.

The repository provides modified engine/plugin sources, build instructions, build-dependency archives and license notices. The installer contains all runtime libraries and corresponding engine/plugin source, with a download link for build-only dependencies.

- XMRig CUDA 6.22.1: GPL-3.0; corresponding source archive and license are included. https://github.com/xmrig/xmrig-cuda/releases/tag/v6.22.1
- NVIDIA NVRTC CUDA 12.9 runtime libraries: redistribution subject to NVIDIA CUDA terms, https://docs.nvidia.com/cuda/eula/index.html . The hardware vendor display driver is not included.
