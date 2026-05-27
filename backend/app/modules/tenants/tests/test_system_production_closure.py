from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from app.modules.tenants.application.system_production_closure_queries import (
    system_production_go_nogo_queries,
    system_production_readiness_matrix_queries,
    system_production_runbook_gap_queries,
    system_production_smoke_checklist_queries,
)


class SystemProductionClosureTests(TestCase):
    def test_readiness_matrix_exposes_cross_module_statuses(self):
        review = system_production_readiness_matrix_queries.get_review(
            matrix_reviewed=True,
            watch_risks_accepted=True,
        )

        self.assertTrue(review["ready"])
        modules = {row["module"]: row["status"] for row in review["matrix"]}
        self.assertEqual(modules["catalog"], "ready")
        self.assertEqual(modules["payments"], "watch")
        self.assertEqual(review["result"], "system-production-matrix-ready")

    def test_runbook_review_blocks_missing_critical_runbook(self):
        review = system_production_runbook_gap_queries.get_review(
            payments_runbook_ready=False,
            notifications_runbook_ready=True,
            shipping_runbook_ready=True,
            catalog_runbook_ready=True,
            checkout_runbook_ready=True,
            incident_owner_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("system-production-runbooks:payments_runbook_ready:missing", review["blockers"])

    def test_smoke_checklist_requires_no_sensitive_output(self):
        review = system_production_smoke_checklist_queries.get_review(
            tenant_resolution_smoke=True,
            storefront_catalog_smoke=True,
            cart_checkout_smoke=True,
            payment_provider_smoke=True,
            notification_smoke=True,
            api_key_smoke=True,
            no_sensitive_output=False,
        )

        self.assertFalse(review["ready"])
        self.assertIn("system-production-smoke:no_sensitive_output:missing", review["blockers"])

    def test_go_nogo_returns_go_when_all_closure_signals_are_ready(self):
        review = system_production_go_nogo_queries.get_review(
            readiness_matrix_ready=True,
            runbooks_ready=True,
            smoke_checklist_ready=True,
            observability_ready=True,
            rollback_drill_ready=True,
            residual_risks_accepted=True,
            decision_owner_confirmed=True,
            docs_updated=True,
            decision_recorded=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["status"], "go")
        self.assertEqual(review["result"], "system-production-go")
        self.assertIn("Growth/Commercial Activation Track", review["next_tracks"])

    def test_go_nogo_returns_no_go_with_blocker_track(self):
        review = system_production_go_nogo_queries.get_review(
            readiness_matrix_ready=True,
            runbooks_ready=False,
            smoke_checklist_ready=True,
            observability_ready=True,
            rollback_drill_ready=True,
            residual_risks_accepted=True,
            decision_owner_confirmed=True,
            docs_updated=True,
            decision_recorded=True,
        )

        self.assertFalse(review["ready"])
        self.assertEqual(review["status"], "no-go")
        self.assertIn("Production Corrective Battery", review["next_tracks"])

    def test_management_command_outputs_go_nogo(self):
        output = StringIO()
        call_command(
            "system_production_closure",
            review="go-nogo",
            readiness_matrix_ready=True,
            runbooks_ready=True,
            smoke_checklist_ready=True,
            observability_ready=True,
            rollback_drill_ready=True,
            residual_risks_accepted=True,
            decision_owner_confirmed=True,
            docs_updated=True,
            decision_recorded=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=system-production-go", value)
        self.assertIn("decision key=production status=go", value)
        self.assertIn("next_track=Growth/Commercial Activation Track", value)
