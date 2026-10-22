# Compatibility

| Target | Current evidence |
| --- | --- |
| Windows 10/11 x64, CPU rx/0 pool mining | Packaged; local accepted-share validation |
| Windows x64, NVIDIA CUDA rx/0 pool mining | Experimental; tested on RTX 5070 Laptop; compatible driver required |
| CPU + NVIDIA CUDA pool mining | Local accepted-share validation; may reduce total efficiency |
| CPU local/authorized remote-node solo | Simulated protocol/submission tests only; no demonstrated mainnet block |
| AMD OpenCL / GPU solo | Not implemented in this independent package; explicitly rejected |
| Linux, ARM, RISC-V, 32-bit x86 | No ready-to-install or fully validated package supplied |

The UI retains its original pages and settings. A selectable control does not imply that every platform/backend combination is implemented. No XMRig fallback is supplied. The app uses standard rx/0 jobs; algorithm switching, RandomX V2 and NiceHash layouts are not supported.
