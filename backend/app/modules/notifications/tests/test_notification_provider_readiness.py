from django.test import SimpleTestCase, override_settings

from app.modules.notifications.application.notification_provider_readiness import (
    get_notification_provider_readiness,
)


class NotificationProviderReadinessTests(SimpleTestCase):
    @override_settings(NOTIFICATIONS_EMAIL_DRY_RUN=True, EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend", DEFAULT_FROM_EMAIL="")
    def test_reports_dry_run_and_missing_from_email_blockers(self):
        readiness = get_notification_provider_readiness()

        self.assertFalse(readiness.can_attempt_real_delivery)
        self.assertIn("dry-run-enabled", readiness.blockers)
        self.assertIn("default-from-email-missing", readiness.blockers)

    @override_settings(
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@hubx.market",
    )
    def test_allows_real_delivery_when_required_settings_exist(self):
        readiness = get_notification_provider_readiness()

        self.assertTrue(readiness.can_attempt_real_delivery)
        self.assertEqual(readiness.blockers, ())
