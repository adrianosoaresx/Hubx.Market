param(
    [int]$Port = 8002,
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$EnsureScript = Join-Path $PSScriptRoot "ensure-platform-owner.ps1"

if (-not (Test-Path $EnsureScript)) {
    throw "Script auxiliar não encontrado em $EnsureScript"
}

& $EnsureScript

$StoreBaseUrl = "http://hubx-demo.localhost:$Port"
$AccessUrl = "$StoreBaseUrl/accounts/login/?next=/ops/"

Write-Host ""
Write-Host "Acesso store owner" -ForegroundColor Cyan
Write-Host "URL:     $AccessUrl" -ForegroundColor Yellow
Write-Host "Usuário: store.owner@hubx.market"
Write-Host "Senha:   secret"
Write-Host ""
Write-Host "Se o servidor não estiver rodando, abra outro PowerShell e execute:" -ForegroundColor DarkYellow
Write-Host ".\scripts\start-hubx-demo.ps1"
Write-Host ""

try {
    Invoke-WebRequest -Uri "$StoreBaseUrl/accounts/login/" -Method Get -TimeoutSec 2 -UseBasicParsing | Out-Null
    Write-Host "Servidor respondeu em $StoreBaseUrl" -ForegroundColor Green
} catch {
    Write-Host "Servidor ainda não respondeu em $StoreBaseUrl" -ForegroundColor DarkYellow
}

if (-not $NoOpen) {
    Start-Process $AccessUrl
}
