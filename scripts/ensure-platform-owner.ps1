param(
    [string]$PlatformEmail = "platform.owner@hubx.market",
    [string]$StoreAdminEmail = "admin@hubx-demo.market",
    [string]$CustomerEmail = "cliente@hubx-demo.market",
    [string]$Password = "secret",
    [string]$PlatformTenantSlug = "platform-system",
    [string]$StoreTenantSlug = "hubx-demo",
    [string]$PublicPort = ""
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
$env:HUBX_MARKET_PUBLIC_PORT = "$PublicPort"
$env:HUBX_MARKET_DEMO_TENANT_SUBDOMAIN = "$StoreTenantSlug"
$env:HUBX_PLATFORM_TENANT_SLUG = "$PlatformTenantSlug"
$env:ALLOWED_HOSTS = ".localhost,localhost,127.0.0.1,testserver"
$env:HUBX_OPS_AUTH_GATE_ENFORCED = "1"

$PythonCode = @"
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from app.modules.accounts.models import AccountProfile, OwnerUser
from app.modules.customers.models import Customer
from app.modules.tenants.models import Tenant

platform_email = "$PlatformEmail"
store_admin_email = "$StoreAdminEmail"
customer_email = "$CustomerEmail"
password = "$Password"
platform_tenant_slug = "$PlatformTenantSlug"
store_tenant_slug = "$StoreTenantSlug"
legacy_store_owner_email = "store.owner@hubx.market"
legacy_store_admin_email = "admin@hubx.market"
legacy_customer_email = "cliente@hubx.market"


def ensure_user(*, email: str, password: str):
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=email,
        defaults={"email": email, "is_active": True},
    )
    user.email = email
    user.is_active = True
    user.set_password(password)
    user.save(update_fields=["email", "is_active", "password"])
    return user, created

with transaction.atomic():
    platform_tenant, _ = Tenant.objects.get_or_create(
        slug=platform_tenant_slug,
        defaults={
            "name": "Hubx Platform",
            "subdomain": platform_tenant_slug,
            "is_active": True,
        },
    )
    platform_tenant.name = "Hubx Platform"
    platform_tenant.subdomain = platform_tenant.subdomain or platform_tenant_slug
    platform_tenant.is_active = True
    platform_tenant.save(update_fields=["name", "subdomain", "is_active", "updated_at"])

    store_tenant, _ = Tenant.objects.get_or_create(
        slug=store_tenant_slug,
        defaults={
            "name": "Hubx Demo Store",
            "subdomain": store_tenant_slug,
            "is_active": True,
        },
    )
    store_tenant.name = store_tenant.name or "Hubx Demo Store"
    store_tenant.subdomain = store_tenant.subdomain or store_tenant_slug
    store_tenant.is_active = True
    store_tenant.save(update_fields=["name", "subdomain", "is_active", "updated_at"])

    platform_user, platform_user_created = ensure_user(email=platform_email, password=password)
    store_admin_user, store_admin_user_created = ensure_user(email=store_admin_email, password=password)
    customer_user, customer_user_created = ensure_user(email=customer_email, password=password)

    platform_owner, platform_owner_created = OwnerUser.objects.update_or_create(
        tenant=platform_tenant,
        email=platform_email,
        defaults={"full_name": "Platform Owner", "role": "owner", "is_active": True},
    )
    OwnerUser.objects.filter(email__iexact=platform_email).exclude(tenant=platform_tenant).update(is_active=False)

    store_owner, store_owner_created = OwnerUser.objects.update_or_create(
        tenant=store_tenant,
        email=store_admin_email,
        defaults={"full_name": "Admin Hubx Demo", "role": "owner", "is_active": True},
    )
    OwnerUser.objects.filter(tenant=store_tenant, email__iexact=legacy_store_owner_email).update(is_active=False)
    OwnerUser.objects.filter(tenant=store_tenant, email__iexact=legacy_store_admin_email).update(is_active=False)

    customer, customer_created = Customer.objects.update_or_create(
        tenant=store_tenant,
        email=customer_email,
        defaults={
            "slug": "cliente-hubx-demo",
            "reference": "#CLI-LOCAL",
            "full_name": "Cliente Hubx Demo",
            "phone": "(11) 90000-0000",
            "status": "active",
            "account_type": "Storefront",
        },
    )
    profile, profile_created = AccountProfile.objects.update_or_create(
        tenant=store_tenant,
        email=customer_email,
        defaults={
            "customer": customer,
            "first_name": "Cliente",
            "last_name": "Hubx Demo",
            "phone": customer.phone,
            "newsletter_opt_in": True,
            "order_updates_opt_in": True,
            "is_active": True,
        },
    )
    AccountProfile.objects.filter(tenant=store_tenant, email__iexact=legacy_customer_email).update(is_active=False)
    Customer.objects.filter(tenant=store_tenant, email__iexact=legacy_customer_email).update(status="inactive")
    User = get_user_model()
    User.objects.filter(email__iexact=legacy_store_owner_email).update(is_active=False)
    User.objects.filter(email__iexact=legacy_store_admin_email).update(is_active=False)
    User.objects.filter(email__iexact=legacy_customer_email).update(is_active=False)

print({
    "platform_tenant": platform_tenant.slug,
    "platform_email": platform_email,
    "platform_role": platform_owner.role,
    "platform_user_created": platform_user_created,
    "platform_owner_created": platform_owner_created,
    "platform_auth_ok": authenticate(username=platform_email, password=password) is not None,
    "store_tenant": store_tenant.slug,
    "store_subdomain": store_tenant.subdomain,
    "store_admin_email": store_admin_email,
    "store_owner_role": store_owner.role,
    "store_admin_user_created": store_admin_user_created,
    "store_owner_created": store_owner_created,
    "store_auth_ok": authenticate(username=store_admin_email, password=password) is not None,
    "customer_email": customer_email,
    "customer_created": customer_created,
    "customer_profile_created": profile_created,
    "customer_user_created": customer_user_created,
    "customer_auth_ok": authenticate(username=customer_email, password=password) is not None,
})
"@

$TempPython = New-TemporaryFile
try {
    $Utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($TempPython.FullName, $PythonCode, $Utf8NoBom)
    $PythonPath = $TempPython.FullName.Replace("'", "\\'")
    $ShellCommand = "exec(compile(open(r'$PythonPath', encoding='utf-8').read(), r'$PythonPath', 'exec'))"
    python $ManagePy shell -c "$ShellCommand"
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao garantir usuários locais da demo. ExitCode=$LASTEXITCODE"
    }
} finally {
    Remove-Item -LiteralPath $TempPython.FullName -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Usuários locais prontos para teste." -ForegroundColor Green
Write-Host "Platform admin: $PlatformEmail"
Write-Host "Admin loja:     $StoreAdminEmail"
Write-Host "Cliente loja:   $CustomerEmail"
Write-Host "Senha:          $Password"
