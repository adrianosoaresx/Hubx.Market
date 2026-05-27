from __future__ import annotations

import time
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_challenge_commands import TotpChallengeVerifier, owner_mfa_challenge_commands
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class OwnerMfaChallengeCommandServiceTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Challenge", slug="mfa-challenge", subdomain="mfa-challenge")
        self.other_tenant = Tenant.objects.create(name="MFA Challenge Other", slug="mfa-challenge-other", subdomain="mfa-challenge-other")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.challenge@hubx.market", role="owner")
        self.factor = OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="env",
            secret_reference="ref:owners/challenge/totp",
            is_active=True,
            is_verified=False,
        )

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_verify_factor_marks_factor_verified_and_records_audit_event(self):
        challenge = self._current_challenge()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_CHALLENGE_TOTP": self.secret}):
            result = owner_mfa_challenge_commands.verify_factor(
                tenant_id=self.tenant.id,
                factor_id=self.factor.id,
                challenge=challenge,
                actor_label="admin@hubx.market",
                actor_role="owner",
            )

        self.factor.refresh_from_db()
        self.assertEqual(result["result"], "owner-mfa-factor-verified")
        self.assertTrue(self.factor.is_verified)
        self.assertIsNotNone(self.factor.verified_at)
        self.assertIsNotNone(self.factor.last_challenged_at)
        self.assertTrue(AuditLog.objects.filter(action="owner.mfa_factor_verified").exists())

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_verify_factor_rejects_invalid_challenge_but_records_attempt(self):
        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_CHALLENGE_TOTP": self.secret}):
            result = owner_mfa_challenge_commands.verify_factor(
                tenant_id=self.tenant.id,
                factor_id=self.factor.id,
                challenge="000000",
                actor_role="owner",
            )

        self.factor.refresh_from_db()
        self.assertEqual(result["result"], "owner-mfa-factor-challenge-invalid")
        self.assertFalse(self.factor.is_verified)
        self.assertIsNotNone(self.factor.last_challenged_at)
        self.assertTrue(AuditLog.objects.filter(action="owner.mfa_factor_verification_failed").exists())

    def test_verify_factor_is_tenant_scoped(self):
        result = owner_mfa_challenge_commands.verify_factor(
            tenant_id=self.other_tenant.id,
            factor_id=self.factor.id,
            challenge=self._current_challenge(),
            actor_role="owner",
        )

        self.assertEqual(result["result"], "owner-mfa-factor-not-found")
        self.factor.refresh_from_db()
        self.assertFalse(self.factor.is_verified)

    def test_verify_factor_blocks_without_permission(self):
        result = owner_mfa_challenge_commands.verify_factor(
            tenant_id=self.tenant.id,
            factor_id=self.factor.id,
            challenge=self._current_challenge(),
            actor_role="marketing",
        )

        self.assertEqual(result["result"], "owner-mfa-permission-denied")

    @override_settings(OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_verify_factor_blocks_local_plain_secret_when_disabled(self):
        self.factor.secret_reference = self.secret
        self.factor.provider_key = "internal"
        self.factor.save(update_fields=("secret_reference", "provider_key", "updated_at"))

        result = owner_mfa_challenge_commands.verify_factor(
            tenant_id=self.tenant.id,
            factor_id=self.factor.id,
            challenge=self._current_challenge(),
            actor_role="owner",
        )

        self.assertEqual(result["result"], "owner-mfa-factor-not-ready")

    def _current_challenge(self) -> str:
        verifier = TotpChallengeVerifier()
        secret = verifier._normalize_secret(self.secret)
        return verifier._code(secret=secret, counter=int(time.time()) // verifier.interval_seconds)


class OwnerMfaChallengeManagementCommandTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Challenge Mgmt", slug="mfa-challenge-mgmt", subdomain="mfa-challenge-mgmt")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.challenge.mgmt@hubx.market", role="owner")
        self.factor = OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="env",
            secret_reference="ref:owners/challenge-mgmt/totp",
            is_active=True,
            is_verified=False,
        )

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_verify_command_outputs_result(self):
        verifier = TotpChallengeVerifier()
        secret = verifier._normalize_secret(self.secret)
        challenge = verifier._code(secret=secret, counter=int(time.time()) // verifier.interval_seconds)
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_CHALLENGE_MGMT_TOTP": self.secret}):
            call_command(
                "owner_mfa_factor",
                "verify",
                "--tenant-id",
                str(self.tenant.id),
                "--factor-id",
                str(self.factor.id),
                "--challenge",
                challenge,
                stdout=output,
            )

        self.assertIn("owner-mfa-factor-verified", output.getvalue())
