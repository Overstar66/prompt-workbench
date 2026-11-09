@echo off
cd /d "%~dp0"
netstat -ano | findstr ":8901" >nul
if errorlevel 1 (
  start "" "D:\Dsh-project\ComfyUI_windows_portable\python_embeded\pythonw.exe" "%~dp0app.py"
  ping -n 4 127.0.0.1 >nul
)
start "" "http://127.0.0.1:8901"
