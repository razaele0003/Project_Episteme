@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run the setup commands in README.md first.
  pause
  exit /b 1
)
start "" http://127.0.0.1:8766
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8766 --no-proxy-headers --no-access-log

