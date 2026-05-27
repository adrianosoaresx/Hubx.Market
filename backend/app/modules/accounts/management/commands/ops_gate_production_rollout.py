from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.ops_gate_production_rollout_queries import ops_gate_production_rollout_queries


class Command(BaseCommand):
    help = "Gera evidência Go/No-Go para rollout de produção do gate /ops/."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Limita a evidência a um tenant específico.")
        parser.add_argument(
            "--expect-gate",
            dest="expect_gate",
            default="enabled",
            choices=["any", "enabled", "disabled"],
            help="Estado esperado do gate no momento da evidência.",
        )
        parser.add_argument(
            "--allow-email-dry-run",
            action="store_true",
            help="Não exige provider de e-mail pronto para entrega real.",
        )
        parser.add_argument(
            "--allow-notification-failures",
            action="store_true",
            help="Não bloqueia rollout quando há EmailLog failed no tenant.",
        )
        parser.add_argument(
            "--block-on-pending-delivery",
            action="store_true",
            help="Bloqueia rollout quando há EmailLog planned/requested no tenant.",
        )
        parser.add_argument("--fail-on-blockers", action="store_true", help="Retorna erro quando houver blockers.")

    def handle(self, *args, **options):
        evidence = ops_gate_production_rollout_queries.get_rollout_evidence(
            tenant_id=str(options.get("tenant_id") or "").strip(),
            expected_gate_state=str(options.get("expect_gate") or "enabled"),
            require_email_delivery=not bool(options.get("allow_email_dry_run")),
            block_on_notification_failures=not bool(options.get("allow_notification_failures")),
            block_on_pending_delivery=bool(options.get("block_on_pending_delivery")),
        )
        status = "READY" if evidence["ready"] else "BLOCKED"
        blocker_label = ",".join(evidence["blockers"]) if evidence["blockers"] else "none"
        preflight = evidence["preflight"]
        provider = preflight["notification_provider"]
        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] gate_enabled={str(preflight['gate_enabled']).lower()} "
                f"expected_gate={preflight['expected_gate_state']} blockers={blocker_label} "
                f"email_dry_run={str(provider.dry_run).lower()} email_can_deliver={str(provider.can_attempt_real_delivery).lower()}"
            )
        )
        for item in evidence["tenants"]:
            notifications = item["notifications"]
            owner_blockers = ",".join(item["owner_blockers"]) if item["owner_blockers"] else "none"
            notification_blockers = ",".join(item["notification_blockers"]) if item["notification_blockers"] else "none"
            self.stdout.write(
                f"tenant_id={item['tenant_id']} slug={item['tenant_slug']} ready={str(item['ready']).lower()} "
                f"owner_blockers={owner_blockers} notification_blockers={notification_blockers} "
                f"email_total={notifications.total} email_planned={notifications.planned} "
                f"email_requested={notifications.requested} email_sent={notifications.sent} "
                f"email_failed={notifications.failed} email_skipped={notifications.skipped}"
            )

        if options.get("fail_on_blockers") and not evidence["ready"]:
            raise CommandError("Ops gate production rollout blocked.")
