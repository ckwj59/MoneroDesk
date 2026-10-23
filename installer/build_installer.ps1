$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$payloadRoot = Join-Path $root 'dist/XMR'
$buildRoot = Join-Path $root 'build/installer'
$downloads = Join-Path $root 'downloads'
$payloadZip = Join-Path $buildRoot 'payload.zip'
$setup = Join-Path $downloads 'XMR-CPU-GPU-Windows-x64-Setup.exe'
$setupSource = Join-Path $PSScriptRoot 'DesktopSetup.cs'
$icon = Join-Path $root 'app.ico'

foreach ($required in @((Join-Path $payloadRoot 'XMR.exe'), (Join-Path $payloadRoot 'engine/XMR-Engine.exe'), $setupSource, $icon)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Required build file is missing: $required" }
}

$files = @(Get-ChildItem -LiteralPath $payloadRoot -Recurse -File -Force | Sort-Object FullName)
if (-not $files.Count) { throw 'The distribution folder is empty.' }
$manifest = [ordered]@{}
foreach ($file in $files) {
    $relative = $file.FullName.Substring($payloadRoot.Length).TrimStart('\').Replace('\', '/')
    if ($relative -match '(^|/)data(/|$)') {
        throw "Refusing to package user runtime data: $relative"
    }
    $manifest[$relative] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
}

New-Item -ItemType Directory -Path $buildRoot, $downloads -Force | Out-Null
if (Test-Path -LiteralPath $payloadZip) { Remove-Item -LiteralPath $payloadZip -Force }
Add-Type -AssemblyName System.IO.Compression
$fileStream = [System.IO.File]::Create($payloadZip)
$archive = [System.IO.Compression.ZipArchive]::new($fileStream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
try {
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($payloadRoot.Length).TrimStart('\').Replace('\', '/')
        $entry = $archive.CreateEntry($relative, [System.IO.Compression.CompressionLevel]::Optimal)
        $input = [System.IO.File]::OpenRead($file.FullName)
        $output = $entry.Open()
        try { $input.CopyTo($output) }
        finally { $output.Dispose(); $input.Dispose() }
    }
    $manifestEntry = $archive.CreateEntry('payload-manifest.json', [System.IO.Compression.CompressionLevel]::Optimal)
    $manifestStream = $manifestEntry.Open()
    $manifestWriter = [System.IO.StreamWriter]::new($manifestStream, [System.Text.UTF8Encoding]::new($false))
    try { $manifestWriter.Write(($manifest | ConvertTo-Json -Depth 10)) }
    finally { $manifestWriter.Dispose() }
}
finally { $archive.Dispose() }

$compilerCandidates = @(
    'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
    'C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe'
)
$compiler = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $compiler) { throw 'The .NET Framework C# compiler (csc.exe) is required to build the installer.' }
$compilerArgs = @(
    '/nologo', '/target:winexe', "/win32icon:$icon", "/resource:$payloadZip,payload.zip",
    "/out:$setup", '/reference:System.Windows.Forms.dll', '/reference:System.IO.Compression.dll',
    '/reference:Microsoft.CSharp.dll', $setupSource
)
& $compiler @compilerArgs
if ($LASTEXITCODE -ne 0) { throw "Installer compilation failed with exit code $LASTEXITCODE." }

$installerHash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant()
$sumPath = Join-Path $downloads 'SHA256SUMS.txt'
[System.IO.File]::WriteAllText($sumPath, "$installerHash  XMR-CPU-GPU-Windows-x64-Setup.exe`n", [System.Text.Encoding]::ASCII)

python (Join-Path $root 'tests/verify_distribution.py')
if ($LASTEXITCODE -ne 0) { throw 'Distribution verification failed.' }

$extractRoot = Join-Path $buildRoot ('extract-' + [Guid]::NewGuid().ToString('N'))
$extractArguments = '--extract-test "{0}"' -f $extractRoot
$extractProcess = Start-Process -FilePath $setup -ArgumentList $extractArguments -Wait -PassThru -NoNewWindow
if ($extractProcess.ExitCode -ne 0) { throw "Installer extraction test failed with exit code $($extractProcess.ExitCode)." }
foreach ($relative in $manifest.Keys) {
    $extracted = Join-Path $extractRoot ($relative.Replace('/', '\'))
    if (-not (Test-Path -LiteralPath $extracted -PathType Leaf)) { throw "Installer omitted file: $relative" }
    $actual = (Get-FileHash -LiteralPath $extracted -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $manifest[$relative]) { throw "Extracted file hash mismatch: $relative" }
}

$setupInfo = Get-Item -LiteralPath $setup
Write-Output "Installer ready: $($setupInfo.FullName)"
Write-Output "Size: $($setupInfo.Length) bytes; SHA-256: $installerHash"
Write-Output "Extraction check passed: $($manifest.Count) payload files."
