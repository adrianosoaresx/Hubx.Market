from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

from django.conf import settings
from django.urls import NoReverseMatch, reverse


@dataclass(frozen=True)
class NotificationCta:
    label: str
    target: str
    url: str


class DjangoOrmNotificationCtaRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders.models import Order
            from app.modules.tenants.models import Tenant
        except Exception:
            self.order_model = None
            self.tenant_model = None
            return
        self.order_model = Order
        self.tenant_model = Tenant

    def get_tenant(self, *, tenant_id: int | str):
        if self.tenant_model is None:
            return None
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return None
        try:
            return self.tenant_model._default_manager.filter(id=normalized_tenant_id).first()
        except Exception:
            return None

    def get_order_number(self, *, tenant_id: int | str, order_id: int | str) -> str:
        if self.order_model is None:
            return ""
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_order_id = str(order_id or "").strip()
        if not normalized_tenant_id or not normalized_order_id:
            return ""
        try:
            order = (
                self.order_model._default_manager.filter(id=normalized_order_id, tenant_id=normalized_tenant_id)
                .only("number")
                .first()
            )
        except Exception:
            return ""
        return str(getattr(order, "number", "") or "").strip() if order is not None else ""


def resolve_notification_cta(
    *,
    tenant_id: int | str,
    cta_label: str,
    cta_target: str,
    entity_type: str,
    entity_id: int | str,
    repository: DjangoOrmNotificationCtaRepository | None = None,
) -> NotificationCta | None:
    normalized_target = str(cta_target or "").strip()
    if not normalized_target:
        return None

    repo = repository or DjangoOrmNotificationCtaRepository()
    tenant = repo.get_tenant(tenant_id=tenant_id)
    if tenant is None:
        return None

    path = _resolve_cta_path(
        tenant_id=tenant_id,
        cta_target=normalized_target,
        entity_type=entity_type,
        entity_id=entity_id,
        repository=repo,
    )
    if not path:
        return None

    return NotificationCta(
        label=str(cta_label or "").strip(),
        target=normalized_target,
        url=urljoin(_tenant_base_url(tenant=tenant), path),
    )


def _resolve_cta_path(
    *,
    tenant_id: int | str,
    cta_target: str,
    entity_type: str,
    entity_id: int | str,
    repository: DjangoOrmNotificationCtaRepository,
) -> str:
    if cta_target not in {"customer_order_detail", "admin_order_detail"}:
        return ""
    if str(entity_type or "").strip() != "order":
        return ""

    order_number = repository.get_order_number(tenant_id=tenant_id, order_id=entity_id)
    if not order_number:
        return ""

    route_name = "accounts:account-order-detail" if cta_target == "customer_order_detail" else "orders:admin-orders-detail"
    try:
        return reverse(route_name, kwargs={"order_number": order_number})
    except NoReverseMatch:
        return ""


def _tenant_base_url(*, tenant) -> str:
    custom_domain = str(getattr(tenant, "custom_domain", "") or "").strip()
    if custom_domain:
        return _normalize_domain(custom_domain)
    subdomain = str(getattr(tenant, "subdomain", "") or "").strip()
    root_domain = str(getattr(settings, "HUBX_MARKET_ROOT_DOMAIN", "hubx.market") or "hubx.market").strip()
    if subdomain:
        return f"https://{subdomain}.{root_domain}/"
    return f"https://{root_domain}/"


def _normalize_domain(domain: str) -> str:
    if domain.startswith("http://") or domain.startswith("https://"):
        return domain.rstrip("/") + "/"
    return f"https://{domain.rstrip('/')}/"
