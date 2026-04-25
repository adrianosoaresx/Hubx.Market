from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from app.modules.checkout.application.checkout_recovery_event_retention_commands import checkout_recovery_event_retention_commands
from app.modules.checkout.models import CheckoutRecoveryEvent
from app.modules.tenants.models import Tenant


class CheckoutRecoveryEventRetentionCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Recovery Retention",
            slug="hubx-recovery-retention",
            subdomain="hubx-recovery-retention",
        )
        self.other_tenant = Tenant.objects.create(
            name="Other Recovery Retention",
            slug="other-recovery-retention",
            subdomain="other-recovery-retention",
        )

    def _create_event(self, *, tenant: Tenant | None = None, days_old: int = 0) -> CheckoutRecoveryEvent:
        event = CheckoutRecoveryEvent.objects.create(
            tenant=tenant or self.tenant,
            result_code="checkout-completion-stock-conflict",
            family="inventory",
            severity="warning",
            recovery_action="restart_from_product",
            stage="review",
        )
        if days_old:
            CheckoutRecoveryEvent.objects.filter(pk=event.pk).update(created_at=timezone.now() - timezone.timedelta(days=days_old))
            event.refresh_from_db()
        return event

    def test_prune_events_dry_run_preserves_candidates(self):
        self._create_event(days_old=220)

        summary = checkout_recovery_event_retention_commands.prune_events(
            tenant_id=self.tenant.id,
            older_than_days=180,
            dry_run=True,
        )

        self.assertEqual(summary.candidates, 1)
        self.assertEqual(summary.deleted, 0)
        self.assertEqual(CheckoutRecoveryEvent.objects.count(), 1)

    def test_prune_events_removes_only_old_events_for_tenant(self):
        old_event = self._create_event(days_old=220)
        recent_event = self._create_event(days_old=20)
        other_event = self._create_event(tenant=self.other_tenant, days_old=220)

        summary = checkout_recovery_event_retention_commands.prune_events(
            tenant_id=self.tenant.id,
            older_than_days=180,
            dry_run=False,
        )

        self.assertEqual(summary.candidates, 1)
        self.assertEqual(summary.deleted, 1)
        self.assertFalse(CheckoutRecoveryEvent.objects.filter(pk=old_event.pk).exists())
        self.assertTrue(CheckoutRecoveryEvent.objects.filter(pk=recent_event.pk).exists())
        self.assertTrue(CheckoutRecoveryEvent.objects.filter(pk=other_event.pk).exists())

    def test_management_command_rejects_short_window(self):
        output = StringIO()

        with self.assertRaises(CommandError):
            call_command(
                "prune_checkout_recovery_events",
                "--tenant-id",
                str(self.tenant.id),
                "--older-than-days",
                "30",
                stdout=output,
            )

    def test_management_command_reports_dry_run_summary(self):
        self._create_event(days_old=220)
        output = StringIO()

        call_command(
            "prune_checkout_recovery_events",
            "--tenant-id",
            str(self.tenant.id),
            "--older-than-days",
            "180",
            "--dry-run",
            stdout=output,
        )

        payload = output.getvalue()
        self.assertIn("Dry-run: checkout_recovery_event_pruning", payload)
        self.assertIn("candidates=1", payload)
