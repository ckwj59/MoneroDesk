# Security review

GitHub CodeQL analyzes the Python application, C# installer and the corresponding C/C++ engine/plugin source on pushes, pull requests, a weekly schedule, and manual workflow dispatch. The engine source archive is unpacked before analysis. No mining process is started by this workflow.

View runs under **Actions → CodeQL Security Review**, and findings under **Security → Code scanning**. Scan completion, warnings, failures, and open findings must be evaluated before claiming a clean result. A passing run is not a malware certification or a guarantee of safety.

Dependabot checks supported Python dependencies and GitHub Actions versions. It does not audit all statically bundled native libraries or certify the bundled executable. Release installer checksums establish integrity, not safety.

## Reporting a vulnerability

Use the repository's private vulnerability reporting feature if it is available. Do not post credentials, seed phrases, private keys, or exploitable private details in public issues. For non-sensitive concerns, open an issue with the affected version and a minimal reproduction.

## Disclosed mining behavior

Mining starts manually. The main payout field is empty. The public author recipient is visible; optional 1% mining-time allocation is enabled by default and can be disabled. Pool queries transmit the public query address to the relevant pool. The app does not provide a wallet-transfer function.
