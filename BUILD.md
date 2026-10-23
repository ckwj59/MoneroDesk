# Build and inspect

The Windows x64 installer bundles XMRig 6.26.0, its optional CUDA plugin/runtime files, an authenticated loopback control bridge, and the existing desktop UI. Source builds require Python 3.12+, the packages in `requirements.txt`, the .NET Framework C# compiler used by the installer script, and the Tcl/Tk data archive at `installer/tcl-runtime.zip`. The build script collects the Tcl/Tk runtime files and verifies the prebuilt XMRig binary and plugin hashes against their manifests.

## Python and GUI

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = "$PWD/engine"
python -m unittest discover -s tests -p 'test_*.py'
python tests/verify_distribution.py
python app.py
```

`build.ps1` rebuilds the bridge and GUI into `dist/XMR`, then verifies the bundled XMRig and GPU plugin hashes. On Windows, run `powershell -File installer/build_installer.ps1` to create the single-file setup executable in `downloads/`, refresh its checksum, and verify both archive contents and extraction. The installer places the app under the current user's LocalAppData and creates a desktop shortcut; it does not start mining.

The runtime XMRig executable and CUDA plugin are prebuilt third-party binaries, not rebuilt by `build.ps1`. The installer includes the corresponding XMRig source archive and license notices. The CUDA plugin still requires a compatible NVIDIA display driver; the package does not install drivers or alter system permissions.

The installer source embeds a `payload.zip` resource compiled with the .NET Framework C# compiler. Its safe extraction, process checks and settings preservation are in `installer/DesktopSetup.cs`. A newly rebuilt installer is ready only after `installer/build_installer.ps1` completes its extraction/hash verification.
