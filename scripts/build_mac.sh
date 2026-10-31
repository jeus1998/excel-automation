#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
PYTHON=.venv/bin/python
"$PYTHON" -m pip install -e '.[build]'
export PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache"
"$PYTHON" -m PyInstaller --clean --noconfirm --windowed \
  --name "Container Workbench" \
  --hidden-import xlrd --hidden-import openpyxl \
  --add-data "resources:resources" \
  main.py

mkdir -p dist
python3 -c 'from pathlib import Path; Path("dist/Container-Workbench-macOS.dmg").unlink(missing_ok=True)'
hdiutil create -volname "Container Workbench" \
  -srcfolder "dist/Container Workbench.app" \
  -ov -format UDZO "dist/Container-Workbench-macOS.dmg"
python3 -c 'from pathlib import Path; import shutil; shutil.rmtree(Path("dist/Container Workbench.app"), ignore_errors=True)'
echo "완료: dist/Container-Workbench-macOS.dmg"
