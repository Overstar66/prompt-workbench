<#
  提示词工作台 - 安装向导（PowerShell 版）
  由 install.bat 调用，负责：检测 Python、装依赖、选模式、拉模型、启动
#>
$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-Python {
    # 1) 优先 3.12 / 3.13 / 3.11 / 3.10（onnxruntime 有现成轮子的版本）
    foreach ($v in @('3.12','3.13','3.11','3.10')) {
        $c = Get-Command py -ErrorAction SilentlyContinue
        if ($c) {
            & py "-$v" -c "import sys" 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { return @{ Exe='py'; Args="@('-${v}')"; Ver=$v } }
        }
    }
    # 2) python_path.txt（用户手动指定过）
    $pp = Join-Path $here 'python_path.txt'
    if (Test-Path $pp) {
        $raw = (Get-Content $pp -Raw).Trim()
        if ($raw) {
            $cand = Join-Path (Split-Path $raw) 'python.exe'
            if (Test-Path $cand) { return @{ Exe=$cand; Args=@(); Ver='custom' } }
        }
    }
    # 3) PATH 里的 python（跳过 Windows 商店占位符）
    foreach ($p in (Get-Command python -All -ErrorAction SilentlyContinue)) {
        if ($p.Source -match 'WindowsApps') { continue }
        return @{ Exe=$p.Source; Args=@(); Ver='path' }
    }
    # 4) 常见安装目录
    foreach ($v in @('312','313','311','310')) {
        $cand = Join-Path $env:LOCALAPPDATA "Programs\Python\Python$v\python.exe"
        if (Test-Path $cand) { return @{ Exe=$cand; Args=@(); Ver="3.$($v.Substring(1))" } }
    }
    # 5) 最后才 py -3（可能是很新的版本）
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -c "import sys" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return @{ Exe='py'; Args=@('-3'); Ver='3.x' } }
    }
    return $null
}

function Run-Py($py, [string[]]$argv) {
    if ($py.Exe -eq 'py') {
        $all = $py.Args + $argv
        & py @all
    } else {
        & $py.Exe @argv
    }
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  提示词工作台 - 安装向导" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/5] 检测 Python..." -ForegroundColor Yellow
$py = Find-Python
if (-not $py) {
    Write-Host ""
    Write-Host "[错误] 没有检测到 Python。" -ForegroundColor Red
    Write-Host "  请安装 Python 3.10 ~ 3.12（推荐 3.12）："
    Write-Host "  https://www.python.org/downloads/"
    Write-Host "  安装时勾选 Add Python to PATH，装完重新运行。"
    Read-Host "按回车退出"
    exit 1
}
$verLine = (Run-Py $py @('-c', 'import sys;print(sys.version.split()[0]);print(sys.executable)')) -join ' '
Write-Host "      已找到: $($py.Exe) $($py.Args -join ' ')"
Write-Host "      $verLine"

Write-Host ""
Write-Host "[2/5] 安装依赖（带下载进度）" -ForegroundColor Yellow
Write-Host "      --- pillow / numpy ---"
Run-Py $py @('-m','pip','install','--disable-pip-version-check','--progress-bar','on','pillow','numpy')
Write-Host ""
Write-Host "      --- onnxruntime（图片反推用，可选）---"
Run-Py $py @('-m','pip','install','--disable-pip-version-check','--progress-bar','on','onnxruntime')
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "      [提示] onnxruntime 装不上。" -ForegroundColor Yellow
    Write-Host "      通常是因为 Python 版本太新（3.14 / 3.15 还没有对应安装包）。"
    Write-Host "      影响：只有「图片反推」不可用，其他功能全部正常。"
    Write-Host "      想用图反推，装一个 Python 3.12 再运行本脚本即可。"
}

Write-Host ""
Write-Host "[3/5] 选择使用模式：" -ForegroundColor Yellow
Write-Host "      1 = 轻量版（用 API Key，不需要 Ollama，推荐）"
Write-Host "      2 = 完整离线版（安装 Ollama + 本地模型，约 7 GB）"
Write-Host "      3 = 跳过，先用模板模式"
$mode = Read-Host "请输入 1 / 2 / 3 后回车（默认 1）"
if ([string]::IsNullOrWhiteSpace($mode)) { $mode = '1' }

if ($mode -eq '3') { . (Join-Path $here 'launch.ps1'); return }

if ($mode -eq '1') {
    Write-Host ""
    Write-Host "[4/5] 配置 DeepSeek API" -ForegroundColor Yellow
    $cfg = Join-Path $here 'api_config.json'
    if (Test-Path $cfg) {
        Write-Host "      api_config.json 已存在，跳过。"
    } else {
        Copy-Item (Join-Path $here 'api_config.example.json') $cfg
        Write-Host "      已生成 api_config.json，请在打开的记事本里填 key。"
        Write-Host "      申请地址：https://platform.deepseek.com/api_keys"
        Start-Process notepad $cfg
    }
    . (Join-Path $here 'launch.ps1')
    return
}

Write-Host ""
Write-Host "[4/5] 检测 Ollama..." -ForegroundColor Yellow
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "      未检测到 Ollama，请从官网安装（约 1 GB）："
    Write-Host "      https://ollama.com/download/windows"
    Write-Host "      装好后重新运行本脚本。"
    Read-Host "按回车退出"
    exit 1
}
Write-Host "      已找到 Ollama。"

Write-Host ""
Write-Host "[5/5] 拉取本地模型（首次约 6.7 GB，会显示进度）..." -ForegroundColor Yellow
& ollama pull qwen2.5:7b
& ollama pull goonsai/qwen2.5-3b-goonsai-nsfw-100k

. (Join-Path $here 'launch.ps1')
