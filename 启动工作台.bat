@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem 如果 8901 已在监听，直接打开浏览器
netstat -ano | findstr ":8901" | findstr "LISTENING" >nul
if errorlevel 1 (
  echo 正在启动提示词工作台...

  rem 优先用 pythonw（无控制台窗口）
  where pythonw >nul 2>nul
  if not errorlevel 1 (
    start "" pythonw "%~dp0app.py"
    goto wait
  )

  rem 其次 py 启动器
  where py >nul 2>nul
  if not errorlevel 1 (
    start "" py -3 "%~dp0app.py"
    goto wait
  )

  rem 最后 python
  where python >nul 2>nul
  if not errorlevel 1 (
    start "" python "%~dp0app.py"
    goto wait
  )

  echo [错误] 没有找到 Python。请安装 Python 3.10+ 并勾选 Add to PATH。
  echo        或手动运行: python "%~dp0app.py"
  pause
  exit /b 1
)

:wait
ping -n 4 127.0.0.1 >nul
start "" "http://127.0.0.1:8901"
