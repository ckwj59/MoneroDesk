$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$target = Join-Path $PSScriptRoot 'dist/XMR'
New-Item -ItemType Directory -Path "$target/engine" -Force | Out-Null
python -m PyInstaller --noconfirm --onefile --name XMR-Engine --distpath "$target/engine" --workpath build/engine --specpath build engine/legacy_bridge.py
if ($LASTEXITCODE -ne 0) { throw 'Engine build failed' }
python -m PyInstaller --noconfirm --onefile --windowed --name XMR --icon app.ico --add-data 'locales;locales' --add-data 'flags;flags' --add-data 'app.ico;.' --add-data 'app.png;.' --distpath $target --workpath build/gui --specpath build app.py
if ($LASTEXITCODE -ne 0) { throw 'GUI build failed' }
foreach($item in @('engine','licenses','source','locales','flags','app.ico','app.png','app.py','portable_support.py','tls_transport.py','system_proxy.py','TLS-TRUST-POLICY.md','LICENSE','README.md','THIRD_PARTY.md')) {
    if ($item -eq 'engine') {
        Get-ChildItem -LiteralPath engine -File | Where-Object Name -ne 'XMR-Engine.exe' | Copy-Item -Destination "$target/engine" -Force
    } else { Copy-Item -LiteralPath $item -Destination $target -Recurse -Force }
}
$manifestPath = Join-Path $target 'engine/manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifest.sha256 = (Get-FileHash -LiteralPath "$target/engine/XMR-Engine.exe" -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))
Write-Output "Build complete: $target/XMR.exe. No mining has been started."
