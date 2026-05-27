from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.initial_owner_provisioning_commands import initial_owner_provisioning_commands


class Command(BaseCommand):
    help = "Provisiona o primeiro owner/user administrativo de um tenant para desbloquear o gate de /ops/."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", required=True, dest="tenant_id", help="Tenant ativo que receberá o owner inicial.")
        parser.add_argument("--email", required=True, dest="email", help="E-mail do owner inicial.")
        parser.add_argument("--full-name", default="", dest="full_name", help="Nome exibido do owner inicial.")
        parser.add_argument("--role", default="owner", choices=["owner", "admin"], help="Papel inicial permitido.")
        parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria feito sem persistir.")

    def handle(self, *args, **options):
        result = initial_owner_provisioning_commands.provision_initial_owner(
            tenant_id=options.get("tenant_id"),
            email=options.get("email"),
            full_name=options.get("full_name"),
            role=options.get("role"),
            dry_run=bool(options.get("dry_run")),
            actor_label="management:provision_initial_owner",
        )
        if result.get("errors"):
            errors = result.get("errors") if isinstance(result.get("errors"), dict) else {}
            raise CommandError(errors.get("__all__") or errors.get("email") or errors.get("role") or "Provisionamento inválido.")

        tenant = result.get("tenant") if isinstance(result.get("tenant"), dict) else {}
        owner = result.get("owner") if isinstance(result.get("owner"), dict) else {}
        user = result.get("user") if isinstance(result.get("user"), dict) else {}
        self.stdout.write(
            self.style.SUCCESS(
                f"[{result.get('result')}] tenant_id={tenant.get('id')} tenant_slug={tenant.get('slug')} "
                f"owner_email={owner.get('email')} owner_created={owner.get('created')} "
                f"user_email={user.get('email')} user_created={user.get('created')}"
            )
        )
