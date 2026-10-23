# Compatibility

| Target | Current evidence |
| --- | --- |
| Windows 10/11 x64, CPU rx/0 pool mining | Bundled XMRig 6.26.0; hardware performance depends on system configuration |
| Windows x64, NVIDIA CUDA rx/0 pool mining | Bundled XMRig CUDA plugin; compatible NVIDIA driver and supported device required |
| Windows x64, AMD OpenCL pool mining | XMRig OpenCL backend; compatible system OpenCL runtime/device required; not verified in this build session |
| CPU + GPU pool mining | Supported by XMRig when both backends initialize; shared power/cooling can lower total hashrate |
| Solo mining | The UI has local/remote node options; this session did not verify a mainnet block or solo payout |
| Linux, ARM, RISC-V, 32-bit x86 | No ready-to-install package validated here |

The UI retains its existing pages and settings. The Windows build uses XMRig for the mining engine and the bridge for control/rate reporting. GPU initialization is hardware/driver-dependent. The app uses standard Monero `rx/0` jobs; other algorithms and NiceHash layouts are not supported.
