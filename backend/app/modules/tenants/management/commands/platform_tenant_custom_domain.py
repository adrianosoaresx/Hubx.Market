from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.tenants.application.platform_tenant_admin_commands import platform_tenant_admin_commands


class Command(BaseCommand):
    help = "Atualiza custom_domain de um tenant via command service platform-only e auditável."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-slug", required=True)
        parser.add_argument("--custom-domain", default="")
        parser.add_argument("--clear", action="store_true")
        parser.add_argument("--actor-label", default="platform-cli")
        parser.add_argument("--actor-role", default="owner")
        parser.add_argument("--fail-on-errors", action="store_true")

    def handle(self, *args, **options):
        custom_domain = "" if options["clear"] else options["custom_domain"]
        result = platform_tenant_admin_commands.update_custom_domain(
            tenant_slug=options["tenant_slug"],
            custom_domain=custom_domain,
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
                f"custom_domain={tenant['custom_domain'] or '-'}"
            )
        if options["fail_on_errors"] and result["result"] != "platform-tenant-custom-domain-updated":
            raise CommandError("Platform tenant custom domain update failed.")
