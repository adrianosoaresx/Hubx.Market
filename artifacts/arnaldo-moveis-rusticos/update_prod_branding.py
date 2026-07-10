from django.conf import settings

from app.modules.accounts.application.admin_permissions import ROLE_OWNER
from app.modules.tenants.application.storefront_branding_commands import storefront_branding_commands
from app.modules.tenants.models import Tenant


SUBDOMAIN = "arnaldomoveisrusticos"
LOGO_URL = "https://arnaldomoveisrusticos.hubx.market/media/storefront/arnaldo-moveis-rusticos/arnaldo-logo-v1.png"
HERO_URL = "https://arnaldomoveisrusticos.hubx.market/media/storefront/arnaldo-moveis-rusticos/arnaldo-cover-hero-v1.png"


tenant = Tenant.objects.get(subdomain=SUBDOMAIN)
print("tenant_before=", {
    "id": tenant.id,
    "slug": tenant.slug,
    "subdomain": tenant.subdomain,
    "logo_url": tenant.logo_url,
    "storefront_hero_image_url": tenant.storefront_hero_image_url,
})
print("media=", {
    "MEDIA_URL": settings.MEDIA_URL,
    "MEDIA_ROOT": settings.MEDIA_ROOT,
    "HUBX_SERVE_MEDIA_LOCALLY": getattr(settings, "HUBX_SERVE_MEDIA_LOCALLY", None),
})

payload = {
    "logo_url": LOGO_URL,
    "conversion_primary_color": tenant.conversion_primary_color,
    "storefront_hero_enabled": "1",
    "storefront_hero_title": tenant.storefront_hero_title,
    "storefront_hero_description": tenant.storefront_hero_description,
    "storefront_hero_image_url": HERO_URL,
    "storefront_hero_cta_label": tenant.storefront_hero_cta_label,
    "storefront_hero_cta_href": tenant.storefront_hero_cta_href,
}
result = storefront_branding_commands.update_storefront_hero(
    tenant_id=tenant.id,
    payload=payload,
    actor_label="codex-prod-branding-update",
    actor_role=ROLE_OWNER,
)
print("update_result=", result)
tenant.refresh_from_db()
print("tenant_after=", {
    "id": tenant.id,
    "slug": tenant.slug,
    "subdomain": tenant.subdomain,
    "logo_url": tenant.logo_url,
    "storefront_hero_image_url": tenant.storefront_hero_image_url,
    "storefront_hero_enabled": tenant.storefront_hero_enabled,
})
