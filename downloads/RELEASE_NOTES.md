# XMR Windows x64 release

- Restores the bundled XMRig 6.26.0 CPU engine and supported GPU backends behind the existing desktop interface.
- Keeps verified TLS routing, pool recovery, the disclosed author-allocation control and separate CPU/GPU rates.
- Uses an authenticated, random-token XMRig control API bound to loopback for live wallet/pool reconfiguration without a full miner restart.
- Main payout address remains blank on a clean installation; disclosed optional 1% author time allocation remains enabled by default.
- Includes the XMRig source archive, GPL notices, CUDA plugin and corresponding runtime files. A compatible display driver is required.
- No sustained hashrate or earnings guarantee is claimed; verify stability and thermal/power limits on your own hardware.

The setup executable embeds the current `dist/XMR` build. Its SHA-256 is listed in `SHA256SUMS.txt`; regenerate it with `installer/build_installer.ps1` after changing the build output.
