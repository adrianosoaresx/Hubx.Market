from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

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


class InMemoryPaymentAlertSignalQueryRepository:
    def list_snapshots(self) -> list[dict[str, object]]:
        return list_payment_alert_signal_snapshots()


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

        return "\n".join(lines) + "\n"


payment_alert_signal_queries = PaymentAlertSignalQueryService(
    repository=InMemoryPaymentAlertSignalQueryRepository(),
)

