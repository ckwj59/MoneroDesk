# XMR

**A Windows desktop interface for Monero CPU mining, experimental NVIDIA GPU mining, and pool monitoring.**

[Download the Windows x64 installer](https://github.com/ckwj59/MoneroDesk/raw/refs/heads/main/downloads/XMR-CPU-GPU-Windows-x64-Setup.exe) · [Checksums](downloads/SHA256SUMS.txt) · [Security scans](https://github.com/ckwj59/MoneroDesk/actions/workflows/codeql.yml) · [Test results](VALIDATION.md)

This preview replaces the previous XMRig-based package with an independently written Stratum client and worker controller. It uses the upstream RandomX algorithm library and separately licensed CUDA helpers. **It does not bundle or run XMRig.** This is an independent project, without official endorsement from Monero or the listed pools.

## Install and start

1. Close the old XMR app and double-click the installer (about 28 MiB / 29.3 MB).
2. Open the **XMR** desktop shortcut. Enter **your own public Monero mainnet payout address** and choose a pool.
3. Choose your CPU percentage and optionally enable NVIDIA CUDA. Review the disclosed allocation, then click **Start mining**.

The installer includes the app, independent engine and native libraries. No separate CUDA Toolkit is required for installation; a compatible NVIDIA driver is required for GPU mining. The app installs under `%LOCALAPPDATA%/Programs/XMR-CPU-GPU`, preserves that installation's `data/` folder on update, and does not start mining automatically. Older MoneroDesk installations use a different folder and are not migrated automatically.

**Preview status:** Windows x64 CPU and NVIDIA CUDA pool mining have local accepted-share validation. AMD OpenCL, GPU solo, Linux/ARM/RISC-V packages and complete cross-platform support are not delivered. CPU solo has local simulated submission tests, without a mainnet block-finding validation. See [compatibility](COMPATIBILITY.md).

## What you can do

- Control CPU and GPU separately; view separate measured device rates, accepted shares and activity logs.
- Allocate CPU mining threads by percentage of the detected machine's logical processors.
- Switch supported pools by fully stopping the old session before starting the new target; pool data follows the active provider.
- Use verified TLS connections, bounded reconnect delays and the already-enabled local Windows HTTP proxy when applicable. Certificate failures do not silently disable verification or fall back to plaintext.
- Inspect supported pool balances, paid amounts and automatic payout thresholds. Missing API data stays unavailable; balances across pools cannot be combined for payment.
- View reference prices, recent blocks and estimates separately from actual credited earnings. Supported payout-setting changes follow each provider's own policy and authentication requirements.
- Use 20 language presets with flags, saved preferences, a system-language initial default and mapped reference currencies. Some translations may fall back to English.
- Read available power sensors and integrate valid samples into kWh. Most consumer PCs cannot expose whole-computer wall power; missing readings are not fabricated.

Rates refresh each second using an approximately 10-second rolling window. Dataset preparation and completed GPU batches affect startup and short-term samples. Monero RandomX favors CPUs; adding GPU mining can reduce CPU speed through shared power, cooling or memory bandwidth. **A larger GPU model number does not establish a particular RandomX rate. No hashrate or earnings target is guaranteed.**

## Transparent defaults and allocation

The app is free; engine developer donation is 0%. Pool and network fees remain provider-defined. Your main payout address starts blank. The app never asks for a seed phrase or private key.

The optional **1% author mining-time allocation is enabled by default**, clearly shown, and can be disabled. Accumulated mining runtime **20:00–21:00**, then **120:00–121:00**, **220:00–221:00** and so on uses the author recipient; other runtime uses your main address. Pauses stop the clock. CPU and GPU share the schedule. This allocates mining time, not an exact percentage of earnings or a transfer from your wallet.

Disclosed author recipient:

```text
48Rd53h2a9aT1wYnMF6VtVZab189WPVR5jgVf6UedT4iRiLNX91MoA5GydXdu5oMVeSZZCv1H86wKR91V6bBZXCu4LpLusv
```

Local settings/history are excluded from the public repository. Pool queries send the public query address to the selected provider; price queries use third-party services. Never upload your local `data/` folder.

## Validation and security

The shipped GPU kernel improved from approximately 347 to 492 H/s in a paired local benchmark, with 8,192 matching reference hashes. A roughly 65-second GPU-only MoneroOcean TLS session recorded 3 accepted / 0 rejected shares. These are short local tests on an RTX 5070 Laptop, not expected performance for every device.

Further 8-lane, 16-lane and 256-thread-block trials checked 24,576 hashes and did **not** demonstrate an effective improvement; those candidates are not shipped. The current preview still has substantial GPU performance limitations.

[CodeQL](https://github.com/ckwj59/MoneroDesk/security/code-scanning) scans the checked-in Python, C/C++ and C# source on pushes. [CI](https://github.com/ckwj59/MoneroDesk/actions/workflows/verify.yml) verifies defaults, native-library hashes and protocol/recovery tests. Check actual run status and findings: a green workflow is not a GitHub safety certificate. CUDA device-code coverage is limited; these workflows do not establish a complete audit of GPU kernels or installer binaries. See [SECURITY.md](SECURITY.md).

## Source, build and contributions

The original interface is in `app.py`; independent engine source and supplied runtime are in `engine/`. Native adapter/kernel source is in `native/`; pinned RandomX corresponding source is in `engine/RandomX-source.zip`. The C# installer source is in `installer/`. See [BUILD.md](BUILD.md).

Report reproducible issues with the app version, device model and redacted logs. Contributions to GPU execution efficiency, translations, API compatibility, accessibility and separately validated platform ports are welcome. Do not include wallet secrets or credentials.

Distributed under [GPL-3.0-or-later](LICENSE), with dependency terms in [THIRD_PARTY.md](THIRD_PARTY.md). Earlier installers and XMRig source/binaries have been removed from the current branch; Git commit history is retained for traceability.
