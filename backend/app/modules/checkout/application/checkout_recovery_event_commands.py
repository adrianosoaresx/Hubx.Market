from __future__ import annotations

from app.modules.checkout.application.checkout_result_taxonomy import CHECKOUT_RESULT_TAXONOMY
from app.modules.checkout.application.checkout_result_taxonomy import classify_checkout_result
from app.modules.checkout.models import CheckoutRecoveryEvent
from app.modules.checkout.models import CheckoutSession


def record_checkout_recovery_event(
    *,
    tenant_id: int | None,
    result: str,
    session_key: str | None = None,
    stage: str | None = None,
    source: str = "checkout_page",
) -> CheckoutRecoveryEvent | None:
    normalized = str(result or "").strip()
    if not tenant_id or normalized not in CHECKOUT_RESULT_TAXONOMY:
        return None

    checkout_session = None
    if session_key:
        checkout_session = (
            CheckoutSession.objects.filter(
                tenant_id=tenant_id,
                session_key=session_key,
            )
            .only("id", "tenant_id")
            .first()
        )

    taxonomy = classify_checkout_result(normalized)
    return CheckoutRecoveryEvent.objects.create(
        tenant_id=tenant_id,
        checkout_session=checkout_session,
        result_code=taxonomy["code"],
        family=taxonomy["family"],
        severity=taxonomy["severity"],
        recovery_action=taxonomy["recovery_action"],
        stage=str(stage or "").strip()[:32],
        source=str(source or "checkout_page").strip()[:64],
    )
