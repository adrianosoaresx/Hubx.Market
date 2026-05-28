param(
    [int]$Port = 8002,
    [ValidateSet("onboarding", "tenants")]
    [string]$Target = "tenants",
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$EnsureScript = Join-Path $PSScriptRoot "ensure-platform-owner.ps1"

if (-not (Test-Path $EnsureScript)) {
    throw "Script auxiliar não encontrado em $EnsureScript"
}

& $EnsureScript

$PlatformBaseUrl = "http://localhost:$Port"
$TargetPath = switch ($Target) {
    "tenants" { "/ops/platform/tenants/" }
    default { "/ops/platform/onboarding/" }
}
$AccessUrl = "$PlatformBaseUrl/accounts/login/?next=$TargetPath"

Write-Host ""
Write-Host "Acesso platform owner" -ForegroundColor Cyan
Write-Host "URL:     $AccessUrl" -ForegroundColor Yellow
Write-Host "Usuário: platform.owner@hubx.market"
Write-Host "Senha:   secret"
Write-Host ""
Write-Host "Se o servidor não estiver rodando, abra outro PowerShell e execute:" -ForegroundColor DarkYellow
Write-Host ".\scripts\start-hubx-demo.ps1"
Write-Host ""

try {
    Invoke-WebRequest -Uri "$PlatformBaseUrl/accounts/login/" -Method Get -TimeoutSec 2 -UseBasicParsing | Out-Null
    Write-Host "Servidor respondeu em $PlatformBaseUrl" -ForegroundColor Green
} catch {
    Write-Host "Servidor ainda não respondeu em $PlatformBaseUrl" -ForegroundColor DarkYellow
}

if (-not $NoOpen) {
    Start-Process $AccessUrl
}
