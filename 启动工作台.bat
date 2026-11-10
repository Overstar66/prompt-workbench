@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

netstat -ano | findstr ":8901" | findstr "LISTENING" >nul
if not errorlevel 1 goto openpage

echo 正在启动提示词工作台...
set "PYRUN="

if exist "%~dp0python_path.txt" (
  for /f "usebackq tokens=*" %%a in ("%~dp0python_path.txt") do set "PYRUN=%%a"
  if exist "!PYRUN!" goto launch
  set "PYRUN="
)

where py >nul 2>nul
if not errorlevel 1 (
  set "PYRUN=py -3"
  goto launch
)

for /f "delims=" %%p in ('where python 2^>nul') do (
  echo %%p | findstr /i "WindowsApps" >nul
  if errorlevel 1 (
    set "PYRUN=%%p"
    goto launch
  )
)

for %%d in (
  "%LocalAppData%\Programs\Python\Python313\python.exe"
  "%LocalAppData%\Programs\Python\Python312\python.exe"
  "%LocalAppData%\Programs\Python\Python311\python.exe"
  "%LocalAppData%\Programs\Python\Python310\python.exe"
  "C:\Python313\python.exe"
  "C:\Python312\python.exe"
  "C:\Python311\python.exe"
  "C:\Python310\python.exe"
) do (
  if exist "%%~d" (
    set "PYRUN=%%~d"
    goto launch
  )
)

echo.
echo [错误] 没有找到可用的 Python。
echo.
echo   1. 安装 Python 3.10+：https://www.python.org/downloads/
echo      安装时勾选 "Add Python to PATH"
echo   2. 如果已经装了，把 pythonw.exe 的完整路径写进
echo      本目录下的 python_path.txt（一行即可）
echo.
pause
exit /b 1

:launch
start "" %PYRUN% "%~dp0app.py"
ping -n 5 127.0.0.1 >nul

:openpage
start "" "http://127.0.0.1:8901"
