from decimal import Decimal
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from app.modules.checkout.models import CheckoutSession, CheckoutSessionItem
from app.modules.tenants.models import Tenant


class CheckoutSessionRetentionCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Checkout Retention",
            slug="hubx-checkout-retention",
            subdomain="hubx-checkout-retention",
        )
        self.other_tenant = Tenant.objects.create(
            name="Hubx Checkout Retention Other",
            slug="hubx-checkout-retention-other",
            subdomain="hubx-checkout-retention-other",
        )

    def _session(self, *, tenant: Tenant | None = None, status: str = CheckoutSession.Status.OPEN) -> CheckoutSession:
        session = CheckoutSession.objects.create(
            tenant=tenant or self.tenant,
            status=status,
            first_name="Ana",
            email="ana@hubx.market",
            subtotal=Decimal("100.00"),
            shipping_total=Decimal("10.00"),
            grand_total=Decimal("110.00"),
        )
        CheckoutSessionItem.objects.create(
            checkout_session=session,
            title="Produto retention",
            price=Decimal("100.00"),
            quantity=1,
        )
        return session

    def test_expire_checkout_sessions_dry_run_does_not_mutate(self):
        stale = self._session()
        CheckoutSession.objects.filter(pk=stale.pk).update(updated_at=timezone.now() - timezone.timedelta(hours=30))
        output = StringIO()

        call_command(
            "expire_checkout_sessions",
            "--tenant-id",
            str(self.tenant.id),
            "--older-than-hours",
            "24",
            "--dry-run",
            stdout=output,
        )

        stale.refresh_from_db()
        self.assertEqual(stale.status, CheckoutSession.Status.OPEN)
        self.assertIn("Dry-run: checkout_session_expiration candidates=1; expired=0", output.getvalue())

    def test_expire_checkout_sessions_respects_tenant_and_status(self):
        stale = self._session()
        other_stale = self._session(tenant=self.other_tenant)
        completed_stale = self._session(status=CheckoutSession.Status.COMPLETED)
        recent = self._session()
        stale_time = timezone.now() - timezone.timedelta(hours=30)
        CheckoutSession.objects.filter(pk__in=[stale.pk, other_stale.pk, completed_stale.pk]).update(updated_at=stale_time)
        output = StringIO()

        call_command(
            "expire_checkout_sessions",
            "--tenant-id",
            str(self.tenant.id),
            "--older-than-hours",
            "24",
            stdout=output,
        )

        stale.refresh_from_db()
        other_stale.refresh_from_db()
        completed_stale.refresh_from_db()
        recent.refresh_from_db()
        self.assertEqual(stale.status, CheckoutSession.Status.EXPIRED)
        self.assertEqual(other_stale.status, CheckoutSession.Status.OPEN)
        self.assertEqual(completed_stale.status, CheckoutSession.Status.COMPLETED)
        self.assertEqual(recent.status, CheckoutSession.Status.OPEN)
        self.assertIn("checkout_session_expiration candidates=1; expired=1", output.getvalue())

    def test_expire_checkout_sessions_includes_explicit_expires_at(self):
        expired_by_timestamp = self._session()
        CheckoutSession.objects.filter(pk=expired_by_timestamp.pk).update(expires_at=timezone.now() - timezone.timedelta(minutes=5))

        call_command("expire_checkout_sessions", "--tenant-id", str(self.tenant.id), "--older-than-hours", "24")

        expired_by_timestamp.refresh_from_db()
        self.assertEqual(expired_by_timestamp.status, CheckoutSession.Status.EXPIRED)

    def test_expire_checkout_sessions_rejects_aggressive_window(self):
        with self.assertRaises(CommandError):
            call_command("expire_checkout_sessions", "--tenant-id", str(self.tenant.id), "--older-than-hours", "1")

    def test_prune_expired_checkout_sessions_dry_run_does_not_delete(self):
        expired = self._session(status=CheckoutSession.Status.EXPIRED)
        old_time = timezone.now() - timezone.timedelta(days=220)
        CheckoutSession.objects.filter(pk=expired.pk).update(updated_at=old_time)
        output = StringIO()

        call_command(
            "prune_expired_checkout_sessions",
            "--tenant-id",
            str(self.tenant.id),
            "--older-than-days",
            "180",
            "--dry-run",
            stdout=output,
        )

        self.assertTrue(CheckoutSession.objects.filter(pk=expired.pk).exists())
        self.assertIn("Dry-run: checkout_expired_session_pruning candidates=1; deleted=0", output.getvalue())

    def test_prune_expired_checkout_sessions_respects_tenant_status_and_age(self):
        expired_old = self._session(status=CheckoutSession.Status.EXPIRED)
        other_expired_old = self._session(tenant=self.other_tenant, status=CheckoutSession.Status.EXPIRED)
        expired_recent = self._session(status=CheckoutSession.Status.EXPIRED)
        completed_old = self._session(status=CheckoutSession.Status.COMPLETED)
        open_old = self._session(status=CheckoutSession.Status.OPEN)
        old_time = timezone.now() - timezone.timedelta(days=220)
        CheckoutSession.objects.filter(pk__in=[expired_old.pk, other_expired_old.pk, completed_old.pk, open_old.pk]).update(updated_at=old_time)
        output = StringIO()

        call_command(
            "prune_expired_checkout_sessions",
            "--tenant-id",
            str(self.tenant.id),
            "--older-than-days",
            "180",
            stdout=output,
        )

        self.assertFalse(CheckoutSession.objects.filter(pk=expired_old.pk).exists())
        self.assertTrue(CheckoutSession.objects.filter(pk=other_expired_old.pk).exists())
        self.assertTrue(CheckoutSession.objects.filter(pk=expired_recent.pk).exists())
        self.assertTrue(CheckoutSession.objects.filter(pk=completed_old.pk).exists())
        self.assertTrue(CheckoutSession.objects.filter(pk=open_old.pk).exists())
        self.assertIn("checkout_expired_session_pruning candidates=1; deleted=2", output.getvalue())

    def test_prune_expired_checkout_sessions_rejects_short_retention_window(self):
        with self.assertRaises(CommandError):
            call_command("prune_expired_checkout_sessions", "--tenant-id", str(self.tenant.id), "--older-than-days", "30")
