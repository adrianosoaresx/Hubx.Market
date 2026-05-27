from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.ops_rbac_production_closure_queries import ops_rbac_production_closure_queries


class Command(BaseCommand):
    help = "Fecha a trilha de ativação production do RBAC granular em /ops/."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Limita o closure a um tenant específico.")
        parser.add_argument(
            "--expect-gate",
            dest="expect_gate",
            default="enabled",
            choices=["any", "enabled", "disabled"],
            help="Estado esperado de HUBX_OPS_AUTH_GATE_ENFORCED.",
        )
        parser.add_argument("--window-minutes", type=int, default=30, help="Janela de monitoramento pós-produção.")
        parser.add_argument(
            "--allow-email-dry-run",
            action="store_true",
            help="Não exige provider de e-mail pronto para entrega real.",
        )
        parser.add_argument(
            "--allow-notification-failures",
            action="store_true",
            help="Não bloqueia quando há EmailLog failed no tenant.",
        )
        parser.add_argument("--fail-on-blockers", action="store_true", help="Retorna erro quando closure não está ready.")

    def handle(self, *args, **options):
        closure = ops_rbac_production_closure_queries.get_closure(
            tenant_id=str(options.get("tenant_id") or "").strip(),
            expected_gate_state=str(options.get("expect_gate") or "enabled"),
            window_minutes=int(options.get("window_minutes") or 30),
            require_email_delivery=not bool(options.get("allow_email_dry_run")),
            block_on_notification_failures=not bool(options.get("allow_notification_failures")),
        )
        status = str(closure["status"]).upper()
        blockers = ",".join(closure["blockers"]) if closure["blockers"] else "none"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] tenant_id={closure['tenant_id'] or 'all'} expected_gate={closure['expected_gate_state']} "
                f"window_minutes={closure['window_minutes']} blockers={blockers}"
            )
        )
        for decision in closure["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for risk in closure["residual_risks"]:
            self.stdout.write(f"residual_risk={risk}")
        for track in closure["next_tracks"]:
            self.stdout.write(f"next_track={track}")

        if options.get("fail_on_blockers") and not closure["ready"]:
            raise CommandError("Ops RBAC production closure is not ready.")
