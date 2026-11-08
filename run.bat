@echo off
setlocal
cd /d "%~dp0backend"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher 'py' was not found. Install Python 3.13 and enable the launcher.
  pause
  exit /b 1
)
py -3.13 --version
if errorlevel 1 (
  echo Python 3.13 is required. Install Python 3.13, then run this file again.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.13 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Backend dependencies could not be installed.
  pause
  exit /b 1
)
python -m uvicorn main:app --reload --port 8000
