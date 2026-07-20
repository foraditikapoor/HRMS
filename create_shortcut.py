import os
import sys

exe_name = 'HRMS.exe'
# Typical PyInstaller output
potential_paths = [
    os.path.join('dist', exe_name),
    os.path.join('dist', 'HRMS', exe_name),
]
exe_path = None
for p in potential_paths:
    if os.path.exists(p):
        exe_path = os.path.abspath(p)
        break

if exe_path is None:
    print('Executable not found in dist/. Run the build script first.')
    sys.exit(1)

desktop = os.path.join(os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop'))
shortcut_path = os.path.join(desktop, 'HRMS.lnk')
icon_path = os.path.abspath('app.ico') if os.path.exists('app.ico') else None

# Try using win32com if available
try:
    import pythoncom
    from win32com.shell import shell, shellcon
    from win32com.client import Dispatch

    shell_link = Dispatch('WScript.Shell').CreateShortCut(shortcut_path)
    shell_link.Targetpath = exe_path
    shell_link.WorkingDirectory = os.path.dirname(exe_path)
    if icon_path:
        shell_link.IconLocation = icon_path
    shell_link.save()
    print('Shortcut created at', shortcut_path)
except Exception as e:
    # Fallback: create an Internet Shortcut (.url) which opens the exe
    url_shortcut = os.path.join(desktop, 'HRMS.url')
    with open(url_shortcut, 'w') as f:
        f.write('[InternetShortcut]\n')
        f.write('URL=file:///' + exe_path.replace('\\', '/') + '\n')
        if icon_path:
            f.write('IconFile=' + icon_path.replace('\\', '/') + '\n')
    print('Could not create .lnk shortcut (missing pywin32). Created .url at', url_shortcut)
