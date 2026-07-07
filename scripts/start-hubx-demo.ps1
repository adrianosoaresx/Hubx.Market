param(
    [int]$Port = 8002,
    [switch]$SkipMigrate,
    [switch]$SkipUsers,
    [switch]$SkipSeed,
    [switch]$OpenBrowser,
    [switch]$OpenPlatform
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ManagePy = Join-Path $RepoRoot "backend\manage.py"
$Activate = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $ManagePy)) {
    throw "manage.py nao encontrado em $ManagePy"
}

if (Test-Path $Activate) {
    . $Activate
}

$env:DEBUG = "1"
$env:HUBX_MARKET_ROOT_DOMAIN = "localhost"
$env:HUBX_MARKET_PUBLIC_PORT = "$Port"
$env:HUBX_MARKET_DEMO_TENANT_SUBDOMAIN = "hubx-demo"
$env:ALLOWED_HOSTS = ".localhost,localhost,127.0.0.1,testserver"
$env:HUBX_OPS_AUTH_GATE_ENFORCED = "1"

$PortalHost = "localhost:$Port"
$StoreHost = "hubx-demo.localhost:$Port"
$BaseUrl = "http://$StoreHost"
$PortalBaseUrl = "http://$PortalHost"
$LoginUrl = "$BaseUrl/accounts/login/"
$PortalLoginUrl = "$PortalBaseUrl/accounts/login/"
$DemoUrl = "$PortalBaseUrl/demo/"
$StorefrontUrl = "$BaseUrl/"
$ShopUrl = "$BaseUrl/catalog/"
$OpsUrl = "$BaseUrl/ops/"
$PlatformTenantsUrl = "$PortalBaseUrl/accounts/login/?next=/ops/platform/tenants/"
$OnboardingUrl = "$PortalBaseUrl/accounts/login/?next=/ops/platform/onboarding/"
$DjangoAdminUrl = "$BaseUrl/admin/"

Write-Host ""
Write-Host "Hubx Market local - hubx-demo" -ForegroundColor Cyan
Write-Host "Root domain local: $env:HUBX_MARKET_ROOT_DOMAIN"
Write-Host "Ops auth gate: $env:HUBX_OPS_AUTH_GATE_ENFORCED"
Write-Host ""
Write-Host "Loja / home:        $StorefrontUrl" -ForegroundColor Green
Write-Host "Loja / catalogo:    $ShopUrl" -ForegroundColor Green
Write-Host "Portal central:     $PortalBaseUrl" -ForegroundColor Yellow
Write-Host "Login central:      $PortalLoginUrl" -ForegroundColor Yellow
Write-Host "Demo publico:       $DemoUrl" -ForegroundColor Yellow
Write-Host "Login loja:         $LoginUrl" -ForegroundColor Yellow
Write-Host "Admin da loja:      $OpsUrl" -ForegroundColor Yellow
Write-Host "Admin de lojas:     $PlatformTenantsUrl" -ForegroundColor Yellow
Write-Host "Wizard onboarding:  $OnboardingUrl" -ForegroundColor Yellow
Write-Host "Django admin raw:   $DjangoAdminUrl" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Platform admin: platform.owner@hubx.market"
Write-Host "Admin loja:     admin@hubx-demo.market"
Write-Host "Cliente loja:   cliente@hubx-demo.market"
Write-Host "Senha padrao:   secret"
Write-Host ""

if (-not $SkipMigrate) {
    Write-Host "Aplicando migrations..." -ForegroundColor Cyan
    python $ManagePy migrate
}

if (-not $SkipUsers) {
    Write-Host "Garantindo tenants e usuários locais da demo..." -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot "ensure-platform-owner.ps1") -StoreTenantSlug hubx-demo -PlatformTenantSlug platform-system -PublicPort "$Port"
}

if (-not $SkipSeed) {
    Write-Host "Atualizando catalogo demo com imagens realistas..." -ForegroundColor Cyan
    python $ManagePy seed_demo_catalog --tenant-subdomain hubx-demo --store-name "Hubx Market Demo" --count 50 --images-per-product 4 --reset-seed --reset-tenant-catalog --clear-discovery-events --image-host $BaseUrl
}

if ($OpenBrowser) {
    Start-Process $StorefrontUrl
}

if ($OpenPlatform) {
    Start-Process $OnboardingUrl
}

$RunserverBind = "0.0.0.0:{0}" -f $Port
Write-Host "Subindo servidor em $RunserverBind ..." -ForegroundColor Cyan
python $ManagePy runserver $RunserverBind
