# Packaging Smart Excel Engine

## Option A — Standalone backend EXE (PyInstaller)

```powershell
cd C:\Users\Mitchashvim\ExcelConverter\backend
.\.venv\Scripts\pip.exe install pyinstaller
.\.venv\Scripts\pyinstaller.exe packaging\build_exe.spec --noconfirm
```

This produces `dist\SmartExcelEngine\SmartExcelEngine.exe`. Run it once and visit `http://127.0.0.1:8765/api/health`. Distribute the entire `dist\SmartExcelEngine` folder.

## Option B — Bundle UI into the EXE (recommended for end-users)

1. Build the frontend:
   ```powershell
   cd ..\frontend
   npm run build       # outputs dist\
   ```
2. In `backend\app.py`, add:
   ```python
   from fastapi.staticfiles import StaticFiles
   app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="ui")
   ```
3. Run PyInstaller spec; add the frontend dist to the `datas` list in `build_exe.spec`:
   ```python
   datas.append((os.path.join(project_root, "..", "frontend", "dist"), "frontend_dist"))
   ```
   And update `app.py` to read from the bundled path when frozen (use `sys._MEIPASS`).

## Option C — Tauri wrapper (lightest, native window)

1. Install Rust and `cargo install tauri-cli`.
2. From the project root: `cargo tauri init --ci --app-name "Smart Excel Engine" --window-title "Smart Excel Engine"`.
3. In `tauri.conf.json` set `"build": { "beforeDevCommand": "npm run dev --prefix frontend", "devPath": "http://localhost:5173", "frontendDist": "../frontend/dist" }`.
4. Spawn the Python backend as a sidecar — see Tauri sidecar docs.
5. `cargo tauri build` produces an MSI installer.

## Option D — Electron wrapper

Similar to Tauri but Node-based. `electron-builder` config example:

```json
{
  "appId": "com.smartexcel.engine",
  "directories": { "output": "release" },
  "files": ["frontend/dist/**", "backend-exe/**"],
  "extraResources": ["backend-exe/SmartExcelEngine.exe"]
}
```

The Electron main process spawns `SmartExcelEngine.exe` and points the `BrowserWindow` at `http://127.0.0.1:8765/`.
