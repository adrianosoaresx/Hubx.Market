from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.tenants.application.platform_tenant_admin_commands import platform_tenant_admin_commands


class Command(BaseCommand):
    help = "Cria um tenant via command service platform-only e auditável."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--slug", required=True)
        parser.add_argument("--subdomain", required=True)
        parser.add_argument("--custom-domain", default="")
        parser.add_argument("--inactive", action="store_true")
        parser.add_argument("--maintenance-mode", action="store_true")
        parser.add_argument("--actor-label", default="platform-cli")
        parser.add_argument("--actor-role", default="owner")
        parser.add_argument("--fail-on-errors", action="store_true")

    def handle(self, *args, **options):
        result = platform_tenant_admin_commands.create_tenant(
            payload={
                "name": options["name"],
                "slug": options["slug"],
                "subdomain": options["subdomain"],
                "custom_domain": options["custom_domain"],
                "is_active": not bool(options["inactive"]),
                "maintenance_mode": bool(options["maintenance_mode"]),
            },
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
                f"active={tenant['is_active']} maintenance={tenant['maintenance_mode']}"
            )
        if options["fail_on_errors"] and result["result"] != "platform-tenant-created":
            raise CommandError("Platform tenant create failed.")
