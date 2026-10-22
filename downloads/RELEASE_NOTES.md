# XMR independent engine preview

- Replaces the previous XMRig runtime with the independent CPU/CUDA pool engine, preserving the original desktop UI.
- Includes verified TLS/system-local-proxy routing, cancellable recovery, separate CPU/GPU rates and one-second reporting.
- Ships only the validated 128-thread / 32-lane GPU kernel. Additional grouping trials did not produce a meaningful improvement and are not included.
- Main payout address remains blank on a clean installation; disclosed optional 1% author time allocation remains enabled by default.
- Removes the obsolete installer and XMRig source/binaries from the current branch. Git history is retained.
- Experimental Windows x64/NVIDIA support; see COMPATIBILITY.md. No safety certification or performance guarantee is claimed.

This is the same validated desktop installer; SHA-256 is listed in SHA256SUMS.txt.
