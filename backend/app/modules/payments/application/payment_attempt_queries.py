from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone


def _string(value: object) -> str:
    return str(value or "").strip()


def _format_timestamp(value: object) -> str:
    if value is None:
        return ""
    try:
        localized = timezone.localtime(value) if timezone.is_aware(value) else value
        return localized.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return ""


def _status_label(status: str) -> str:
    normalized = _string(status).lower()
    return {
        "pending": "Pendente",
        "paid": "Pago",
        "failed": "Falhou",
    }.get(normalized, "Indisponível")


def _badge_variant(level: str) -> str:
    normalized = _string(level).lower()
    return {
        "success": "success",
        "warning": "warning",
        "error": "danger",
    }.get(normalized, "info")


def _parse_iso_datetime(value: object):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except Exception:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _pending_age_summary(*, created_at: object, latest_event_at: object) -> dict[str, object]:
    created = created_at if hasattr(created_at, "tzinfo") else None
    latest_event = _parse_iso_datetime(latest_event_at)
    reference = latest_event or created
    if reference is None:
        return {
            "age_label": "",
            "stale_state": "",
            "stale_title": "",
            "stale_description": "",
        }
    current_time = timezone.now()
    delta = current_time - reference
    total_minutes = max(int(delta.total_seconds() // 60), 0)
    if total_minutes < 60:
        age_label = f"há {max(total_minutes, 1)} min"
    elif total_minutes < 24 * 60:
        age_label = f"há {max(total_minutes // 60, 1)} h"
    else:
        age_label = f"há {max(delta.days, 1)} dia(s)"

    if delta >= timedelta(hours=6):
        return {
            "age_label": age_label,
            "stale_state": "critical",
            "stale_title": "Tentativa pendente há tempo demais",
            "stale_description": "A tentativa continua aberta sem atualização recente e já merece reconciliação operacional.",
        }
    if delta >= timedelta(minutes=30):
        return {
            "age_label": age_label,
            "stale_state": "warning",
            "stale_title": "Tentativa pendente sem atualização recente",
            "stale_description": "A tentativa continua aberta e já vale confirmar se houve abandono, expiração ou falha de retorno.",
        }
    return {
        "age_label": age_label,
        "stale_state": "",
        "stale_title": "",
        "stale_description": "",
    }


def _order_attempt_drift_summary(*, attempt_status: str, order_status: str, order_payment_status: str) -> dict[str, str]:
    normalized_attempt = _string(attempt_status).lower()
    normalized_order = _string(order_status).lower()
    normalized_payment = _string(order_payment_status).lower()
    order_is_confirmed = normalized_order == "paid" or "confirm" in normalized_payment or "pago" in normalized_payment

    if normalized_attempt == "paid" and not order_is_confirmed:
        return {
            "drift_state": "critical",
            "drift_title": "Tentativa paga sem confirmação do pedido",
            "drift_description": "A tentativa já foi reconciliada como paga, mas o pedido ainda não avançou para um estado confirmado.",
        }
    if normalized_attempt == "pending" and order_is_confirmed:
        return {
            "drift_state": "critical",
            "drift_title": "Pedido confirmado com tentativa ainda pendente",
            "drift_description": "O pedido já avançou para um estado confirmado, mas a tentativa de pagamento ainda não foi reconciliada no mesmo ritmo.",
        }
    if normalized_attempt == "failed" and order_is_confirmed:
        return {
            "drift_state": "warning",
            "drift_title": "Tentativa falha com pedido confirmado",
            "drift_description": "O pedido aparece como confirmado, mas a tentativa mais recente ainda carrega falha operacional e merece conferência.",
        }
    return {
        "drift_state": "",
        "drift_title": "",
        "drift_description": "",
    }


def _operational_copy(*, status: str, provider_label: str, latest_event_title: str, stale_title: str, stale_description: str) -> tuple[str, str]:
    normalized_status = _string(status).lower()
    provider = _string(provider_label) or "gateway externo"
    latest_event = _string(latest_event_title)
    if normalized_status == "paid":
        return (
            "Pagamento reconciliado",
            f"O pagamento já foi conciliado com {provider} e o pedido segue com o lifecycle interno protegido.",
        )
    if normalized_status == "failed":
        return (
            "Tentativa com falha",
            f"A última tentativa via {provider} não avançou. O pedido continua salvo para retomada segura.",
        )
    if stale_title and stale_description:
        return (
            stale_title,
            f"{stale_description} Provider atual: {provider}.",
        )
    if latest_event:
        return (
            "Pagamento em acompanhamento",
            f"A trilha externa segue em acompanhamento com {provider}. Último marco operacional: {latest_event.lower()}.",
        )
    return (
        "Pagamento em acompanhamento",
        f"A tentativa atual segue aberta em {provider} e continua pronta para diagnóstico operacional.",
    )


class DjangoOrmPaymentAttemptQueryRepository:
    def __init__(self) -> None:
        try:
            from app.modules.payments.models import PaymentAttempt
        except Exception:
            self.payment_attempt_model = None
            return
        self.payment_attempt_model = PaymentAttempt

    def get_latest_pending_attempt(self, *, tenant_id: int | None, order_number: str):
        if self.payment_attempt_model is None or not tenant_id or not _string(order_number):
            return None
        try:
            return (
                self.payment_attempt_model._default_manager.select_related("order")
                .filter(
                    tenant_id=tenant_id,
                    order__number=_string(order_number).lstrip("#"),
                    status=self.payment_attempt_model.Status.PENDING,
                )
                .order_by("-created_at", "-id")
                .first()
            )
        except Exception:
            return None

    def get_latest_attempt(self, *, tenant_id: int | None, order_number: str):
        if self.payment_attempt_model is None or not tenant_id or not _string(order_number):
            return None
        try:
            return (
                self.payment_attempt_model._default_manager.select_related("order")
                .filter(
                    tenant_id=tenant_id,
                    order__number=_string(order_number).lstrip("#"),
                )
                .order_by("-created_at", "-id")
                .first()
            )
        except Exception:
            return None


@dataclass
class PaymentAttemptQueryService:
    repository: DjangoOrmPaymentAttemptQueryRepository

    def get_latest_pending_hosted_payment(self, *, tenant_id: int | None, order_number: str) -> dict[str, str] | None:
        attempt = self.repository.get_latest_pending_attempt(tenant_id=tenant_id, order_number=order_number)
        if attempt is None:
            return None
        return {
            "attempt_key": _string(getattr(attempt, "attempt_key", "")),
            "provider_label": _string(getattr(attempt, "provider_label", "") or "Gateway externo"),
            "provider_code": _string(getattr(attempt, "provider_code", "") or getattr(attempt, "payment_method_code", "")),
        }

    def get_latest_attempt_summary(self, *, tenant_id: int | None, order_number: str) -> dict[str, object] | None:
        attempt = self.repository.get_latest_attempt(tenant_id=tenant_id, order_number=order_number)
        if attempt is None:
            return None
        metadata = dict(getattr(attempt, "metadata", {}) or {})
        timeline = list(metadata.get("timeline") or [])
        latest_timeline = timeline[-1] if timeline else {}
        order = getattr(attempt, "order", None)
        drift = _order_attempt_drift_summary(
            attempt_status=_string(getattr(attempt, "status", "")),
            order_status=_string(getattr(order, "status", "")),
            order_payment_status=_string(getattr(order, "payment_status", "")),
        )
        pending_age = _pending_age_summary(
            created_at=getattr(attempt, "created_at", None),
            latest_event_at=metadata.get("latest_event_at"),
        )
        operational_title, operational_description = _operational_copy(
            status=_string(getattr(attempt, "status", "")),
            provider_label=_string(getattr(attempt, "provider_label", "") or "Gateway externo"),
            latest_event_title=_string(latest_timeline.get("title")),
            stale_title=str(pending_age.get("stale_title") or ""),
            stale_description=str(pending_age.get("stale_description") or ""),
        )
        if drift.get("drift_title") and drift.get("drift_description"):
            operational_title = str(drift.get("drift_title") or operational_title)
            operational_description = str(drift.get("drift_description") or operational_description)
        timeline_items = [
            {
                "title": _string(item.get("title")),
                "description": _string(item.get("description")),
                "timestamp": _format_timestamp(item.get("at")),
                "meta": _string(item.get("code")),
                "badge_label": "Pagamento",
                "badge_variant": _badge_variant(_string(item.get("level") or "info")),
            }
            for item in timeline[-5:]
            if _string(item.get("title"))
        ]
        if drift.get("drift_title"):
            timeline_items.insert(
                0,
                {
                    "title": str(drift.get("drift_title") or ""),
                    "description": str(drift.get("drift_description") or ""),
                    "timestamp": "",
                    "meta": "order_payment_drift",
                    "badge_label": "Drift",
                    "badge_variant": "danger" if str(drift.get("drift_state") or "") == "critical" else "warning",
                },
            )
        if pending_age.get("stale_title"):
            timeline_items.insert(
                0,
                {
                    "title": str(pending_age.get("stale_title") or ""),
                    "description": str(pending_age.get("stale_description") or ""),
                    "timestamp": str(pending_age.get("age_label") or ""),
                    "meta": "pending_stale_state",
                    "badge_label": "Atenção",
                    "badge_variant": "danger" if str(pending_age.get("stale_state") or "") == "critical" else "warning",
                },
            )
        return {
            "attempt_key": _string(getattr(attempt, "attempt_key", "")),
            "status": _string(getattr(attempt, "status", "")),
            "status_label": _status_label(_string(getattr(attempt, "status", ""))),
            "provider_label": _string(getattr(attempt, "provider_label", "") or "Gateway externo"),
            "provider_code": _string(getattr(attempt, "provider_code", "") or getattr(attempt, "payment_method_code", "")),
            "external_reference": _string(getattr(attempt, "external_reference", "")),
            "checkout_session_key": _string(metadata.get("checkout_session_key")),
            "created_at": _format_timestamp(getattr(attempt, "created_at", None)),
            "bootstrapped_at": _format_timestamp(getattr(attempt, "bootstrapped_at", None)),
            "paid_at": _format_timestamp(getattr(attempt, "paid_at", None)),
            "failed_at": _format_timestamp(getattr(attempt, "failed_at", None)),
            "age_label": str(pending_age.get("age_label") or ""),
            "stale_state": str(pending_age.get("stale_state") or ""),
            "stale_title": str(pending_age.get("stale_title") or ""),
            "stale_description": str(pending_age.get("stale_description") or ""),
            "operational_title": operational_title,
            "operational_description": operational_description,
            "latest_event_title": _string(latest_timeline.get("title")),
            "latest_event_description": _string(latest_timeline.get("description")),
            "latest_event_level": _string(latest_timeline.get("level") or "info"),
            "timeline_items": timeline_items,
        }


payment_attempt_queries = PaymentAttemptQueryService(
    repository=DjangoOrmPaymentAttemptQueryRepository(),
)
