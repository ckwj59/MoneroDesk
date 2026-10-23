# Local validation evidence

The Windows package in this repository uses the bundled XMRig 6.26.0 CPU/GPU engine through the project's authenticated loopback bridge. The results below describe checks run locally; they are not a performance guarantee, security certification, or GitHub scan result.

| Check | Result |
| --- | --- |
| XMRig CPU benchmark | 9,669.6 H/s final rate; 9,862.3 H/s observed rolling peak |
| Benchmark settings | Ryzen 9 8940HX, 32 threads, `--bench=1M`, RandomX fast mode, huge pages explicitly disabled |
| Benchmark duration | About 103 seconds |
| Unit and bridge tests | 48 tests passed |
| Installer payload | SHA-256 manifest checked; extraction test must pass in `installer/build_installer.ps1` |

This benchmark was run with huge pages disabled and is not a prediction of every app session. The app requests huge pages, but Windows permissions, BIOS settings, power mode, memory configuration, cooling, GPU load, and background work affect the sustained rate. GPU mining has not been benchmarked in this validation run. A stable 15,000 H/s result is not established.

Pool acceptance depends on the selected pool, wallet, TLS endpoint, and job availability. A local bridge test or successful GUI launch does not prove pool connectivity. Review the live XMRig log and accepted/rejected share counters when testing a pool.

GitHub CodeQL and other workflow results should be reviewed directly in the repository's Security/Actions pages. Passing local tests does not certify the application as secure.
