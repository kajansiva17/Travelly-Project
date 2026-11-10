# Starts everything Travelly needs for local development, each in its own window.
# Safe to run again: anything that is already running is skipped.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py   = Join-Path $root '.venv\Scripts\python.exe'

function Test-Port($port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
}
function Start-Window($title, $command) {
    Start-Process powershell -ArgumentList '-NoExit', '-Command', "`$Host.UI.RawUI.WindowTitle = '$title'; $command"
}

if (Test-Port 6379) { Write-Host 'Redis already running' }
else {
    Start-Window 'Travelly Redis' "Set-Location '$root'; & '$py' Backend\scripts\start_local_redis.py"
    Start-Sleep -Seconds 3
}

$writer = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*app.services.review_writer*' }
if ($writer) { Write-Host 'Review writer already running' }
else {
    Start-Window 'Travelly Review Writer' "Set-Location '$root\Backend'; & '$py' -m app.services.review_writer"
    Start-Sleep -Seconds 3
}

if (Test-Port 8000) { Write-Host 'Backend already running (port 8000)' }
else {
    Start-Window 'Travelly Backend' "Set-Location '$root'; & '$py' -m uvicorn app.main:app --app-dir Backend --reload --host 127.0.0.1 --port 8000"
}

if (Test-Port 5173) { Write-Host 'Frontend already running (port 5173)' }
else {
    Start-Window 'Travelly Frontend' "Set-Location '$root\Frontend'; npm.cmd run dev"
}

Write-Host ''
Write-Host 'Done. Wait about 10 seconds, then open http://localhost:5173'
Write-Host 'Do not close the Redis, Review Writer, Backend and Frontend windows while you work.'
