from __future__ import annotations


CHECKOUT_RESULT_TAXONOMY = {
    "checkout-saved": ("progress", "success", "continue_session"),
    "checkout-save-unavailable": ("session", "warning", "restart_from_product"),
    "checkout-completed": ("completion", "success", "view_order"),
    "checkout-completion-blocked": ("readiness", "warning", "complete_current_session"),
    "checkout-completion-unavailable": ("session", "warning", "restart_from_product"),
    "checkout-completion-session-drift": ("session", "warning", "restart_from_product"),
    "checkout-completion-inventory-link-missing": ("inventory", "warning", "restart_from_product"),
    "checkout-completion-inventory-unavailable": ("inventory", "warning", "restart_from_product"),
    "checkout-completion-stock-conflict": ("inventory", "warning", "review_current_session"),
    "checkout-completion-snapshot-conflict": ("snapshot", "warning", "review_current_session"),
    "checkout-item-updated": ("cart_mutation", "success", "continue_session"),
    "checkout-item-removed": ("cart_mutation", "success", "continue_session"),
    "checkout-inventory-reconciled": ("inventory", "success", "review_current_session"),
    "checkout-inventory-item-removed": ("inventory", "success", "review_current_session"),
    "checkout-item-session-empty": ("cart_mutation", "warning", "restart_from_product"),
    "checkout-item-mutation-unavailable": ("cart_mutation", "warning", "review_current_session"),
    "reorder-lite-ready": ("reorder", "success", "continue_session"),
    "reorder-lite-partial": ("reorder", "info", "review_current_session"),
    "reorder-lite-unavailable": ("reorder", "warning", "view_order"),
    "payment-retry-ready": ("payment_retry", "success", "continue_session"),
    "payment-retry-partial": ("payment_retry", "info", "review_current_session"),
    "payment-retry-unavailable": ("payment_retry", "warning", "view_order"),
    "payment-retry-blocked": ("payment_retry", "warning", "view_order"),
}


def classify_checkout_result(result: str) -> dict[str, str]:
    normalized = str(result or "").strip()
    family, severity, action = CHECKOUT_RESULT_TAXONOMY.get(normalized, ("unknown", "", ""))
    return {
        "code": normalized,
        "family": family,
        "severity": severity,
        "recovery_action": action,
    }
