from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.ops_rbac_post_production_monitoring_queries import (
    ops_rbac_post_production_monitoring_queries,
)


class Command(BaseCommand):
    help = "Resume sinais pós-produção do RBAC granular em /ops/."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Limita o snapshot a um tenant específico.")
        parser.add_argument("--window-minutes", type=int, default=30, help="Janela recente observada.")
        parser.add_argument("--permission-denied-warning", type=int, default=3)
        parser.add_argument("--gate-forbidden-warning", type=int, default=3)
        parser.add_argument("--login-failed-warning", type=int, default=5)
        parser.add_argument("--rate-limited-rollback", type=int, default=1)
        parser.add_argument("--email-failed-rollback", type=int, default=1)
        parser.add_argument("--fail-on-watch", action="store_true", help="Retorna erro quando houver sinal watch.")
        parser.add_argument("--fail-on-rollback", action="store_true", help="Retorna erro quando houver sinal rollback.")

    def handle(self, *args, **options):
        snapshot = ops_rbac_post_production_monitoring_queries.get_snapshot(
            tenant_id=str(options.get("tenant_id") or "").strip(),
            window_minutes=int(options.get("window_minutes") or 30),
            permission_denied_warning_threshold=int(options.get("permission_denied_warning") or 0),
            gate_forbidden_warning_threshold=int(options.get("gate_forbidden_warning") or 0),
            login_failed_warning_threshold=int(options.get("login_failed_warning") or 0),
            rate_limited_rollback_threshold=int(options.get("rate_limited_rollback") or 0),
            email_failed_rollback_threshold=int(options.get("email_failed_rollback") or 0),
        )
        status = str(snapshot["status"]).upper()
        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] window_minutes={snapshot['window_minutes']} tenant_id={snapshot['tenant_id'] or 'all'} "
                f"watch_signals={len(snapshot['watch_signals'])} rollback_signals={len(snapshot['rollback_signals'])}"
            )
        )
        for row in snapshot["audit_counts"]:
            self.stdout.write(
                f"audit_count tenant_id={row['tenant_id']} action={row['action']} count={int(row['count'])}"
            )
        for row in snapshot["email_counts"]:
            self.stdout.write(
                f"email_count tenant_id={row['tenant_id']} intent_key={row['intent_key']} "
                f"status={row['status']} count={int(row['count'])}"
            )
        for signal in snapshot["watch_signals"]:
            self.stdout.write(
                f"watch_signal key={signal.key} count={signal.count} threshold={signal.threshold} action={signal.action}"
            )
        for signal in snapshot["rollback_signals"]:
            self.stdout.write(
                f"rollback_signal key={signal.key} count={signal.count} threshold={signal.threshold} action={signal.action}"
            )

        if options.get("fail_on_rollback") and snapshot["rollback_signals"]:
            raise CommandError("Ops RBAC post-production rollback signal present.")
        if options.get("fail_on_watch") and (snapshot["watch_signals"] or snapshot["rollback_signals"]):
            raise CommandError("Ops RBAC post-production watch signal present.")
