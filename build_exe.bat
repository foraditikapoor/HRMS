@echo off
pyinstaller --noconfirm --clean --onefile --add-data "templates;templates" --add-data "instance;instance" --name HRMS launcher.py
pause

