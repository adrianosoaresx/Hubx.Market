from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.tenants.application.platform_tenant_admin_commands import platform_tenant_admin_commands


class Command(BaseCommand):
    help = "Provisiona o owner inicial de um tenant via orquestração platform-only e auditável."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-slug", required=True)
        parser.add_argument("--owner-email", required=True)
        parser.add_argument("--owner-name", default="")
        parser.add_argument("--owner-role", default="owner", choices=("owner", "admin"))
        parser.add_argument("--actor-label", default="platform-cli")
        parser.add_argument("--actor-role", default="owner")
        parser.add_argument("--fail-on-errors", action="store_true")

    def handle(self, *args, **options):
        result = platform_tenant_admin_commands.bootstrap_owner(
            tenant_slug=options["tenant_slug"],
            payload={
                "owner_email": options["owner_email"],
                "owner_name": options["owner_name"],
                "owner_role": options["owner_role"],
            },
            actor_label=options["actor_label"],
            actor_role=options["actor_role"],
        )
        self.stdout.write(f"result={result['result']}")
        for field, message in (result.get("errors") or {}).items():
            self.stdout.write(f"error field={field} message={message}")
        tenant = result.get("tenant") or {}
        owner = result.get("owner") or {}
        user = result.get("user") or {}
        if tenant and owner:
            self.stdout.write(
                f"tenant id={tenant['id']} slug={tenant['slug']} owner_email={owner['email']} "
                f"owner_created={owner.get('created')} user_created={user.get('created')}"
            )
        if options["fail_on_errors"] and result["result"] != "platform-tenant-owner-bootstrapped":
            raise CommandError("Platform tenant owner bootstrap failed.")
