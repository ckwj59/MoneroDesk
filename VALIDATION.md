# Local validation evidence

These are historical local tests of the shipped engine, not GitHub scan results or guaranteed performance.

| Check | Result |
| --- | --- |
| GPU paired benchmark, before/current | 346.76 / 491.995 H/s mean; +41.88%; 8,192 hashes checked, zero mismatches |
| GPU-only MoneroOcean verified TLS | About 65.5 seconds; 3 accepted / 0 rejected |
| CPU MoneroOcean verified TLS through enabled local proxy | About 166 seconds; 30 accepted / 0 rejected |
| HashVault verified TLS | About 166 seconds; 3 accepted / 0 rejected |
| Follow-up GPU grouping trials | 24,576 hashes checked, zero mismatches; no effective additional speedup; not shipped |
| Installer payload/extraction | Every manifest hash checked; no data/ directory included |

GPU trials used an NVIDIA GeForce RTX 5070 Laptop. Inputs and elapsed timing are controlled in local comparisons; live pool jobs and rolling windows vary. Short tests do not establish long-term stability, profitability or a device performance ceiling. Current GitHub checks must be read in Actions/Security, separately from this document.
