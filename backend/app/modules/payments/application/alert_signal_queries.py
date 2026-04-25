from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from django.db.models import Count

from app.modules.payments.infrastructure.alert_signal_metrics import list_payment_alert_signal_snapshots


def _string(value: object) -> str:
    return str(value or "").strip()


def _timestamp_to_epoch_seconds(value: object) -> float:
    normalized = _string(value)
    if not normalized:
        return 0.0
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except Exception:
        return 0.0


class PaymentAlertSignalQueryRepository(Protocol):
    def list_snapshots(self) -> list[dict[str, object]]:
        ...

    def list_attempt_status_counts(self) -> list[dict[str, object]]:
        ...


class InMemoryPaymentAlertSignalQueryRepository:
    def list_snapshots(self) -> list[dict[str, object]]:
        return list_payment_alert_signal_snapshots()

    def list_attempt_status_counts(self) -> list[dict[str, object]]:
        try:
            from app.modules.payments.models import PaymentAttempt
        except Exception:
            return []
        return list(
            PaymentAttempt.objects.values("tenant_id", "status")
            .annotate(count=Count("id"))
            .order_by("tenant_id", "status")
        )


@dataclass
class PaymentAlertSignalQueryService:
    repository: PaymentAlertSignalQueryRepository

    def export_prometheus_metrics(self) -> str:
        snapshots = self.repository.list_snapshots()
        lines = [
            "# HELP hubx_payments_alert_signal_total Total acumulado de sinais críticos de pagamento por código.",
            "# TYPE hubx_payments_alert_signal_total counter",
        ]
        for snapshot in snapshots:
            signal_code = _string(snapshot.get("signal_code"))
            count = int(snapshot.get("count", 0) or 0)
            lines.append(f'hubx_payments_alert_signal_total{{signal_code="{signal_code}"}} {count}')

        lines.extend(
            [
                "# HELP hubx_payments_alert_signal_last_timestamp_seconds Último timestamp observado para cada sinal crítico de pagamento.",
                "# TYPE hubx_payments_alert_signal_last_timestamp_seconds gauge",
            ]
        )
        for snapshot in snapshots:
            signal_code = _string(snapshot.get("signal_code"))
            last_at = _timestamp_to_epoch_seconds(snapshot.get("last_at"))
            lines.append(
                f'hubx_payments_alert_signal_last_timestamp_seconds{{signal_code="{signal_code}"}} {last_at:.6f}'
            )

        lines.extend(
            [
                "# HELP hubx_payments_attempt_total Total de tentativas de pagamento por tenant e status.",
                "# TYPE hubx_payments_attempt_total gauge",
            ]
        )
        for row in self.repository.list_attempt_status_counts():
            tenant_id = _string(row.get("tenant_id"))
            status = _string(row.get("status"))
            count = int(row.get("count", 0) or 0)
            lines.append(f'hubx_payments_attempt_total{{tenant_id="{tenant_id}",status="{status}"}} {count}')

        return "\n".join(lines) + "\n"


payment_alert_signal_queries = PaymentAlertSignalQueryService(
    repository=InMemoryPaymentAlertSignalQueryRepository(),
)
