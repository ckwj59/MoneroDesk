# Build and inspect

The supplied Windows runtime is ready to run; source builds require Python 3.11+, Tk, CMake, MSVC x64 build tools, and a compatible CUDA Toolkit for NVIDIA builds. No XMRig is needed.

## Python and GUI

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = "$PWD/engine"
python -m unittest discover -s tests -p 'test_*.py'
python tests/verify_distribution.py
python app.py
```

`build.ps1` rebuilds the independent bridge and GUI into `dist/XMR` and refreshes the bridge manifest. Native DLLs are copied from `engine/`; rebuilding native code requires refreshing its corresponding SHA-256 manifests before loading the new DLLs.

## Native dependencies

Extract `engine/RandomX-source.zip` into `native/`; the archive already contains the `RandomX/` top-level folder. Build its pinned source with:

```powershell
cmake -S native/RandomX -B native/build -DBUILD_SHARED_LIBS=ON -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON
cmake --build native/build --config Release --target randomx
cmake -S native/cpu -B native/cpu-build
cmake --build native/cpu-build --config Release
cmake -S native/gpu -B native/gpu-build -DXMR_VM_LANES=32 -DXMR_VM_THREADS=128 -DXMR_VM_CODE_GLOBAL=ON
cmake --build native/gpu-build --config Release
```

The CUDA host adapter includes RandomX headers using this relative layout. CPU CMake links `native/build/Release/randomx.lib`. Preserve precise division/square root, `--fmad=false`, instruction ordering and all correctness checks. Do not enable fast-math or ship unverified candidates. Compiler/toolkit differences may change binary hashes; the supplied hashes describe the distributed binaries, not a bit-for-bit reproducible build promise.

The installer source embeds a `payload.zip` resource compiled with the .NET Framework C# compiler. Its safe extraction, process checks and settings preservation are in `installer/DesktopSetup.cs`. The distributed executable and manifest have been extraction-verified; do not represent a newly rebuilt installer as tested until repeating that verification.
