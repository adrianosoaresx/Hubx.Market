from django.core.management import call_command
from django.test import TestCase

from app.modules.api_keys.application.api_key_commands import api_key_commands
from app.modules.api_keys.application.api_key_quota_commands import api_key_quota_commands
from app.modules.audit.application.audit_instrumentation_expansion_queries import audit_instrumentation_expansion_queries
from app.modules.audit.models import AuditLog
from app.modules.catalog.application.admin_product_commands import admin_product_commands
from app.modules.catalog.models import Product
from app.modules.tenants.models import Tenant


class AuditInstrumentationExpansionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Audit Expansion", slug="audit-expansion", subdomain="audit-expansion")
        self.other_tenant = Tenant.objects.create(name="Other Audit Expansion", slug="other-audit-expansion", subdomain="other-audit-expansion")

    def test_review_closes_battery_f_when_all_signals_are_present(self):
        review = audit_instrumentation_expansion_queries.get_review(
            critical_inventory_ready=True,
            payment_admin_actions_ready=True,
            api_key_actions_ready=True,
            catalog_admin_actions_ready=True,
            evidence_review_ready=True,
            metadata_redaction_ready=True,
            tenant_scope_confirmed=True,
            docs_updated=True,
            decision_recorded=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "audit-instrumentation-expansion-ready")
        self.assertIn("catalog.product.visibility_updated", review["instrumented_actions"])
        self.assertIn("Battery G — Notifications Production Delivery", review["next_tracks"])

    def test_catalog_visibility_command_records_tenant_scoped_audit_event(self):
        product = Product.objects.create(
            tenant=self.tenant,
            name="Produto crítico",
            slug="produto-critico",
            status=Product.Status.DRAFT,
            is_active=False,
            is_featured=False,
        )

        result = admin_product_commands.update_product_visibility(
            tenant_id=self.tenant.id,
            product_id=product.id,
            status=Product.Status.ACTIVE,
            is_active=True,
            is_featured=True,
            actor_label="catalog-owner@example.com",
        )

        self.assertEqual(result["result"], "product-visibility-updated")
        log = AuditLog.objects.get(module="catalog", action="product.visibility_updated")
        self.assertEqual(log.tenant, self.tenant)
        self.assertEqual(log.entity_type, "Product")
        self.assertEqual(log.entity_id, str(product.id))
        self.assertEqual(log.actor_label, "catalog-owner@example.com")
        self.assertEqual(log.metadata["previous_status"], Product.Status.DRAFT)
        self.assertEqual(log.metadata["status"], Product.Status.ACTIVE)
        self.assertTrue(log.metadata["is_active"])

    def test_catalog_visibility_command_blocks_cross_tenant_update(self):
        product = Product.objects.create(
            tenant=self.tenant,
            name="Produto isolado",
            slug="produto-isolado",
            status=Product.Status.DRAFT,
            is_active=False,
        )

        result = admin_product_commands.update_product_visibility(
            tenant_id=self.other_tenant.id,
            product_id=product.id,
            status=Product.Status.ACTIVE,
            is_active=True,
            actor_label="catalog-owner@example.com",
        )

        self.assertEqual(result["result"], "product-visibility-not-found")
        self.assertFalse(AuditLog.objects.filter(module="catalog").exists())

    def test_api_key_actions_remain_instrumented_without_secret_metadata(self):
        create_result = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="Partner key",
            scopes=("read:catalog",),
            actor_label="owner@example.com",
        )
        api_key_id = create_result["api_key"]["id"]
        api_key_quota_commands.upsert_quota(
            tenant_id=self.tenant.id,
            api_key_id=api_key_id,
            endpoint="catalog.products.list",
            limit=50,
            actor_label="owner@example.com",
        )
        api_key_commands.revoke_key(
            tenant_id=self.tenant.id,
            key_id=api_key_id,
            actor_label="owner@example.com",
        )

        actions = set(AuditLog.objects.filter(tenant=self.tenant, module="api_keys").values_list("action", flat=True))
        self.assertEqual(actions, {"api_key.created", "api_key.quota_upserted", "api_key.revoked"})
        for log in AuditLog.objects.filter(tenant=self.tenant, module="api_keys"):
            self.assertNotIn("secret", log.metadata)
            self.assertNotIn("key_hash", log.metadata)

    def test_management_command_reports_ready_closure(self):
        from io import StringIO

        output = StringIO()
        call_command(
            "audit_instrumentation_expansion",
            critical_inventory_ready=True,
            payment_admin_actions_ready=True,
            api_key_actions_ready=True,
            catalog_admin_actions_ready=True,
            evidence_review_ready=True,
            metadata_redaction_ready=True,
            tenant_scope_confirmed=True,
            docs_updated=True,
            decision_recorded=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=audit-instrumentation-expansion-ready", value)
        self.assertIn("instrumented_action=payments.refund.approved", value)
        self.assertIn("next_track=Battery G — Notifications Production Delivery", value)
