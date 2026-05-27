from django.test import TestCase

from app.modules.notifications.application.owner_access_email_commands import owner_access_email_commands
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class OwnerAccessEmailCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Owner Access Email",
            slug="owner-access-email",
            subdomain="owner-access-email",
        )

    def test_records_owner_invite_email_log(self):
        result = owner_access_email_commands.record_owner_invite_email(
            tenant_id=self.tenant.id,
            owner_id=42,
            owner_email="Owner@Hubx.Market",
            owner_name="Owner Hubx",
            reset_url="https://owner-access-email.hubx.market/accounts/reset-password/u/t/",
        )

        self.assertTrue(result.created)
        self.assertEqual(result.log.tenant, self.tenant)
        self.assertEqual(result.log.source_event, "owner.invited")
        self.assertEqual(result.log.intent_key, "owner.access.invite")
        self.assertEqual(result.log.audience, "owner")
        self.assertEqual(result.log.recipient_type, "owner_user")
        self.assertEqual(result.log.recipient_id, "42")
        self.assertEqual(result.log.recipient_email, "owner@hubx.market")
        self.assertEqual(result.log.status, EmailLog.Status.PLANNED)
        self.assertIn("Defina sua senha", result.log.description)

    def test_records_owner_password_reset_email_log_idempotently(self):
        first = owner_access_email_commands.record_owner_password_reset_email(
            tenant_id=self.tenant.id,
            owner_id=77,
            owner_email="owner.reset@hubx.market",
            reset_url="https://owner-access-email.hubx.market/accounts/reset-password/u/t/",
        )
        second = owner_access_email_commands.record_owner_password_reset_email(
            tenant_id=self.tenant.id,
            owner_id=77,
            owner_email="owner.reset@hubx.market",
            reset_url="https://owner-access-email.hubx.market/accounts/reset-password/u/t/",
        )

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.log.id, second.log.id)
        self.assertEqual(EmailLog.objects.count(), 1)
        self.assertEqual(first.log.source_event, "owner.password_reset_requested")
        self.assertEqual(first.log.intent_key, "owner.access.password_reset")
