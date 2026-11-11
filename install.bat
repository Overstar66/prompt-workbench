@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   提示词工作台 - 安装向导
echo ============================================
echo.

rem ---------- 1. 检测 Python ----------
echo [1/5] 检测 Python...
set "PY="
where pythonw >nul 2>nul && set "PY=pythonw"
where py >nul 2>nul && set "PY=py -3"
where python >nul 2>nul && if not defined PY set "PY=python"

if not defined PY (
  echo.
  echo [错误] 没有检测到 Python。
  echo.
  echo   请先安装 Python 3.10 或更高版本：
  echo   https://www.python.org/downloads/
  echo.
  echo   安装时务必勾选 "Add Python to PATH"，装完重新运行本脚本。
  echo.
  pause
  exit /b 1
)
echo       已找到: %PY%

rem ---------- 2. 安装依赖 ----------
echo.
echo [2/5] 安装 Python 依赖（onnxruntime / pillow / numpy）...
%PY% -m pip install --quiet --disable-pip-version-check onnxruntime pillow numpy
if errorlevel 1 (
  echo       [警告] 依赖安装失败，图反推功能可能不可用，其他功能不受影响。
) else (
  echo       依赖安装完成。
)

rem ---------- 3. 询问使用模式 ----------
echo.
echo [3/5] 选择使用模式：
echo       1 = 轻量版（用 API Key，不需要 Ollama，推荐）
echo       2 = 完整离线版（安装 Ollama + 本地模型，约 7 GB）
echo       3 = 跳过，先用模板模式
echo.
set /p MODE=请输入 1 / 2 / 3 后回车（默认 1）:
if "%MODE%"=="" set MODE=1

if "%MODE%"=="3" goto launch

rem ---------- 4. API 配置 ----------
if "%MODE%"=="1" (
  echo.
  echo [4/5] 配置 DeepSeek API
  if exist "api_config.json" (
    echo       api_config.json 已存在，跳过。如需修改请手动编辑该文件。
  ) else (
    copy api_config.example.json api_config.json >nul
    echo       已生成 api_config.json，请填入你的 Key：
    echo         1. 打开 https://platform.deepseek.com/api_keys 申请
    echo         2. 用记事本打开 api_config.json，把 key 填在 "key": "" 中间
    echo.
    notepad api_config.json
  )
  goto launch
)

rem ---------- 5. Ollama ----------
echo.
echo [4/5] 检测 Ollama...
where ollama >nul 2>nul
if errorlevel 1 (
  echo       未检测到 Ollama。
  echo.
  echo       请从官网下载安装（约 1 GB）：
  echo       https://ollama.com/download/windows
  echo.
  echo       安装完成后重新运行本脚本，会自动拉取模型。
  echo.
  pause
  exit /b 1
)
echo       已找到 Ollama。

echo.
echo [5/5] 拉取本地模型（首次约 6.7 GB，请耐心等待）...
echo       - qwen2.5:7b（安全内容扩写/润色）
ollama pull qwen2.5:7b
echo       - goonsai/qwen2.5-3b-goonsai-nsfw-100k（成人向润色）
ollama pull goonsai/qwen2.5-3b-goonsai-nsfw-100k
echo       模型准备完成。

if errorlevel 1 (
  echo.
  echo 上一步出错了，把这里的文字截图发出来即可帮你判断。
  pause
)

:launch
echo.
echo ============================================
echo   安装完成，正在启动工作台...
echo   访问地址：http://127.0.0.1:8901
echo ============================================
echo.
call "%~dp0启动工作台.bat"
