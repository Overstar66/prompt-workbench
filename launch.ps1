# 启动工作台（供 install.ps1 与用户直接调用）
$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-Python {
    foreach ($v in @('3.12','3.13','3.11','3.10')) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py "-$v" -c "import sys" 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { return @{ Exe='py'; Args=@("-${v}") } }
        }
    }
    $pp = Join-Path $here 'python_path.txt'
    if (Test-Path $pp) {
        $raw = (Get-Content $pp -Raw).Trim()
        if ($raw) {
            $cand = Join-Path (Split-Path $raw) 'pythonw.exe'
            if (Test-Path $cand) { return @{ Exe=$cand; Args=@() } }
            $cand2 = Join-Path (Split-Path $raw) 'python.exe'
            if (Test-Path $cand2) { return @{ Exe=$cand2; Args=@() } }
        }
    }
    foreach ($p in (Get-Command pythonw -All -ErrorAction SilentlyContinue)) {
        if ($p.Source -match 'WindowsApps') { continue }
        return @{ Exe=$p.Source; Args=@() }
    }
    foreach ($p in (Get-Command python -All -ErrorAction SilentlyContinue)) {
        if ($p.Source -match 'WindowsApps') { continue }
        return @{ Exe=$p.Source; Args=@() }
    }
    return $null
}

# 已经在跑就直接开浏览器
$listening = Get-NetTCPConnection -LocalPort 8901 -State Listen -ErrorAction SilentlyContinue
if (-not $listening) {
    $py = Find-Python
    if (-not $py) {
        Write-Host "[错误] 找不到 Python，请先运行 install.bat 或手动 python app.py" -ForegroundColor Red
        Read-Host "按回车退出"
        exit 1
    }
    $app = Join-Path $here 'app.py'
    if ($py.Exe -eq 'py') {
        $all = $py.Args + @($app)
        Start-Process -FilePath 'py' -ArgumentList $all -WorkingDirectory $here -WindowStyle Hidden
    } else {
        Start-Process -FilePath $py.Exe -ArgumentList @($app) -WorkingDirectory $here -WindowStyle Hidden
    }
    Start-Sleep -Seconds 4
}
Start-Process 'http://127.0.0.1:8901'
Write-Host ""
Write-Host "工作台已启动：http://127.0.0.1:8901" -ForegroundColor Green
