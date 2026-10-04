@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Python 3.11+ wurde nicht gefunden. & pause & exit /b 1)
if not exist .venv\Scripts\python.exe python -m venv .venv
if errorlevel 1 (pause & exit /b 1)
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (pause & exit /b 1)
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onefile --name "The Lobby Control Center" main.py
if errorlevel 1 (pause & exit /b 1)
echo Fertig: dist\The Lobby Control Center.exe
pause
