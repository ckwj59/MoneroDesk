$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m PyInstaller --noconfirm --onefile --windowed --name MoneroDesk --icon "$PSScriptRoot/app.ico" --add-data "$PSScriptRoot/app.ico;." --add-data "$PSScriptRoot/app.png;." --add-data "$PSScriptRoot/locales;locales" --add-data "$PSScriptRoot/flags;flags" --distpath "$PSScriptRoot/dist/MoneroDesk" --workpath "$PSScriptRoot/build" --specpath "$PSScriptRoot/build" "$PSScriptRoot/app.py"
if ($LASTEXITCODE -ne 0) { throw 'GUI build failed' }
foreach($item in @('engine','licenses','source','locales','flags','app.ico','app.png','app.py','README.md','ABOUT.txt','THIRD_PARTY.md','LICENSE','requirements.txt','build.ps1','tests')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $item) -Destination "$PSScriptRoot/dist/MoneroDesk" -Recurse -Force
}
Write-Output 'Build complete: dist/MoneroDesk/MoneroDesk.exe'
