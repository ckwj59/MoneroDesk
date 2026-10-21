# Security remediation — 2026-10-22

The previous CodeQL analysis reported 34 open findings. This change addresses the
reported source locations; **the new scan must be reviewed before claiming closure**.

- Bound floating-point XML formatting and serialize distance entries with checked lengths.
- Validate distance-matrix index and byte ranges before allocation; widen multiplication before use.
- Validate CUDA launch dimensions and scratchpad address-space limits.
- Match GPU diagnostic format arguments to their actual types.
- Strictly parse PCI hexadecimal components and check bitmap parsing failures.
- Accept inline HWLOC_PCI_LOCALITY mappings only; environment-selected file reads are removed.
- Create TLS key/certificate and XML export files with owner-restricted permissions.
  Existing files are refused rather than overwritten, preventing symlink/overwrite races.
- Use correctly typed KawPow node storage and RAII for RandomX cache-construction cleanup.
- Remove the redundant constant pool-password field from generated disk configuration;
  the engine's existing non-secret default remains unchanged. Payout addresses are public data.

Native Windows x64 regression checks passed for overflow rejection, strict parsing,
protected file creation and maximum-integer XML export/import. The modified engine compiled.
No alerts were manually dismissed, and no third-party source directories were excluded.
This is not a security certification or a guarantee that all defects are absent.
