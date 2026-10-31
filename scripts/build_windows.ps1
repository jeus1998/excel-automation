$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
  throw "Windows 설치 파일은 Windows에서 빌드해야 합니다. 이 스크립트를 Windows PC에서 실행해 주세요."
}

$venvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m venv .venv
  } else {
    python -m venv .venv
  }
}
& $venvPython -m pip install -e ".[build]"
$env:PYINSTALLER_CONFIG_DIR = Join-Path (Get-Location) ".pyinstaller-cache"
New-Item -ItemType Directory -Path "dist" -Force | Out-Null
if (Test-Path "dist\Container-Workbench-Setup.exe") {
  Remove-Item "dist\Container-Workbench-Setup.exe" -Force
}
& $venvPython -m PyInstaller --clean --noconfirm --windowed `
  --name "Container Workbench" `
  --hidden-import xlrd --hidden-import openpyxl `
  --add-data "resources;resources" `
  main.py

$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $compiler) {
  $defaultCompiler = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
  if (Test-Path $defaultCompiler) {
    $compiler = @{ Source = $defaultCompiler }
  } else {
    throw "Inno Setup is required. Install it from https://jrsoftware.org/isdl.php, then run this script again."
  }
}
& $compiler.Source "installer\windows.iss"
if (-not (Test-Path "dist\Container-Workbench-Setup.exe")) {
  throw "Inno Setup did not create dist\Container-Workbench-Setup.exe."
}
Write-Host "완료: dist\Container-Workbench-Setup.exe"
