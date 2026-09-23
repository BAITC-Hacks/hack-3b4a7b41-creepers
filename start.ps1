$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$backendPath = Join-Path $projectRoot 'Backend'
$frontendPath = Join-Path $projectRoot 'Frontend'
$pythonPath = Join-Path $backendPath '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install backend dependencies first; see README.md.' }
if (-not (Test-Path -LiteralPath (Join-Path $frontendPath 'node_modules\next\dist\bin\next'))) { throw 'Run npm ci in Frontend first.' }
$nodePath = (Get-Command node -ErrorAction Stop).Source
$logPath = Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Force -Path $logPath | Out-Null
if (-not (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--no-access-log') -WorkingDirectory $backendPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logPath 'backend.out.log') -RedirectStandardError (Join-Path $logPath 'backend.err.log') | Out-Null
}
if (-not (Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $nodePath -ArgumentList @('node_modules/next/dist/bin/next', 'dev', '--hostname', '127.0.0.1', '--port', '3000') -WorkingDirectory $frontendPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logPath 'frontend.out.log') -RedirectStandardError (Join-Path $logPath 'frontend.err.log') | Out-Null
}
Write-Output 'Live: http://localhost:3000'
Write-Output 'Offline demo: http://localhost:3000/?mode=demo'
Write-Output 'Startup can take a few seconds. Logs: .local. Existing listeners are left running.'
