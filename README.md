# MoneroDesk

### Monero mining and pool monitoring, in one desktop app.

Install a Windows app, choose your pool, and manage your CPU and optional GPU from one place. MoneroDesk brings mining controls, separate device hashrates, pool balances and payout thresholds into a multilingual interface—so you can spend less time editing configuration files.

**Windows x64 · CPU + optional GPU · 20 language presets · Open source · GPL-3.0-or-later**

**Transparent defaults:** mining starts manually. Your main payout field is blank. Optional **1% author mining-time allocation is enabled by default**, displayed in the app, and can be turned off. Pool and network fees are separate.

## Get started

**[Download the Windows installer →](https://github.com/ckwj59/MoneroDesk/raw/refs/heads/main/downloads/MoneroDesk-Windows-x64-v1.1.0-Setup.exe)**

[Verify SHA-256](downloads/SHA256SUMS.txt) · [What's new](downloads/RELEASE_NOTES.md) · [Compatibility](COMPATIBILITY.md) · [Security scan runs](https://github.com/ckwj59/MoneroDesk/actions/workflows/codeql.yml)

1. Close an existing MoneroDesk GPU session, then double-click the installer. The app, mining engine, NVIDIA CUDA plugin and required CUDA runtime libraries are included.
2. Open **Monero Desk GPU** from your desktop. Enter **your own Monero mainnet payout address** and select a pool. Pool mode is the initial default.
3. Choose your CPU allocation, review the visible fee/allocation settings, and click **Start mining**. GPU mining is optional and off by default.

No separate CUDA Toolkit download is needed. A compatible NVIDIA or AMD display driver is still required. The installer uses `%LOCALAPPDATA%/MoneroDesk-GPU`, preserves existing settings, and keeps a separate D-drive installation intact.

## Why use MoneroDesk?

- **Keep control of your hardware.** Independent CPU/GPU switches, CPU percentage controls, manual start/stop, accepted-share counts and readable activity logs.
- **See what each device contributes.** CPU, GPU and total hashrates are displayed separately. Backend measurements use a 10-second window; unavailable data is not invented as zero.
- **Switch pools with clear feedback.** HashVault and MoneroOcean presets are included. Switching stops the old worker before starting the new one; a job from the new pool confirms the connection.
- **Track earnings across supported pools.** Inspect confirmed unpaid balances, available pending amounts, total paid and remaining amounts to each pool's payout threshold. Pool balances remain separate.
- **Manage supported payout thresholds.** Read the pool's policy, choose an eligible amount, and verify submitted settings by reading them back. This changes an automatic payout threshold; it does not force an immediate withdrawal.
- **Use a familiar language.** Twenty language presets with flags, saved preferences and mapped reference currencies. Some translations are machine-generated, and newer labels may fall back to English; corrections are welcome.
- **Understand the numbers.** Recent blocks, network statistics, reference prices and theoretical estimates are kept separate from actual pool-credited earnings. Supported hardware power readings are integrated into kWh; missing sensors stay unavailable.

Pool mining is the easiest starting point. Local-node solo and authorized remote-node solo modes are also available for users who understand their node setup. Optional wallet queries require a separately running `monero-wallet-rpc`; the official wallet GUI alone does not expose that interface.

## CPU or CPU + GPU?

Monero's RandomX favors CPUs. Running a GPU alongside a CPU can reduce CPU hashrate through shared power, cooling or memory bandwidth; total performance can fall too. MoneroDesk displays this warning in the app. Compare steady total hashrate and power before deciding to enable GPU mining. More threads or more devices do not guarantee more earnings.

The Windows package includes NVIDIA CUDA and AMD OpenCL backends. RTX 5070 plugin loading and device detection have been tested; a complete GPU accepted-share validation and AMD device testing have not been completed here.

## Fees, privacy and the author allocation

| Item | What to expect |
| --- | --- |
| App | Free and open source. |
| Bundled XMRig developer donation | Set to 0% in the disclosed custom engine source. |
| Author time allocation | Optional 1%, enabled by default; visible and removable on the Mining page. |
| Pool and payout fees | Set by each provider. Reaching a threshold does not guarantee immediate payment. |
| Your information | Enter a public payout address only. The app does not request a seed phrase or private key and does not provide a wallet-transfer function. |

When author allocation is enabled, accumulated mining runtime **20:00–21:00**, then **120:00–121:00**, **220:00–221:00**, and so on uses the author recipient. Pauses stop the clock; normal restarts resume it. CPU and GPU share this schedule. This allocates mining time—not an exact percentage of coins or a transfer from your wallet.

The disclosed author recipient is:

```text
48Rd53h2a9aT1wYnMF6VtVZab189WPVR5jgVf6UedT4iRiLNX91MoA5GydXdu5oMVeSZZCv1H86wKR91V6bBZXCu4LpLusv
```

The public package includes no developer-machine settings, account caches, mining history or credentials. Local settings live in `data/` beside the app; do not publish that folder. Pool queries send the public query address to the selected provider. Reference prices are requested from CoinGecko.

## Compatibility and practical limits

The ready-to-install release is **Windows 10/11 x64**. Linux and other CPU architectures have a native source-build entry and a documented validation status; they are **not all tested or supplied as ready-to-install packages**. See [COMPATIBILITY.md](COMPATIBILITY.md) before building for another device.

Many consumer computers do not expose a whole-system power meter. CPU package power is not whole-computer power, and administrator access cannot create missing sensors. Use an external meter when actual wall consumption is needed.

Earnings are not guaranteed. Estimates are not credited balances, and solo mining may produce no rewards for a long time. This is an independent project, without official endorsement from Monero, XMRig or the listed pools.

## Inspect, build and contribute

The desktop interface, native build helpers, C# installer source, corresponding modified mining-engine/plugin source and third-party notices are available in this repository.

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build.ps1
python tests/test_public_defaults.py
```

The GUI build produces `dist/MoneroDesk/`; keep its `engine/` folder beside the executable. For Linux/native architecture builds, follow [COMPATIBILITY.md](COMPATIBILITY.md) and `build_native.py`. Build-only dependencies are available under `source/`; users installing the app do not need them.

Contributions that help more people use the app are welcome:

- Improve translations and accessibility.
- Report reproducible pool/API issues with the app version, device model and redacted logs.
- Test native builds on Linux, ARM or RISC-V, clearly separating build success from actual mining results.
- Improve diagnostics, hardware measurements and performance comparisons.

Open an [issue](https://github.com/ckwj59/MoneroDesk/issues) for a bug or feature request, or submit a pull request. Never include private keys, seed phrases, credentials or private account data.

## Security review

[GitHub CodeQL runs](https://github.com/ckwj59/MoneroDesk/actions/workflows/codeql.yml) analyze the Python app, corresponding C/C++ sources and C# installer. Check both the run result and reported findings. A successful scan is not GitHub malware certification or a guarantee of safety; checksums establish file integrity only. See [SECURITY.md](SECURITY.md).

Distributed under [GPL-3.0-or-later](LICENSE). Retain the notices in [THIRD_PARTY.md](THIRD_PARTY.md), `licenses/` and `source/`.
