# Third-party components

- Upstream RandomX, commit recorded in `engine/randomx-manifest.json`: BSD-3-Clause. License and corresponding source archive are included in `engine/`.
- Standalone SChernykh/RandomX_CUDA AES/Blake helpers and the independent CUDA adapter: GPL-3.0-or-later. Source is in `native/` and `source/CUDA-source.zip`; notices are preserved. These are not the XMRig engine or its plugin API.
- Python, OpenSSL, psutil, PyCryptodome and PyInstaller: notices are in `licenses/`. PyInstaller's applicable bootloader exception is retained.
- NVIDIA's CUDA runtime is linked into the native GPU library; redistribution remains subject to NVIDIA CUDA terms. A display driver is not included.
- Original interface and local translations: GPL-3.0-or-later; language notices remain in `locales/`.

Preserve all license notices when redistributing source or binaries. This release has no XMRig executable, plugin or source dependency; previous Git history may contain the former implementation.
