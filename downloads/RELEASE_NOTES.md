# MoneroDesk v1.1.0 — Windows installer

Download `MoneroDesk-Windows-x64-v1.1.0-Setup.exe` and double-click to install. The previous portable ZIP has been removed from the current download directory.

- Bundles the desktop app, custom XMRig engine, NVIDIA CUDA 12.9 plugin and NVRTC libraries in one installer.
- Separate CPU/GPU checkmark switches and measured backend hashrates. Pool mining is the initial default; user choices are saved.
- GPU efficiency notice explains why simultaneous mining can reduce CPU or total performance.
- Preserves the public author recipient and optional 1% runtime allocation, enabled by default. The main payout address is blank. No private settings, history, account caches or credentials are shipped.
- Native Windows/Linux source build helpers and an honest compatibility table are included; additional architectures are not claimed as tested.
- Installer source is published under `installer/`; Python, C/C++ and C# source scanning is configured in GitHub Actions. Passing analysis is not certification of the installer binary.

Close an existing GPU session before upgrading. The installer preserves local `data/`. GPU mining is off by default. The app starts mining only after an explicit user action. A compatible graphics driver is required. Check SHA256SUMS.txt for file integrity.
