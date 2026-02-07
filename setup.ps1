# Setup script for SD Host Controller 3.0 RAG project
# This script helps configure the environment for development

Write-Host "SD Host Controller 3.0 RAG - Environment Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if ANTHROPIC_API_KEY is set
if ($env:ANTHROPIC_API_KEY) {
    Write-Host "✓ ANTHROPIC_API_KEY is already set" -ForegroundColor Green
} else {
    Write-Host "✗ ANTHROPIC_API_KEY is not set" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To set your API key, run:" -ForegroundColor White
    Write-Host '  $env:ANTHROPIC_API_KEY = "your-api-key-here"' -ForegroundColor Gray
    Write-Host ""
    Write-Host "Get your API key from: https://console.anthropic.com/settings/keys" -ForegroundColor White
    Write-Host ""
    Write-Host "For persistent setup, add to your PowerShell profile:" -ForegroundColor White
    Write-Host "  notepad `$PROFILE" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "Setup complete!" -ForegroundColor Green
