# MoneroDesk

**A Windows desktop workbench for Monero CPU mining, pool monitoring, and payout management.**

MoneroDesk brings mining controls, live pool statistics, price estimates, hardware information, and payout thresholds into one interface. It is designed for people who want visible controls and clear information about where their mining work is sent.

**Windows x64 · 20 interface languages · Multiple pools · Blank main payout field · GPL-3.0-or-later**

## Features and practical advantages

| Feature | What it provides |
| --- | --- |
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

Download the portable Windows package:

- [MoneroDesk v1.0.1 — Windows x64 ZIP](https://github.com/ckwj59/MoneroDesk/raw/refs/heads/main/downloads/MoneroDesk-Windows-x64-v1.0.1.zip)
- [SHA-256 checksum](downloads/SHA256SUMS.txt)
- [Release notes](downloads/RELEASE_NOTES.md)

The downloadable distribution is published in this repository's `downloads/` directory.

1. Extract the complete archive to a writable folder. Keep its directory structure.
2. Run `MoneroDesk.exe`.
3. Enter **your own Monero mainnet payout address**. Never enter a seed phrase or private key.
4. Choose a mining mode and pool or node, then select a CPU percentage.
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
- This distribution mines with the CPU. Its engine is built without CUDA, OpenCL, or MSR support and does not automatically elevate privileges.
- More threads do not necessarily mean better hashrate. Cache, memory, temperature, and scheduling affect results.
- Earnings are not guaranteed. Theoretical estimates do not represent credited income or complete electricity costs. Solo mining may produce no block rewards for a long time.
- Many consumer computers do not expose a valid whole-system power meter. Administrator access cannot create missing sensor data. CPU package power is not treated as whole-computer power. Use an external meter to measure actual wall consumption.
- This is an independent third-party project, not an official product of Monero, XMRig, HashVault, MoneroOcean, or CoinGecko.

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

## Reporting issues

Include the app version, the error type, and a redacted log excerpt. Do not post seed phrases, private keys, RPC passwords, or addresses you do not want to make public.
