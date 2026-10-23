$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$tclRuntime = Join-Path $PSScriptRoot 'build/tcl-runtime'
if (Test-Path -LiteralPath $tclRuntime) { Remove-Item -LiteralPath $tclRuntime -Recurse -Force }
Expand-Archive -LiteralPath (Join-Path $PSScriptRoot 'installer/tcl-runtime.zip') -DestinationPath $tclRuntime -Force
$target = Join-Path $PSScriptRoot 'dist/XMR'
$rootPath = (Resolve-Path -LiteralPath $PSScriptRoot).Path.TrimEnd('\') + '\'
$targetPath = [IO.Path]::GetFullPath($target)
if (-not $targetPath.StartsWith($rootPath, [StringComparison]::OrdinalIgnoreCase)) { throw "Refusing to clean outside repository: $targetPath" }
if (Test-Path -LiteralPath $targetPath) { Remove-Item -LiteralPath $targetPath -Recurse -Force }
New-Item -ItemType Directory -Path "$target/engine" -Force | Out-Null
Remove-Item -LiteralPath 'XMR-Engine.spec','XMR.spec' -Force -ErrorAction SilentlyContinue
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) {
    $candidate = Join-Path $env:LOCALAPPDATA 'Programs/Python/Python312/python.exe'
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $pythonExe = $candidate }
}
if (-not $pythonExe) { throw 'Python 3.12 is required to build the desktop application.' }
$existingPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = @((Join-Path $PSScriptRoot 'build/python-deps'), (Join-Path $PSScriptRoot 'engine'), $existingPythonPath) -join ';'
& $pythonExe -m PyInstaller --noconfirm --onefile --name XMR-Engine --distpath "$target/engine" --workpath build/engine --specpath . engine/xmrig_bridge.py
if ($LASTEXITCODE -ne 0) { throw 'Engine build failed' }
& $pythonExe -m PyInstaller --noconfirm --onefile --windowed --name XMR --icon app.ico --add-data 'locales;locales' --add-data 'flags;flags' --add-data 'app.ico;.' --add-data 'app.png;.' --additional-hooks-dir installer/pyinstaller-hooks --hidden-import tkinter --hidden-import _tkinter --distpath $target --workpath build/gui --specpath . app.py
if ($LASTEXITCODE -ne 0) { throw 'GUI build failed' }
foreach($item in @('engine','licenses','source','locales','flags','app.ico','app.png','app.py','portable_support.py','tls_transport.py','system_proxy.py','TLS-TRUST-POLICY.md','LICENSE','README.md','THIRD_PARTY.md','使用说明.txt')) {
    if ($item -eq 'engine') {
        foreach ($name in @('xmrig.exe','xmrig-cuda.dll','nvrtc64_120_0.dll','nvrtc-builtins64_129.dll','xmrig-manifest.json','gpu-manifest.json')) {
            $source = Join-Path 'engine' $name
            if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Required XMRig runtime file is missing: $source" }
            Copy-Item -LiteralPath $source -Destination "$target/engine" -Force
        }
    } else { Copy-Item -LiteralPath $item -Destination $target -Recurse -Force }
}
$xmrigManifest = Get-Content -LiteralPath "$target/engine/xmrig-manifest.json" -Raw | ConvertFrom-Json
$xmrigHash = (Get-FileHash -LiteralPath "$target/engine/xmrig.exe" -Algorithm SHA256).Hash.ToLowerInvariant()
if ($xmrigHash -ne $xmrigManifest.sha256) { throw 'Bundled XMRig hash does not match its source manifest.' }
$gpuManifest = Get-Content -LiteralPath "$target/engine/gpu-manifest.json" -Raw | ConvertFrom-Json
foreach ($property in $gpuManifest.files.PSObject.Properties) {
    $actual = (Get-FileHash -LiteralPath "$target/engine/$($property.Name)" -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $property.Value) { throw "Bundled XMRig GPU file hash mismatch: $($property.Name)" }
}
$manifestPath = Join-Path $target 'engine/manifest.json'
$manifest = [ordered]@{version='XMRig-bridge-1.0';target='windows-x64';developer_donation=0;sha256=(Get-FileHash -LiteralPath "$target/engine/XMR-Engine.exe" -Algorithm SHA256).Hash.ToLowerInvariant();source='XMRig v6.26.0 with authenticated loopback live-config bridge';gpu_backends=@('cuda','opencl')}
[IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))
Write-Output "Build complete: $target/XMR.exe. No mining has been started."
