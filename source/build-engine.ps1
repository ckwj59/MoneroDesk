$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Expand-Archive -LiteralPath '.\xmrig-6.26.0-modified.zip' -DestinationPath '.\src' -Force
Expand-Archive -LiteralPath '.\xmrig-deps-msvc2022-x64.zip' -DestinationPath '.\deps' -Force
cmake -S .\src\xmrig-6.26.0 -B .\build -G 'Visual Studio 18 2026' -A x64 "-DXMRIG_DEPS=$PSScriptRoot/deps/x64" -DWITH_OPENCL=OFF -DWITH_CUDA=OFF -DWITH_MSR=OFF -DWITH_HTTP=ON -DWITH_BENCHMARK=ON -DWITH_HWLOC=ON -DWITH_TLS=ON
if ($LASTEXITCODE -ne 0) { throw 'Configuration failed' }
cmake --build .\build --config Release --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
Write-Output 'Built engine: build\Release\xmrig.exe'
