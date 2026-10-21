# MoneroDesk

**A Windows desktop workbench for Monero CPU/GPU mining, pool monitoring, and payout management.**

MoneroDesk brings mining controls, live pool statistics, price estimates, hardware information, and payout thresholds into one interface. It is designed for people who want visible controls and clear information about where their mining work is sent.

**Windows x64 · 20 interface languages · Multiple pools · Blank main payout field · GPL-3.0-or-later**

## Features and practical advantages

| Feature | What it provides |
| --- | --- |
| CPU and GPU controls | Separate CPU/GPU checkmark buttons, measured backend hashrates over a 10-second window, combined total, and visible GPU startup logs. Both backends share the selected pool, wallet and optional allocation schedule. |
| Bundled NVIDIA runtime | The installer contains the CUDA 12.9 XMRig plugin and NVRTC runtime libraries. A compatible vendor display driver is still required; no separate CUDA Toolkit download is needed. |
| Visible mining controls | Start and stop manually; monitor local hashrate, accepted shares, connection status, runtime, and activity logs. |
| Three mining modes | Local-node solo mining, authorized remote-node solo mining, and pool mining. HashVault and MoneroOcean presets are included. |
| Controlled pool switching | Stop the previous worker and wait for it to exit before starting the new pool. A new mining job confirms the connection. Live statistics follow the actual running target. |
| Multiple-pool earnings | View confirmed unpaid balance, pending earnings where available, total paid, current account threshold, minimum permitted threshold, and remaining amount for each pool separately. |
| Automatic payout settings | Read the pool's current policy, enter an XMR threshold or use its minimum, then submit and verify the value by reading it back. |
| CPU percentage controls | Detect the local CPU and translate a percentage into an appropriate logical-thread count. Display physical cores and cache-related information. |
| 20 languages with flags | Follow the Windows UI language on first launch, or save a manual language selection for later sessions. The app title follows the saved language. |
| Matching display currencies | Show actual JPY quotes for Japanese, CNY for Chinese, and other mapped currencies with explicit ISO codes. Retain a USD price reference. Missing quotes are not relabeled as another currency. |
| Chain statistics and estimates | Query recent blocks, network hashrate, hashrate share, and theoretical earnings. Estimated earnings remain separate from actual credited balances. |
| Hardware-based energy readings | Request whole-computer power from the Windows power-meter interface and integrate valid samples into kWh. Unsupported readings are shown as unavailable. |
| Clean public defaults | The main payout field starts empty. The visible author recipient is prefilled and optional 1% time allocation is enabled by default. No personal configuration, account cache, or mining history is shipped. |

## Download and run

Download the single-file installer (no manual extraction of runtime files):

