HRMS Windows Packaging and Launcher

1. Build executable (Windows):

- Ensure you have a Python environment with `pyinstaller` installed:

```powershell
pip install pyinstaller
```

- Run the build script from the project root:

```powershell
build_exe.bat
```

This will produce `dist\HRMS.exe` (one-file). The `--add-data` flags include `templates`, `static`, and `instance` folders.

2. Create Desktop Shortcut:

- After the build finishes, run:

```powershell
python create_shortcut.py
```

If `pywin32` is available, the script will create a proper `.lnk` shortcut named "HRMS" on the current user's Desktop and use `app.ico` if present. Otherwise it will create a `.url` shortcut as a fallback.

3. Run:

- Double-click the `HRMS` desktop shortcut. This will start the bundled server and open your default browser at `http://127.0.0.1:5000`.

Notes:
- The launcher script is `launcher.py` and will be used as the PyInstaller entrypoint.
- If you prefer a one-folder build to ease runtime file access, modify `build_exe.bat` to remove `--onefile`.
- The SQLite database and uploaded files are read from the bundled `instance` folder; ensure writes are allowed by the executable location or move the DB to a writable location and update `app.config['DATABASE_PATH']` accordingly.
