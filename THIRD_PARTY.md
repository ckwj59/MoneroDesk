# Third-party components

- XMRig 6.26.0: GPL-3.0-or-later. The bundled Windows executable's source archive is in `source/xmrig-6.26.0-modified.zip`, and its license is included in `licenses/xmrig-GPL-3.0.txt`. The archive and manifest identify the source revision and distributed binary hash.
- XMRig CUDA plugin 6.22.1: GPL-3.0-or-later; its license notice is in `licenses/xmrig-cuda-LICENSE`. NVIDIA CUDA runtime DLLs are bundled separately and remain subject to NVIDIA's redistribution terms; the NVIDIA display driver is not included.
- The app's bridge supervises XMRig and uses a random bearer token on an HTTP API bound to `127.0.0.1`; it is project code, not part of upstream XMRig.
- Tcl/Tk 8.6.12 support files are bundled to make the Tkinter interface build reproducibly. Their license terms are included in `licenses/TCL-TK-license.terms`; the source data archive is `installer/tcl-runtime.zip`.
- RandomX source and the independent experimental backend remain in the repository for development/testing but are not used by the Windows installer built by `build.ps1`.
- Python, OpenSSL, psutil, PyCryptodome and PyInstaller: notices are in `licenses/`. PyInstaller's applicable bootloader exception is retained.
- NVIDIA CUDA runtime DLLs are bundled as separate files; redistribution remains subject to NVIDIA CUDA terms. A display driver is not included.
- Original interface and local translations: GPL-3.0-or-later; language notices remain in `locales/`.

Preserve all license notices when redistributing source or binaries. The installer payload includes XMRig, its source archive, CUDA plugin/runtime files, and the corresponding notices.
