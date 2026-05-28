from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.tenants.application.system_roi_reselection_queries import system_roi_reselection_queries


class SystemRoiReselectionTests(TestCase):
    def test_reselection_prioritizes_storefront_smoke_when_regression_pressure_is_confirmed(self):
        review = system_roi_reselection_queries.get_review(
            **self._store_management_closed_flags(),
            production_validation_preferred=True,
            storefront_regression_pressure_confirmed=True,
            payments_provider_blocker_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "system-roi-reselection-ready")
        self.assertEqual(
            review["recommendation"].recommended_track,
            "System Validation Pass 2 — Storefront/Admin Smoke & Template Regression",
        )
        self.assertIn("System Validation Pass 2 — Storefront/Admin Smoke & Template Regression", review["next_tracks"])

    def test_reselection_can_prioritize_payments_when_provider_blocker_is_confirmed(self):
        review = system_roi_reselection_queries.get_review(
            **self._store_management_closed_flags(),
            payments_provider_blocker_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["recommendation"].recommended_track, "Payments Production Readiness Review")

    def test_reselection_blocks_when_store_management_is_not_closed(self):
        review = system_roi_reselection_queries.get_review(
            production_validation_preferred=True,
            storefront_regression_pressure_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("store-management:platform-store-management-track-blocked", review["blockers"])
        self.assertIn(
            "store-management:platform-store-management-track-closure:tenant_ops_closed_confirmed:missing",
            review["blockers"],
        )

    def test_command_outputs_recommendation(self):
        output = StringIO()

        call_command(
            "system_roi_reselection",
            *self._store_management_closed_args(),
            "--production-validation-preferred",
            "--storefront-regression-pressure-confirmed",
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("recommendation=System Validation Pass 2 — Storefront/Admin Smoke & Template Regression", value)
        self.assertIn("candidate key=storefront-admin-smoke-regression", value)
        self.assertIn("decision key=visible-regression-pressure status=confirmed", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("system_roi_reselection", "--fail-on-blockers", stdout=StringIO())

    def _store_management_closed_flags(self) -> dict[str, bool]:
        return {
            "tenant_ops_closed_confirmed": True,
            "owner_bootstrap_closed_confirmed": True,
            "custom_domain_runtime_closed_confirmed": True,
            "production_evidence_confirmed": True,
            "docs_tests_confirmed": True,
            "remaining_risks_accepted": True,
        }

    def _store_management_closed_args(self) -> tuple[str, ...]:
        return (
            "--tenant-ops-closed-confirmed",
            "--owner-bootstrap-closed-confirmed",
            "--custom-domain-runtime-closed-confirmed",
            "--production-evidence-confirmed",
            "--docs-tests-confirmed",
            "--remaining-risks-accepted",
        )
