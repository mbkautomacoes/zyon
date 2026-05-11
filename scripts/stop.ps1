# Stops webhook server (Cloudflare Tunnel runs as Windows service separately)
$ErrorActionPreference = "SilentlyContinue"

Write-Host "Stopping webhook..."
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='py.exe'" | Where-Object {
    $_.CommandLine -like "*webhook_server*"
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Write-Host "Stopped."
