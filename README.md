# XMR

**A Windows desktop app for Monero CPU and GPU mining, pool monitoring, and manual control.**

[Download the Windows x64 installer](https://github.com/ckwj59/MoneroDesk/raw/refs/heads/main/downloads/XMR-CPU-GPU-Windows-x64-Setup.exe) · [Checksums](downloads/SHA256SUMS.txt) · [Security scans](https://github.com/ckwj59/MoneroDesk/actions/workflows/codeql.yml) · [Test results](VALIDATION.md)

The Windows package uses XMRig 6.26.0 for its CPU JIT and supported GPU backends. A small project bridge preserves the existing interface, applies live wallet/pool changes through XMRig's authenticated HTTP API bound to `127.0.0.1`, and reads separate CPU/GPU rates. This project is not endorsed by Monero or by the listed pools.

## Install and start

1. Double-click the single-file Windows x64 installer and choose Install.
2. Open the **XMR** desktop shortcut. A clean install has a blank main payout address; enter your own public Monero mainnet address.
3. Choose a pool, CPU thread count, and optional GPU backend. Review the displayed time allocation and click **Start mining**.

The installer includes the application, XMRig CPU engine, XMRig CUDA plugin and its CUDA runtime libraries, source archive, and license notices. A compatible NVIDIA driver is still required for CUDA; AMD OpenCL depends on a compatible system OpenCL driver. The app installs under `%LOCALAPPDATA%/Programs/XMR-CPU-GPU`, preserves its settings/history when updated, and does not start mining automatically.

This release targets Windows x64. Linux, ARM and RISC-V builds are not included. GPU solo behavior has not been independently validated. See [compatibility](COMPATIBILITY.md).

## Features

- Run CPU and GPU separately or together, with separate measured hashrates and activity logs.
- Select logical CPU thread counts, switch supported pools, and apply wallet allocation changes while XMRig remains running.
- Use verified TLS for supported remote pools. The local management API uses a random bearer token, listens only on loopback, and is removed when the miner exits.
- View pool balances, valid/invalid shares, payout thresholds, reference prices, recent blocks and measured power data where the system provides it.
- Use saved language preferences and the included translations.

RandomX performance depends on CPU model, memory configuration, large-page permissions, laptop power limits, cooling and background load. CPU/GPU mining together can share power and cooling capacity. **No specific hashrate or earnings are guaranteed; compare sustained readings after the system reaches steady temperature.**

## Transparent defaults and allocation

The app's XMRig developer donation is configured to 0%. Pool and network fees remain provider-defined. The optional **1% author mining-time allocation is enabled by default**, is shown in the interface, and can be disabled. Accumulated runtime from 20:00–21:00, then 120:00–121:00, 220:00–221:00 and so on uses the disclosed author recipient; other runtime uses the user's main address. Pauses stop the clock. This allocates mining time; it does not guarantee an exact share of earnings or a payout.

Disclosed author recipient:

```text
48Rd53h2a9aT1wYnMF6VtVZab189WPVR5jgVf6UedT4iRiLNX91MoA5GydXdu5oMVeSZZCv1H86wKR91V6bBZXCu4LpLusv
```

Local settings/history are excluded from the repository. Pool queries send the public query address to the selected provider; price queries use third-party services. Never upload your local `data/` folder or enter a seed phrase/private key.

## Validation and security

The repository includes bridge/API tests, configuration/hash checks, and installer extraction verification. The bundled XMRig and CUDA-plugin files are checked against SHA-256 manifests. These checks do not establish a specific sustained hashrate, GPU compatibility on every system, profitability, or a security certification.

[CodeQL](https://github.com/ckwj59/MoneroDesk/security/code-scanning) and CI results should be reviewed directly in GitHub. A green workflow is not a security certificate; binary and GPU-device-code coverage is limited. See [SECURITY.md](SECURITY.md).

## Source and license

The interface is in `app.py`; the live-configuration bridge is `engine/xmrig_bridge.py`. The bundled XMRig source archive and its GPL license are in `source/` and `licenses/`; CUDA plugin notices are included alongside them. See [BUILD.md](BUILD.md) and [THIRD_PARTY.md](THIRD_PARTY.md).

The project is distributed under [GPL-3.0-or-later](LICENSE), subject to the third-party licenses and notices in `THIRD_PARTY.md`. The XMRig and plugin licenses and corresponding source are included with the installer.
