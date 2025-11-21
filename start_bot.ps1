# Quick start script for the Telegram bot
# The bot now reads token from .env file automatically
# No need to set environment variables manually!

Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     🎬 TELEGRAM MEDIA DOWNLOADER BOT 🎬            ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Checking configuration..." -ForegroundColor Yellow

if (Test-Path ".env") {
    Write-Host "✅ Configuration file found (.env)" -ForegroundColor Green
} else {
    Write-Host "⚠️  No .env file found. Using environment variable..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🚀 Starting bot..." -ForegroundColor Green
Write-Host "📱 Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Run the bot
python .\bot.py
