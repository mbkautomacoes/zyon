# ============================================================
# WhatsApp Claude Agent — Windows installer
# ============================================================
# Run from project root:
#   powershell -ExecutionPolicy Bypass -File install.ps1
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== WhatsApp Claude Agent - Install ===" -ForegroundColor Cyan
Write-Host ""

# --- 1. Check Python ---
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pyVersion = python --version 2>&1
    Write-Host "  OK: $pyVersion"
} catch {
    Write-Host "  ERROR: Python not found. Install from https://python.org" -ForegroundColor Red
    exit 1
}

# --- 2. Check curl ---
Write-Host "[2/5] Checking curl..." -ForegroundColor Yellow
try {
    $null = curl --version
    Write-Host "  OK: curl available"
} catch {
    Write-Host "  ERROR: curl not found." -ForegroundColor Red
    exit 1
}

# --- 3. Check ngrok ---
Write-Host "[3/5] Checking ngrok..." -ForegroundColor Yellow
$ngrokOK = $false
try {
    $null = ngrok version 2>&1
    $ngrokOK = $true
    Write-Host "  OK: ngrok in PATH"
} catch {
    Write-Host "  WARNING: ngrok not found. Download: https://ngrok.com/download" -ForegroundColor Yellow
    Write-Host "  After install, run: ngrok config add-authtoken <YOUR_TOKEN>"
}

# --- 4. Run interactive config wizard ---
Write-Host "[4/5] Configuring..." -ForegroundColor Yellow
python setup_config.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: config wizard failed." -ForegroundColor Red
    exit 1
}

# --- 5. Done ---
Write-Host "[5/5] Install complete." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run:    .\start.ps1"
Write-Host "  2. Paste the ngrok URL shown into megaAPI webhook config"
Write-Host "  3. Send WhatsApp message to yourself"
Write-Host "  4. Run:    python discover_lid.py    (auto-fills LID)"
Write-Host "  5. Open Claude Code and follow CLAUDE_PROMPT.md"
Write-Host "  - If anything breaks: python doctor.py"
Write-Host ""