- [Download MoneroDesk v1.1.0 — Windows x64 installer (.exe)](https://github.com/ckwj59/MoneroDesk/raw/refs/heads/main/downloads/MoneroDesk-Windows-x64-v1.1.0-Setup.exe)
- [SHA-256 checksum](downloads/SHA256SUMS.txt)
- [Release notes](downloads/RELEASE_NOTES.md)

The downloadable distribution is published in this repository's `downloads/` directory.

1. Close an existing MoneroDesk GPU session, then run `MoneroDesk-Windows-x64-v1.1.0-Setup.exe`.
2. Confirm installation, then open the **Monero Desk GPU** desktop shortcut. The installer uses `%LOCALAPPDATA%/MoneroDesk-GPU`, preserves existing settings, and keeps a separate D-drive installation intact.
3. Enter **your own Monero mainnet payout address**. Never enter a seed phrase or private key.
4. Pool mining is the initial default. Enter your payout address, select a pool and CPU percentage. CPU and GPU have separate checkmark controls; GPU is off by default. Select NVIDIA CUDA or AMD OpenCL when enabling GPU.
5. Read the disclosure and click **Start mining**. The app does not start mining automatically at Windows startup.
6. Open **Price & earnings** to inspect supported pools, or **Live pool data** to manage the corresponding automatic payout threshold.

Pool balances are settled separately and cannot be combined across providers. Reaching a threshold does not guarantee immediate payment; the pool schedules payouts and may charge network fees.

Optional local-wallet balance queries require a separately running `monero-wallet-rpc` service. The official wallet GUI alone does not expose that wallet RPC interface.

## Language preferences

The first launch follows the Windows UI language. A manual selection is saved under `data/settings.json` and restored on subsequent launches, including the window title and reference currency. Select **Follow system language** to return to automatic detection.

When running the packaged executable, the app also updates an existing desktop shortcut that targets that exact executable so its name and description follow the selected language. It does not rename unrelated shortcuts or replace an existing file with the same name.

Some translations are machine-generated. Translation corrections are welcome.

## Privacy, fees, and optional time allocation

- The main payout address is empty. Each user must enter their own main address.
- The publicly disclosed author allocation recipient is `48Rd53h2a9aT1wYnMF6VtVZab189WPVR5jgVf6UedT4iRiLNX91MoA5GydXdu5oMVeSZZCv1H86wKR91V6bBZXCu4LpLusv`. This is a public receiving address, not a private key.
- No developer-machine `data/`, logs, pool account caches, energy history, or session records are included.
- Optional 1% mining-time allocation is **enabled by default** and shown on the Mining page. Users can uncheck it before starting; it is not hidden or mandatory.
- When enabled, the recipient receives the 20:00–21:00 window of accumulated mining runtime, then 120:00–121:00, 220:00–221:00, and so on: one minute per 100 minutes. Pauses stop the clock; normal restarts resume it. This allocates mining time, not an exact amount of coins.
- The bundled custom XMRig engine has its developer donation level set to zero. Pool fees and payout network fees remain provider-controlled.
- Settings are stored locally in `data/` beside the app. Do not upload that directory to a public repository.
- Pool queries send the public query address to the selected provider. Prices are requested from CoinGecko. The app does not request seed phrases or private keys and does not include a wallet-transfer function.

## Scope and limitations

- Windows 10/11 x64. The source development environment uses Python 3.11.
- This Windows x64 distribution includes CPU, CUDA and OpenCL backends, with MSR support disabled. The GPU plugin and matching runtime libraries are bundled; the installer does not install display drivers or automatically start mining.
- **GPU efficiency:** Monero RandomX favors CPUs. CPU/GPU mining together may reduce CPU and total hashrate through shared power, cooling or bandwidth. Compare stable measurements; adding a GPU does not guarantee more earnings.
- Windows x64 has been device-tested. Linux and other CPU architectures have a native source-build entry only; they have not been runtime-validated here. See [compatibility and native builds](COMPATIBILITY.md). Windows ARMv7/RISC-V installers and a Linux GPU runtime bundle are not supplied.
- More threads do not necessarily mean better hashrate. Cache, memory, temperature, and scheduling affect results.
- Earnings are not guaranteed. Theoretical estimates do not represent credited income or complete electricity costs. Solo mining may produce no block rewards for a long time.
- Many consumer computers do not expose a valid whole-system power meter. Administrator access cannot create missing sensor data. CPU package power is not treated as whole-computer power. Use an external meter to measure actual wall consumption.
- This is an independent third-party project, not an official product of Monero, XMRig, HashVault, MoneroOcean, or CoinGecko.

## Security scan status

[View GitHub CodeQL runs](https://github.com/ckwj59/MoneroDesk/actions/workflows/codeql.yml). CodeQL checks Python, corresponding C/C++ sources and the C# installer. Scan findings are separate from a successful workflow run. This project does not claim GitHub malware certification, code-signing certification, or guaranteed safety.

## Build from source

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The output is `dist/MoneroDesk/`. Keep `engine/` beside the executable.

- `app.py`: desktop application source.
- `locales/`, `flags/`, `app.ico`, `app.png`: interface resources.
- `engine/manifest.json`: the exact bundled engine SHA-256, checked before starting a worker.
- `source/`: complete modified engine source archive, dependency archive, modification notes, and rebuild script.
- `licenses/`: third-party license notices.

The build does not copy local runtime data. Run the offline public-default checks before distributing:

```powershell
python tests/test_public_defaults.py
```

## License and upstream projects

Distributed under [GNU GPL v3 or later](LICENSE). Retain all applicable upstream copyright and license notices. See [THIRD_PARTY.md](THIRD_PARTY.md), `licenses/`, and the corresponding engine source in `source/`.

- [Monero](https://www.getmonero.org/)
- [XMRig](https://github.com/xmrig/xmrig)
- [HashVault API](https://hashvault.pro/monero/api)
- [MoneroOcean frontend and API usage](https://github.com/MoneroOcean/mo-pool-ui)
- [CoinGecko price API](https://docs.coingecko.com/reference/simple-price)

## Automated security review

[CodeQL runs](https://github.com/ckwj59/MoneroDesk/actions/workflows/codeql.yml) analyze the Python app and unpacked C/C++ engine source. Findings appear under Security → Code scanning. Dependabot monitors supported dependencies and Actions versions. See [SECURITY.md](SECURITY.md) for scope and limitations. Scan status must be checked; this is not a malware safety certification.

## Reporting issues

Include the app version, the error type, and a redacted log excerpt. Do not post seed phrases, private keys, RPC passwords, or addresses you do not want to make public.
