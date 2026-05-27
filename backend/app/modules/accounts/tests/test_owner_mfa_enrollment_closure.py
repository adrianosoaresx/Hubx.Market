from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from app.modules.accounts.application.owner_mfa_enrollment_closure_queries import owner_mfa_enrollment_closure_queries


class OwnerMfaEnrollmentClosureTests(TestCase):
    def test_closure_is_ready_and_lists_next_tracks(self):
        closure = owner_mfa_enrollment_closure_queries.get_closure()

        self.assertEqual(closure["result"], "owner-mfa-enrollment-closure-ready")
        self.assertTrue(closure["ready"])
        self.assertIn("Owner MFA Admin Surface Review", closure["next_tracks"])

    def test_command_outputs_closure(self):
        output = StringIO()

        call_command("owner_mfa_enrollment_closure", stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("decision key=mfa-factor-model", output.getvalue())
        self.assertIn("decision key=mfa-challenge-verification", output.getvalue())
