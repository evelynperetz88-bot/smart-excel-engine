# PyInstaller spec — bundles the FastAPI backend into a single Windows .exe.
#
# Usage (from backend/):
#   ..\.venv\Scripts\pip.exe install pyinstaller
#   ..\.venv\Scripts\pyinstaller.exe packaging\build_exe.spec --noconfirm
#
# After build, the executable lives at: dist/SmartExcelEngine/SmartExcelEngine.exe
# Run it; it serves the API on http://127.0.0.1:8765 .
#
# To package the *complete* desktop app (UI + backend) you have two options:
#   1) Embed the built frontend (npm run build) into the executable and have
#      FastAPI serve it as static files (mount StaticFiles at "/").
#   2) Wrap the backend exe with Tauri or Electron — see packaging/README.md.

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

datas = []
binaries = []
hiddenimports = []

for pkg in ("reportlab", "openpyxl", "docx", "bidi"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

datas.append((os.path.join(project_root, "builtin_templates"), "builtin_templates"))

a = Analysis(
    [os.path.join(project_root, "app.py")],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on", "uvicorn.lifespan.off",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts,
    name="SmartExcelEngine",
    console=True,
    icon=None,
    debug=False,
    strip=False,
    upx=True,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=True,
    name="SmartExcelEngine",
)
