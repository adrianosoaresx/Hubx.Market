from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.tenants.application.platform_tenant_admin_commands import (
    TENANT_STATE_ACTIONS,
    platform_tenant_admin_commands,
)


class Command(BaseCommand):
    help = "Altera is_active/maintenance_mode de um tenant via command service platform-only e auditável."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-slug", required=True)
        parser.add_argument("--action", choices=TENANT_STATE_ACTIONS, required=True)
        parser.add_argument("--actor-label", default="platform-cli")
        parser.add_argument("--actor-role", default="owner")
        parser.add_argument("--fail-on-errors", action="store_true")

    def handle(self, *args, **options):
        result = platform_tenant_admin_commands.update_tenant_state(
            tenant_slug=options["tenant_slug"],
            action=options["action"],
            actor_label=options["actor_label"],
            actor_role=options["actor_role"],
        )
        self.stdout.write(f"result={result['result']}")
        for field, message in (result.get("errors") or {}).items():
            self.stdout.write(f"error field={field} message={message}")
        tenant = result.get("tenant") or {}
        if tenant:
            self.stdout.write(
                f"tenant id={tenant['id']} slug={tenant['slug']} subdomain={tenant['subdomain']} "
                f"active={tenant['is_active']} maintenance={tenant['maintenance_mode']} action={result['action']}"
            )
        if options["fail_on_errors"] and result["result"] != "platform-tenant-state-updated":
            raise CommandError("Platform tenant state update failed.")
