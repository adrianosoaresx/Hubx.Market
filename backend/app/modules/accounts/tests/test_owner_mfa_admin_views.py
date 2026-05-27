from __future__ import annotations

import time
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.application.owner_mfa_challenge_commands import TotpChallengeVerifier
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=["testserver", ".hubx.market", "localhost"])
class OwnerMfaAdminViewTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Admin", slug="mfa-admin", subdomain="mfa-admin")
        self.other_tenant = Tenant.objects.create(name="MFA Admin Other", slug="mfa-admin-other", subdomain="mfa-admin-other")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.admin@hubx.market", role="owner")
        self.factor = OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="env",
            secret_reference="ref:owners/admin/totp",
            is_active=True,
            is_verified=False,
        )

    def test_mfa_list_renders_tenant_factors(self):
        other_owner = OwnerUser.objects.create(tenant=self.other_tenant, email="other.owner@hubx.market", role="owner")
        OwnerMfaFactor.objects.create(
            tenant=self.other_tenant,
            owner=other_owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            secret_reference=self.secret,
        )

        response = self.client.get(
            reverse("owners:admin-owner-mfa-list"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "owner.mfa.admin@hubx.market")
        self.assertContains(response, "Pendente")
        self.assertNotContains(response, "other.owner@hubx.market")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_mfa_verify_action_marks_factor_verified(self):
        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_ADMIN_TOTP": self.secret}):
            response = self.client.post(
                reverse("owners:admin-owner-mfa-verify", kwargs={"factor_id": self.factor.id}),
                data={"challenge": self._current_challenge(), "next": reverse("owners:admin-owner-mfa-list")},
                HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
            )

        self.factor.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertIn("result=owner-mfa-factor-verified", response["Location"])
        self.assertTrue(self.factor.is_verified)
        self.assertTrue(AuditLog.objects.filter(action="owner.mfa_factor_verified").exists())

    def test_mfa_deactivate_action_marks_factor_inactive(self):
        response = self.client.post(
            reverse("owners:admin-owner-mfa-deactivate", kwargs={"factor_id": self.factor.id}),
            data={"next": reverse("owners:admin-owner-mfa-list")},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.factor.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertIn("result=owner-mfa-factor-deactivated", response["Location"])
        self.assertFalse(self.factor.is_active)

    def _current_challenge(self) -> str:
        verifier = TotpChallengeVerifier()
        secret = verifier._normalize_secret(self.secret)
        return verifier._code(secret=secret, counter=int(time.time()) // verifier.interval_seconds)
