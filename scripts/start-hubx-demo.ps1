param(
    [int]$Port = 8002,
    [switch]$SkipMigrate,
    [switch]$OpenBrowser,
    [switch]$OpenPlatform
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ManagePy = Join-Path $RepoRoot "backend\manage.py"
$Activate = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $ManagePy)) {
    throw "manage.py não encontrado em $ManagePy"
}

if (Test-Path $Activate) {
    . $Activate
}

$env:DEBUG = "1"
$env:HUBX_MARKET_ROOT_DOMAIN = "localhost"
$env:HUBX_MARKET_PUBLIC_PORT = "$Port"
$env:ALLOWED_HOSTS = ".localhost,localhost,127.0.0.1,testserver"
$env:HUBX_OPS_AUTH_GATE_ENFORCED = "1"

$PortalHost = "localhost:$Port"
$StoreHost = "hubx-demo.localhost:$Port"
$BaseUrl = "http://$StoreHost"
$PortalBaseUrl = "http://$PortalHost"
$LoginUrl = "$BaseUrl/accounts/login/"
$PortalLoginUrl = "$PortalBaseUrl/accounts/login/"
$StorefrontUrl = "$BaseUrl/"
$ShopUrl = "$BaseUrl/catalog/"
$OpsUrl = "$BaseUrl/ops/"
$PlatformTenantsUrl = "$PortalBaseUrl/accounts/login/?next=/ops/platform/tenants/"
$OnboardingUrl = "$PortalBaseUrl/accounts/login/?next=/ops/platform/onboarding/"
$DjangoAdminUrl = "$BaseUrl/admin/"

Write-Host ""
Write-Host "Hubx Market local — hubx-demo" -ForegroundColor Cyan
Write-Host "Root domain local: $env:HUBX_MARKET_ROOT_DOMAIN"
Write-Host "Ops auth gate: $env:HUBX_OPS_AUTH_GATE_ENFORCED"
Write-Host ""
Write-Host "Loja / home:        $StorefrontUrl" -ForegroundColor Green
Write-Host "Loja / catálogo:    $ShopUrl" -ForegroundColor Green
Write-Host "Portal central:     $PortalBaseUrl" -ForegroundColor Yellow
Write-Host "Login central:      $PortalLoginUrl" -ForegroundColor Yellow
Write-Host "Login loja:         $LoginUrl" -ForegroundColor Yellow
Write-Host "Admin da loja:      $OpsUrl" -ForegroundColor Yellow
Write-Host "Admin de lojas:     $PlatformTenantsUrl" -ForegroundColor Yellow
Write-Host "Wizard onboarding:  $OnboardingUrl" -ForegroundColor Yellow
Write-Host "Django admin raw:   $DjangoAdminUrl" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Platform admin: platform.owner@hubx.market"
Write-Host "Store admin:    store.owner@hubx.market"
Write-Host "Senha padrão:   secret"
Write-Host ""

if (-not $SkipMigrate) {
    Write-Host "Aplicando migrations..." -ForegroundColor Cyan
    python $ManagePy migrate
}

if ($OpenBrowser) {
    Start-Process $StorefrontUrl
}

if ($OpenPlatform) {
    Start-Process $OnboardingUrl
}

Write-Host "Subindo servidor em 0.0.0.0:$Port ..." -ForegroundColor Cyan
python $ManagePy runserver "0.0.0.0:$Port"
