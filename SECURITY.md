# Security policy and review scope

Use the repository Security reporting tools for a sensitive report, or open an issue with redacted details. Never post seed phrases, private keys, passwords or full local account files.

The app uses verified TLS for remote mining. Known pool certificate pins are explicit in `TLS-TRUST-POLICY.md`; an unexpected certificate is not automatically trusted. The local HTTP proxy route is limited to an already-enabled loopback endpoint. The app does not install a proxy, change DNS, disable antivirus, install an MSR driver or modify system security policy.

## Automated checks

- GitHub CodeQL: Python, C/C++ and C# source analysis, with security-extended queries. Pinned RandomX source is unpacked into the analysis tree; CUDA `.cu` device-code coverage is not comprehensive.
- CI: installer/DLL checksum verification, blank main address and visible author-allocation defaults, protocol parsing, TLS failure/retry and recovery tests. These tests use local simulated servers, not paid GitHub-hosted mining workloads.
- Dependabot: pip requirements and GitHub Actions update monitoring.

An analysis job that succeeds can still report findings. Inspect the Security/code-scanning tab as well as Actions. Missing or failed analysis is not a clean result. Automated scanning is not a GitHub certification, a complete malware analysis, or a guarantee of safety. Executables are not represented as signed or independently audited.

Old implementation files are removed from current main because they are no longer used, not to suppress findings. Historical alerts are left to GitHub's normal analysis lifecycle; no alerts are manually dismissed as false positives by this release.
