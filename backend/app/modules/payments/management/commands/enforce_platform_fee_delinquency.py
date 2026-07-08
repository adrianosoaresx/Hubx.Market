from __future__ import annotations

from django.core.management.base import BaseCommand

from app.modules.payments.application.platform_billing_commands import platform_billing_commands


class Command(BaseCommand):
    help = "Aplica a política de inadimplência para complementos mensais Pro pendentes."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", type=int, default=0)
        parser.add_argument("--actor-label", default="enforce-platform-fee-delinquency")

    def handle(self, *args, **options):
        results = platform_billing_commands.apply_pro_delinquency_policy(
            tenant_id=int(options.get("tenant_id") or 0) or None,
            actor_label=str(options.get("actor_label") or "enforce-platform-fee-delinquency"),
        )
        summary = " ".join(f"{key}={value}" for key, value in sorted(results.items()))
        self.stdout.write(self.style.SUCCESS(f"platform_fee_delinquency {summary}"))
