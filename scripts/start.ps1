# ============================================================
# WhatsApp Claude Agent — Windows starter
# ============================================================
# Cloudflare Tunnel roda como Windows service (cloudflared service install).
# Este script so cuida do webhook. URL vem de config.PUBLIC_WEBHOOK_URL.
# ============================================================

$ErrorActionPreference = "Stop"

if (-Not (Test-Path "config.py")) {
    Write-Host "ERROR: config.py not found. Run install.ps1 first." -ForegroundColor Red
    exit 1
}

$publicUrl = (& py -c "from config import PUBLIC_WEBHOOK_URL; print(PUBLIC_WEBHOOK_URL)" 2>$null)

Write-Host ""
Write-Host "=== WhatsApp Claude Agent - Start ===" -ForegroundColor Cyan
Write-Host ""

# --- Kill old webhook ---
Write-Host "[1/2] Cleaning old webhook + legacy ngrok..."
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='py.exe'" | Where-Object {
    $_.CommandLine -like "*webhook_server*"
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Get-CimInstance Win32_Process -Filter "Name='ngrok.exe'" | Where-Object {
    $_.CommandLine -like "*http 3020*"
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

# --- Start webhook server (background) ---
Write-Host "[2/2] Starting webhook server on :3020..."
Start-Process -FilePath "python" -ArgumentList "-m", "whatsapp_agent.webhook_server" -WindowStyle Hidden -RedirectStandardOutput "webhook.log" -RedirectStandardError "webhook.err.log"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "=== READY ===" -ForegroundColor Green
Write-Host ""
if ($publicUrl) {
    Write-Host "Webhook URL publica (config.PUBLIC_WEBHOOK_URL):" -ForegroundColor Cyan
    Write-Host "  $publicUrl/?session=1" -ForegroundColor White
    Write-Host "  $publicUrl/?session=2" -ForegroundColor White
} else {
    Write-Host "WARNING: config.PUBLIC_WEBHOOK_URL vazio." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Cloudflare Tunnel: instale como servico uma vez:"
Write-Host "  cloudflared service install" -ForegroundColor White
Write-Host ""
Write-Host "Apos alterar PUBLIC_WEBHOOK_URL: python -m whatsapp_agent.update_webhooks" -ForegroundColor White
Write-Host ""
Write-Host "Next: in Claude Code session, set Monitor to:"
Write-Host "  python -m whatsapp_agent.monitor 1" -ForegroundColor White
Write-Host ""
Write-Host "Logs: webhook.log / webhook.err.log"
Write-Host "Stop: .\stop.ps1"
