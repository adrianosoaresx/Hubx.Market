param(
    [string]$PlatformEmail = "platform.owner@hubx.market",
    [string]$StoreOwnerEmail = "store.owner@hubx.market",
    [string]$Password = "secret",
    [string]$PlatformTenantSlug = "platform-system",
    [string]$StoreTenantSlug = "hubx-demo"
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
$env:HUBX_MARKET_PUBLIC_PORT = ""
$env:ALLOWED_HOSTS = ".localhost,localhost,127.0.0.1,testserver"
$env:HUBX_OPS_AUTH_GATE_ENFORCED = "1"

$PythonCode = @"
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant

platform_email = "$PlatformEmail"
store_owner_email = "$StoreOwnerEmail"
password = "$Password"
platform_tenant_slug = "$PlatformTenantSlug"
store_tenant_slug = "$StoreTenantSlug"


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
    store_user, store_user_created = ensure_user(email=store_owner_email, password=password)

    platform_owner, platform_owner_created = OwnerUser.objects.update_or_create(
        tenant=platform_tenant,
        email=platform_email,
        defaults={"full_name": "Platform Owner", "role": "owner", "is_active": True},
    )
    OwnerUser.objects.filter(email__iexact=platform_email).exclude(tenant=platform_tenant).update(is_active=False)

    store_owner, store_owner_created = OwnerUser.objects.update_or_create(
        tenant=store_tenant,
        email=store_owner_email,
        defaults={"full_name": "Store Owner", "role": "owner", "is_active": True},
    )

print({
    "platform_tenant": platform_tenant.slug,
    "platform_email": platform_email,
    "platform_role": platform_owner.role,
    "platform_user_created": platform_user_created,
    "platform_owner_created": platform_owner_created,
    "platform_auth_ok": authenticate(username=platform_email, password=password) is not None,
    "store_tenant": store_tenant.slug,
    "store_subdomain": store_tenant.subdomain,
    "store_owner_email": store_owner_email,
    "store_owner_role": store_owner.role,
    "store_user_created": store_user_created,
    "store_owner_created": store_owner_created,
    "store_auth_ok": authenticate(username=store_owner_email, password=password) is not None,
})
"@

python $ManagePy shell -c $PythonCode

Write-Host ""
Write-Host "Usuários locais prontos para teste." -ForegroundColor Green
Write-Host "Platform admin: $PlatformEmail"
Write-Host "Store admin:    $StoreOwnerEmail"
Write-Host "Senha:          $Password"
