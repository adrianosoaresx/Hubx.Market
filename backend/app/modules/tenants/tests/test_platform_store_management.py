from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from app.modules.tenants.application.platform_store_management_queries import (
    PLATFORM_TENANT_ADMIN_ROUTE,
    platform_store_management_track_closure_queries,
    platform_tenant_create_contract_queries,
    platform_tenant_custom_domain_contract_queries,
    platform_tenant_custom_domain_runtime_activation_runbook_queries,
    platform_tenant_custom_domain_runtime_resolver_evidence_review_queries,
    platform_tenant_custom_domain_runtime_resolver_review_queries,
    platform_tenant_custom_domain_runtime_production_activation_evidence_queries,
    platform_tenant_custom_domain_runtime_production_closure_queries,
    platform_tenant_custom_domain_runtime_production_gate_queries,
    platform_tenant_custom_domain_runtime_staging_evidence_queries,
    platform_tenant_admin_surface_queries,
    platform_tenant_ops_closure_queries,
    platform_tenant_owner_bootstrap_admin_surface_closure_queries,
    platform_tenant_owner_bootstrap_admin_surface_review_queries,
    platform_tenant_owner_bootstrap_production_closure_queries,
    platform_tenant_owner_bootstrap_production_evidence_queries,
    platform_tenant_owner_bootstrap_review_queries,
    platform_tenant_state_contract_queries,
)


class PlatformStoreManagementTests(TestCase):
    def test_surface_review_selects_platform_tenant_admin_contract(self):
        review = platform_tenant_admin_surface_queries.get_review(
            platform_owner_gate_confirmed=True,
            rbac_scope_confirmed=True,
            audit_events_confirmed=True,
            custom_domain_contract_confirmed=True,
            destructive_actions_deferred=True,
            tenant_isolation_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-admin-surface-ready")
        self.assertEqual(review["route"], PLATFORM_TENANT_ADMIN_ROUTE)
        self.assertIn("Platform Store Management — Tenant Admin Read-Only Surface Execution", review["next_tracks"])
        self.assertIn("deletar tenant", review["excluded_actions"])

    def test_surface_review_blocks_without_platform_owner_gate(self):
        review = platform_tenant_admin_surface_queries.get_review(
            platform_owner_gate_confirmed=False,
            rbac_scope_confirmed=True,
            audit_events_confirmed=True,
            custom_domain_contract_confirmed=True,
            destructive_actions_deferred=True,
            tenant_isolation_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn(
            "platform-tenant-admin-surface:platform_owner_gate_confirmed:missing",
            review["blockers"],
        )

    def test_management_command_outputs_surface_review(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            platform_owner_gate_confirmed=True,
            rbac_scope_confirmed=True,
            audit_events_confirmed=True,
            custom_domain_contract_confirmed=True,
            destructive_actions_deferred=True,
            tenant_isolation_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-admin-surface-ready", value)
        self.assertIn(f"route={PLATFORM_TENANT_ADMIN_ROUTE}", value)
        self.assertIn("allowed_action key=list", value)

    def test_create_contract_review_defines_minimal_write_boundary(self):
        review = platform_tenant_create_contract_queries.get_review(
            platform_permission_confirmed=True,
            unique_slug_subdomain_confirmed=True,
            reserved_subdomains_confirmed=True,
            audit_platform_scope_confirmed=True,
            no_bootstrap_side_effects_confirmed=True,
            custom_domain_contract_only_confirmed=True,
            rollback_manual_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-create-contract-ready")
        self.assertEqual(review["route"], f"{PLATFORM_TENANT_ADMIN_ROUTE}new/")
        self.assertIn("Platform Store Management — Tenant Create Command Execution", review["next_tracks"])
        self.assertEqual([field["key"] for field in review["required_fields"]], ["name", "slug", "subdomain"])
        self.assertIn("criar owner inicial automaticamente", review["excluded_actions"])

    def test_create_contract_blocks_without_audit_platform_scope(self):
        review = platform_tenant_create_contract_queries.get_review(
            platform_permission_confirmed=True,
            unique_slug_subdomain_confirmed=True,
            reserved_subdomains_confirmed=True,
            audit_platform_scope_confirmed=False,
            no_bootstrap_side_effects_confirmed=True,
            custom_domain_contract_only_confirmed=True,
            rollback_manual_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn(
            "platform-tenant-create-contract:audit_platform_scope_confirmed:missing",
            review["blockers"],
        )

    def test_management_command_outputs_create_contract_review(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="create-contract",
            platform_permission_confirmed=True,
            unique_slug_subdomain_confirmed=True,
            reserved_subdomains_confirmed=True,
            audit_platform_scope_confirmed=True,
            no_bootstrap_side_effects_confirmed=True,
            custom_domain_contract_only_confirmed=True,
            rollback_manual_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-create-contract-ready", value)
        self.assertIn(f"route={PLATFORM_TENANT_ADMIN_ROUTE}new/", value)
        self.assertIn("required_field key=name", value)
        self.assertIn("excluded_action=criar catálogo demo automaticamente", value)

    def test_state_management_contract_defines_safe_state_boundary(self):
        review = platform_tenant_state_contract_queries.get_review(
            platform_manage_permission_confirmed=True,
            audit_platform_scope_confirmed=True,
            resolver_impact_confirmed=True,
            no_commerce_side_effects_confirmed=True,
            manual_rollback_confirmed=True,
            maintenance_semantics_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-state-contract-ready")
        self.assertEqual(review["route"], f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/state/")
        self.assertIn("Platform Store Management — Tenant State Command Execution", review["next_tracks"])
        self.assertEqual([action["key"] for action in review["allowed_actions"]], ["activate", "deactivate", "maintenance-on", "maintenance-off"])
        self.assertIn("encerrar pedidos, pagamentos ou carrinhos", review["excluded_actions"])

    def test_state_management_contract_blocks_without_resolver_confirmation(self):
        review = platform_tenant_state_contract_queries.get_review(
            platform_manage_permission_confirmed=True,
            audit_platform_scope_confirmed=True,
            resolver_impact_confirmed=False,
            no_commerce_side_effects_confirmed=True,
            manual_rollback_confirmed=True,
            maintenance_semantics_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("platform-tenant-state-contract:resolver_impact_confirmed:missing", review["blockers"])

    def test_management_command_outputs_state_contract_review(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="state-contract",
            platform_manage_permission_confirmed=True,
            audit_platform_scope_confirmed=True,
            resolver_impact_confirmed=True,
            no_commerce_side_effects_confirmed=True,
            manual_rollback_confirmed=True,
            maintenance_semantics_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-state-contract-ready", value)
        self.assertIn(f"route={PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/state/", value)
        self.assertIn("allowed_action key=activate", value)

    def test_custom_domain_contract_defines_contract_only_boundary(self):
        review = platform_tenant_custom_domain_contract_queries.get_review(
            platform_manage_permission_confirmed=True,
            normalization_confirmed=True,
            uniqueness_confirmed=True,
            audit_platform_scope_confirmed=True,
            resolver_unchanged_confirmed=True,
            dns_tls_out_of_scope_confirmed=True,
            rollback_manual_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-custom-domain-contract-ready")
        self.assertEqual(review["route"], f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/custom-domain/")
        self.assertIn("Platform Store Management — Custom Domain Command Execution", review["next_tracks"])
        self.assertEqual([field["key"] for field in review["fields"]], ["custom_domain"])
        self.assertIn("alterar middleware/resolver HTTP", review["excluded_actions"])

    def test_custom_domain_contract_blocks_without_resolver_unchanged_confirmation(self):
        review = platform_tenant_custom_domain_contract_queries.get_review(
            platform_manage_permission_confirmed=True,
            normalization_confirmed=True,
            uniqueness_confirmed=True,
            audit_platform_scope_confirmed=True,
            resolver_unchanged_confirmed=False,
            dns_tls_out_of_scope_confirmed=True,
            rollback_manual_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn(
            "platform-tenant-custom-domain-contract:resolver_unchanged_confirmed:missing",
            review["blockers"],
        )

    def test_management_command_outputs_custom_domain_contract_review(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="custom-domain-contract",
            platform_manage_permission_confirmed=True,
            normalization_confirmed=True,
            uniqueness_confirmed=True,
            audit_platform_scope_confirmed=True,
            resolver_unchanged_confirmed=True,
            dns_tls_out_of_scope_confirmed=True,
            rollback_manual_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-custom-domain-contract-ready", value)
        self.assertIn(f"route={PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/custom-domain/", value)
        self.assertIn("field key=custom_domain", value)

    def test_tenant_ops_closure_marks_initial_platform_ops_track_closed(self):
        review = platform_tenant_ops_closure_queries.get_review(
            read_surface_confirmed=True,
            create_surface_confirmed=True,
            state_surface_confirmed=True,
            custom_domain_surface_confirmed=True,
            rbac_enforced_confirmed=True,
            audit_platform_scope_confirmed=True,
            contract_only_boundaries_confirmed=True,
            docs_tests_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-ops-closed")
        self.assertEqual(review["route"], PLATFORM_TENANT_ADMIN_ROUTE)
        self.assertIn("Platform Store Management — Owner Bootstrap Review", review["next_tracks"])
        self.assertEqual(
            [deliverable["key"] for deliverable in review["deliverables"]],
            ["inventory", "detail", "create", "state", "custom-domain"],
        )
        self.assertIn("resolver custom_domain no middleware HTTP", review["deferred_capabilities"])

    def test_tenant_ops_closure_blocks_without_docs_tests_confirmation(self):
        review = platform_tenant_ops_closure_queries.get_review(
            read_surface_confirmed=True,
            create_surface_confirmed=True,
            state_surface_confirmed=True,
            custom_domain_surface_confirmed=True,
            rbac_enforced_confirmed=True,
            audit_platform_scope_confirmed=True,
            contract_only_boundaries_confirmed=True,
            docs_tests_confirmed=False,
        )

        self.assertFalse(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-ops-blocked")
        self.assertIn("platform-tenant-ops-closure:docs_tests_confirmed:missing", review["blockers"])

    def test_management_command_outputs_tenant_ops_closure_review(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="ops-closure",
            read_surface_confirmed=True,
            create_surface_confirmed=True,
            state_surface_confirmed=True,
            custom_domain_surface_confirmed=True,
            rbac_enforced_confirmed=True,
            audit_platform_scope_confirmed=True,
            contract_only_boundaries_confirmed=True,
            docs_tests_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-ops-closed", value)
        self.assertIn("deliverable key=custom-domain", value)
        self.assertIn("deferred_capability=validar DNS e provisionar TLS", value)

    def test_owner_bootstrap_review_defines_invitation_only_boundary(self):
        review = platform_tenant_owner_bootstrap_review_queries.get_review(
            tenant_manage_permission_confirmed=True,
            owner_identity_boundary_confirmed=True,
            invitation_flow_confirmed=True,
            no_password_manual_confirmed=True,
            audit_platform_scope_confirmed=True,
            duplicate_owner_guard_confirmed=True,
            no_commerce_side_effects_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-owner-bootstrap-ready")
        self.assertEqual(review["route"], f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/owner-bootstrap/")
        self.assertIn("Platform Store Management — Owner Bootstrap Command Execution", review["next_tracks"])
        self.assertEqual([field["key"] for field in review["fields"]], ["owner_email", "owner_name", "owner_role"])
        self.assertIn("misturar Customer com OwnerUser", review["excluded_actions"])

    def test_owner_bootstrap_review_blocks_without_identity_boundary(self):
        review = platform_tenant_owner_bootstrap_review_queries.get_review(
            tenant_manage_permission_confirmed=True,
            owner_identity_boundary_confirmed=False,
            invitation_flow_confirmed=True,
            no_password_manual_confirmed=True,
            audit_platform_scope_confirmed=True,
            duplicate_owner_guard_confirmed=True,
            no_commerce_side_effects_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn(
            "platform-tenant-owner-bootstrap:owner_identity_boundary_confirmed:missing",
            review["blockers"],
        )

    def test_management_command_outputs_owner_bootstrap_review(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="owner-bootstrap",
            tenant_manage_permission_confirmed=True,
            owner_identity_boundary_confirmed=True,
            invitation_flow_confirmed=True,
            no_password_manual_confirmed=True,
            audit_platform_scope_confirmed=True,
            duplicate_owner_guard_confirmed=True,
            no_commerce_side_effects_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-owner-bootstrap-ready", value)
        self.assertIn("field key=owner_email", value)
        self.assertIn("excluded_action=definir senha manualmente na criação", value)

    def test_custom_domain_runtime_review_defines_safe_resolver_boundary(self):
        review = platform_tenant_custom_domain_runtime_resolver_review_queries.get_review(
            custom_domain_unique_confirmed=True,
            resolver_precedence_confirmed=True,
            active_tenant_guard_confirmed=True,
            safe_miss_confirmed=True,
            dns_tls_out_of_scope_confirmed=True,
            observability_confirmed=True,
            rollback_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-custom-domain-runtime-ready")
        self.assertEqual(review["route"], "TenantResolutionMiddleware")
        self.assertIn("Platform Store Management — Custom Domain Runtime Resolver Execution", review["next_tracks"])
        self.assertEqual(
            [rule["key"] for rule in review["resolver_rules"]],
            ["exact-host-match", "active-tenant-only", "subdomain-precedence", "no-dns-tls-provisioning", "safe-miss"],
        )
        self.assertIn("usar fallback para primeiro tenant", review["excluded_actions"])

    def test_custom_domain_runtime_review_blocks_without_safe_miss(self):
        review = platform_tenant_custom_domain_runtime_resolver_review_queries.get_review(
            custom_domain_unique_confirmed=True,
            resolver_precedence_confirmed=True,
            active_tenant_guard_confirmed=True,
            safe_miss_confirmed=False,
            dns_tls_out_of_scope_confirmed=True,
            observability_confirmed=True,
            rollback_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("platform-tenant-custom-domain-runtime:safe_miss_confirmed:missing", review["blockers"])

    def test_management_command_outputs_custom_domain_runtime_review(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="custom-domain-runtime",
            custom_domain_unique_confirmed=True,
            resolver_precedence_confirmed=True,
            active_tenant_guard_confirmed=True,
            safe_miss_confirmed=True,
            dns_tls_out_of_scope_confirmed=True,
            observability_confirmed=True,
            rollback_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-custom-domain-runtime-ready", value)
        self.assertIn("resolver_rule key=exact-host-match", value)
        self.assertIn("excluded_action=provisionar DNS automaticamente", value)

    def test_owner_bootstrap_admin_surface_review_defines_detail_action_surface(self):
        review = platform_tenant_owner_bootstrap_admin_surface_review_queries.get_review(
            command_service_confirmed=True,
            detail_entry_confirmed=True,
            manage_permission_confirmed=True,
            no_password_field_confirmed=True,
            existing_owner_state_confirmed=True,
            audit_feedback_confirmed=True,
            no_commerce_side_effects_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-owner-bootstrap-admin-surface-ready")
        self.assertEqual(review["route"], f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/owner-bootstrap/")
        self.assertIn("Platform Store Management — Owner Bootstrap Admin Surface Execution", review["next_tracks"])
        self.assertEqual(
            [element["key"] for element in review["surface_elements"]],
            ["detail-entry", "owner-email", "owner-name", "owner-role", "existing-owner-state"],
        )

    def test_owner_bootstrap_admin_surface_review_blocks_without_no_password_field(self):
        review = platform_tenant_owner_bootstrap_admin_surface_review_queries.get_review(
            command_service_confirmed=True,
            detail_entry_confirmed=True,
            manage_permission_confirmed=True,
            no_password_field_confirmed=False,
            existing_owner_state_confirmed=True,
            audit_feedback_confirmed=True,
            no_commerce_side_effects_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn(
            "platform-tenant-owner-bootstrap-admin-surface:no_password_field_confirmed:missing",
            review["blockers"],
        )

    def test_management_command_outputs_owner_bootstrap_admin_surface_review(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="owner-bootstrap-admin-surface",
            command_service_confirmed=True,
            detail_entry_confirmed=True,
            manage_permission_confirmed=True,
            no_password_field_confirmed=True,
            existing_owner_state_confirmed=True,
            audit_feedback_confirmed=True,
            no_commerce_side_effects_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-owner-bootstrap-admin-surface-ready", value)
        self.assertIn("surface_element key=owner-email", value)

    def test_custom_domain_runtime_evidence_review_defines_activation_evidence_pack(self):
        review = platform_tenant_custom_domain_runtime_resolver_evidence_review_queries.get_review(
            resolver_flag_confirmed=True,
            flag_off_evidence_confirmed=True,
            flag_on_evidence_confirmed=True,
            inactive_tenant_evidence_confirmed=True,
            safe_miss_evidence_confirmed=True,
            rollback_evidence_confirmed=True,
            dns_tls_external_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-custom-domain-runtime-evidence-ready")
        self.assertEqual(review["route"], "TenantResolutionMiddleware")
        self.assertIn(
            "Platform Store Management — Custom Domain Runtime Resolver Activation Runbook",
            review["next_tracks"],
        )
        self.assertEqual(
            [item["key"] for item in review["evidence_items"]],
            ["flag-off-smoke", "flag-on-smoke", "inactive-tenant-smoke", "safe-miss-smoke", "rollback"],
        )

    def test_custom_domain_runtime_evidence_review_blocks_without_rollback_evidence(self):
        review = platform_tenant_custom_domain_runtime_resolver_evidence_review_queries.get_review(
            resolver_flag_confirmed=True,
            flag_off_evidence_confirmed=True,
            flag_on_evidence_confirmed=True,
            inactive_tenant_evidence_confirmed=True,
            safe_miss_evidence_confirmed=True,
            rollback_evidence_confirmed=False,
            dns_tls_external_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn(
            "platform-tenant-custom-domain-runtime-evidence:rollback_evidence_confirmed:missing",
            review["blockers"],
        )

    def test_management_command_outputs_custom_domain_runtime_evidence_review(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="custom-domain-runtime-evidence",
            resolver_flag_confirmed=True,
            flag_off_evidence_confirmed=True,
            flag_on_evidence_confirmed=True,
            inactive_tenant_evidence_confirmed=True,
            safe_miss_evidence_confirmed=True,
            rollback_evidence_confirmed=True,
            dns_tls_external_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-custom-domain-runtime-evidence-ready", value)
        self.assertIn("evidence_item key=flag-on-smoke", value)

    def test_custom_domain_runtime_activation_runbook_defines_operational_steps(self):
        runbook = platform_tenant_custom_domain_runtime_activation_runbook_queries.get_runbook(
            environment="staging",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            rollback_owner="ops@hubx.market",
        )

        self.assertTrue(runbook["ready"])
        self.assertEqual(runbook["result"], "platform-tenant-custom-domain-runtime-runbook-ready")
        self.assertEqual(runbook["feature_flag"], "HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED")
        self.assertEqual([step["key"] for step in runbook["steps"]], [
            "preflight",
            "flag-off-smoke",
            "flag-on-smoke",
            "inactive-smoke",
            "safe-miss-smoke",
            "rollback",
        ])
        self.assertIn("Platform Store Management — Custom Domain Runtime Staging Activation Evidence", runbook["next_tracks"])

    def test_custom_domain_runtime_activation_runbook_blocks_without_target_domain(self):
        runbook = platform_tenant_custom_domain_runtime_activation_runbook_queries.get_runbook(
            environment="staging",
            tenant_slug="demo",
            custom_domain="",
        )

        self.assertFalse(runbook["ready"])
        self.assertIn("platform-tenant-custom-domain-runtime-runbook:custom_domain:missing", runbook["blockers"])

    def test_management_command_outputs_custom_domain_runtime_activation_runbook(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="custom-domain-runtime-runbook",
            environment="staging",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            rollback_owner="ops@hubx.market",
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-custom-domain-runtime-runbook-ready", value)
        self.assertIn("runbook_step key=flag-on-smoke", value)
        self.assertIn("feature_flag=HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED", value)

    def test_owner_bootstrap_admin_surface_closure_marks_surface_closed(self):
        review = platform_tenant_owner_bootstrap_admin_surface_closure_queries.get_review(
            form_render_confirmed=True,
            post_action_confirmed=True,
            permission_denied_confirmed=True,
            existing_owner_block_confirmed=True,
            audit_platform_scope_confirmed=True,
            no_password_field_confirmed=True,
            tests_docs_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-owner-bootstrap-admin-surface-closed")
        self.assertEqual(review["route"], f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/owner-bootstrap/")
        self.assertIn("Platform Store Management — Owner Bootstrap Production Evidence", review["next_tracks"])
        self.assertEqual(
            [item["key"] for item in review["deliverables"]],
            ["detail-form", "blocked-state", "post-action", "audit", "no-password"],
        )

    def test_owner_bootstrap_admin_surface_closure_blocks_without_permission_denied_evidence(self):
        review = platform_tenant_owner_bootstrap_admin_surface_closure_queries.get_review(
            form_render_confirmed=True,
            post_action_confirmed=True,
            permission_denied_confirmed=False,
            existing_owner_block_confirmed=True,
            audit_platform_scope_confirmed=True,
            no_password_field_confirmed=True,
            tests_docs_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn(
            "platform-tenant-owner-bootstrap-admin-closure:permission_denied_confirmed:missing",
            review["blockers"],
        )

    def test_management_command_outputs_owner_bootstrap_admin_surface_closure(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="owner-bootstrap-admin-closure",
            form_render_confirmed=True,
            post_action_confirmed=True,
            permission_denied_confirmed=True,
            existing_owner_block_confirmed=True,
            audit_platform_scope_confirmed=True,
            no_password_field_confirmed=True,
            tests_docs_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-owner-bootstrap-admin-surface-closed", value)
        self.assertIn("deliverable key=no-password", value)

    def test_custom_domain_runtime_staging_evidence_marks_package_ready(self):
        evidence = platform_tenant_custom_domain_runtime_staging_evidence_queries.get_evidence(
            environment="staging",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            flag_off_confirmed=True,
            flag_on_confirmed=True,
            inactive_tenant_confirmed=True,
            safe_miss_confirmed=True,
            rollback_confirmed=True,
            dns_tls_external_confirmed=True,
        )

        self.assertTrue(evidence["ready"])
        self.assertEqual(evidence["result"], "platform-tenant-custom-domain-staging-evidence-ready")
        self.assertEqual(evidence["feature_flag"], "HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED")
        self.assertIn("Platform Store Management — Custom Domain Runtime Production Gate Review", evidence["next_tracks"])
        self.assertEqual(
            [item["key"] for item in evidence["evidence_items"]],
            ["staging-target", "flag-off-result", "flag-on-result", "inactive-result", "safe-miss-result", "rollback-result"],
        )

    def test_custom_domain_runtime_staging_evidence_blocks_without_safe_miss(self):
        evidence = platform_tenant_custom_domain_runtime_staging_evidence_queries.get_evidence(
            environment="staging",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            flag_off_confirmed=True,
            flag_on_confirmed=True,
            inactive_tenant_confirmed=True,
            safe_miss_confirmed=False,
            rollback_confirmed=True,
            dns_tls_external_confirmed=True,
        )

        self.assertFalse(evidence["ready"])
        self.assertIn(
            "platform-tenant-custom-domain-staging-evidence:safe_miss_confirmed:missing",
            evidence["blockers"],
        )

    def test_management_command_outputs_custom_domain_runtime_staging_evidence(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="custom-domain-staging-evidence",
            environment="staging",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            flag_off_confirmed=True,
            flag_on_confirmed=True,
            inactive_tenant_confirmed=True,
            safe_miss_confirmed=True,
            rollback_confirmed=True,
            dns_tls_external_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-custom-domain-staging-evidence-ready", value)
        self.assertIn("evidence_item key=flag-on-result", value)

    def test_owner_bootstrap_production_evidence_marks_package_ready(self):
        evidence = platform_tenant_owner_bootstrap_production_evidence_queries.get_evidence(
            environment="production",
            tenant_slug="demo",
            owner_email="owner@example.com",
            owner_created_confirmed=True,
            unusable_password_confirmed=True,
            platform_audit_confirmed=True,
            tenant_audit_confirmed=True,
            no_auto_login_confirmed=True,
            rollback_contact_confirmed=True,
        )

        self.assertTrue(evidence["ready"])
        self.assertEqual(evidence["result"], "platform-tenant-owner-bootstrap-production-evidence-ready")
        self.assertEqual(evidence["owner_email"], "owner@example.com")
        self.assertIn("Platform Store Management — Owner Bootstrap Production Closure", evidence["next_tracks"])
        self.assertEqual(
            [item["key"] for item in evidence["evidence_items"]],
            ["target-tenant", "owner-created", "unusable-password", "platform-audit", "tenant-audit", "login-not-automatic"],
        )

    def test_owner_bootstrap_production_evidence_blocks_without_tenant_audit(self):
        evidence = platform_tenant_owner_bootstrap_production_evidence_queries.get_evidence(
            environment="production",
            tenant_slug="demo",
            owner_email="owner@example.com",
            owner_created_confirmed=True,
            unusable_password_confirmed=True,
            platform_audit_confirmed=True,
            tenant_audit_confirmed=False,
            no_auto_login_confirmed=True,
            rollback_contact_confirmed=True,
        )

        self.assertFalse(evidence["ready"])
        self.assertIn(
            "platform-tenant-owner-bootstrap-production-evidence:tenant_audit_confirmed:missing",
            evidence["blockers"],
        )

    def test_management_command_outputs_owner_bootstrap_production_evidence(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="owner-bootstrap-production-evidence",
            environment="production",
            tenant_slug="demo",
            owner_email="owner@example.com",
            owner_created_confirmed=True,
            unusable_password_confirmed=True,
            platform_audit_confirmed=True,
            tenant_audit_confirmed=True,
            no_auto_login_confirmed=True,
            rollback_contact_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-owner-bootstrap-production-evidence-ready", value)
        self.assertIn("evidence_item key=unusable-password", value)
        self.assertIn("owner_email=owner@example.com", value)

    def test_custom_domain_runtime_production_gate_returns_go_when_all_signals_confirmed(self):
        gate = platform_tenant_custom_domain_runtime_production_gate_queries.get_review(
            environment="production",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            staging_evidence_confirmed=True,
            dns_tls_confirmed=True,
            feature_flag_confirmed=True,
            rollback_owner_confirmed=True,
            monitoring_window_confirmed=True,
            support_comms_confirmed=True,
        )

        self.assertTrue(gate["ready"])
        self.assertEqual(gate["result"], "platform-tenant-custom-domain-production-gate-go")
        self.assertEqual(gate["decision"], "GO")
        self.assertIn("Platform Store Management — Custom Domain Runtime Production Activation Evidence", gate["next_tracks"])
        self.assertEqual(
            [item["key"] for item in gate["gate_items"]],
            ["staging-evidence", "tenant-target", "dns-tls-external", "feature-flag", "rollback-owner", "monitoring-window"],
        )

    def test_custom_domain_runtime_production_gate_returns_no_go_without_dns_tls(self):
        gate = platform_tenant_custom_domain_runtime_production_gate_queries.get_review(
            environment="production",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            staging_evidence_confirmed=True,
            dns_tls_confirmed=False,
            feature_flag_confirmed=True,
            rollback_owner_confirmed=True,
            monitoring_window_confirmed=True,
            support_comms_confirmed=True,
        )

        self.assertFalse(gate["ready"])
        self.assertEqual(gate["decision"], "NO-GO")
        self.assertIn("platform-tenant-custom-domain-production-gate:dns_tls_confirmed:missing", gate["blockers"])

    def test_management_command_outputs_custom_domain_runtime_production_gate(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="custom-domain-production-gate",
            environment="production",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            staging_evidence_confirmed=True,
            dns_tls_confirmed=True,
            feature_flag_confirmed=True,
            rollback_owner_confirmed=True,
            monitoring_window_confirmed=True,
            support_comms_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-custom-domain-production-gate-go", value)
        self.assertIn("decision=GO", value)
        self.assertIn("gate_item key=dns-tls-external", value)

    def test_owner_bootstrap_production_closure_marks_track_closed(self):
        review = platform_tenant_owner_bootstrap_production_closure_queries.get_review(
            environment="production",
            tenant_slug="demo",
            owner_email="owner@example.com",
            production_evidence_confirmed=True,
            owner_access_ready_confirmed=True,
            audit_trail_confirmed=True,
            no_impersonation_confirmed=True,
            operational_handoff_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-owner-bootstrap-production-closed")
        self.assertIn("Platform Store Management — Store Management Track Closure", review["next_tracks"])
        self.assertEqual(
            [item["key"] for item in review["deliverables"]],
            ["production-evidence", "owner-access", "audit-trail", "no-impersonation", "handoff"],
        )

    def test_owner_bootstrap_production_closure_blocks_without_handoff(self):
        review = platform_tenant_owner_bootstrap_production_closure_queries.get_review(
            environment="production",
            tenant_slug="demo",
            owner_email="owner@example.com",
            production_evidence_confirmed=True,
            owner_access_ready_confirmed=True,
            audit_trail_confirmed=True,
            no_impersonation_confirmed=True,
            operational_handoff_confirmed=False,
        )

        self.assertFalse(review["ready"])
        self.assertIn(
            "platform-tenant-owner-bootstrap-production-closure:operational_handoff_confirmed:missing",
            review["blockers"],
        )

    def test_management_command_outputs_owner_bootstrap_production_closure(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="owner-bootstrap-production-closure",
            environment="production",
            tenant_slug="demo",
            owner_email="owner@example.com",
            production_evidence_confirmed=True,
            owner_access_ready_confirmed=True,
            audit_trail_confirmed=True,
            no_impersonation_confirmed=True,
            operational_handoff_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-owner-bootstrap-production-closed", value)
        self.assertIn("deliverable key=handoff", value)

    def test_custom_domain_runtime_production_activation_evidence_marks_ready(self):
        evidence = platform_tenant_custom_domain_runtime_production_activation_evidence_queries.get_evidence(
            environment="production",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            production_gate_go_confirmed=True,
            flag_enabled_confirmed=True,
            custom_domain_smoke_confirmed=True,
            subdomain_smoke_confirmed=True,
            safe_miss_confirmed=True,
            rollback_ready_confirmed=True,
            monitoring_captured_confirmed=True,
        )

        self.assertTrue(evidence["ready"])
        self.assertEqual(evidence["result"], "platform-tenant-custom-domain-production-activation-evidence-ready")
        self.assertIn("Platform Store Management — Custom Domain Runtime Production Closure", evidence["next_tracks"])
        self.assertEqual(
            [item["key"] for item in evidence["evidence_items"]],
            [
                "production-gate",
                "flag-enabled",
                "custom-domain-smoke",
                "subdomain-smoke",
                "safe-miss-smoke",
                "rollback-ready",
                "monitoring-captured",
            ],
        )

    def test_custom_domain_runtime_production_activation_evidence_blocks_without_gate(self):
        evidence = platform_tenant_custom_domain_runtime_production_activation_evidence_queries.get_evidence(
            environment="production",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            production_gate_go_confirmed=False,
            flag_enabled_confirmed=True,
            custom_domain_smoke_confirmed=True,
            subdomain_smoke_confirmed=True,
            safe_miss_confirmed=True,
            rollback_ready_confirmed=True,
            monitoring_captured_confirmed=True,
        )

        self.assertFalse(evidence["ready"])
        self.assertIn(
            "platform-tenant-custom-domain-production-activation:production_gate_go_confirmed:missing",
            evidence["blockers"],
        )

    def test_management_command_outputs_custom_domain_runtime_production_activation_evidence(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="custom-domain-production-activation",
            environment="production",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            production_gate_go_confirmed=True,
            flag_enabled_confirmed=True,
            custom_domain_smoke_confirmed=True,
            subdomain_smoke_confirmed=True,
            safe_miss_confirmed=True,
            rollback_ready_confirmed=True,
            monitoring_captured_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-custom-domain-production-activation-evidence-ready", value)
        self.assertIn("evidence_item key=custom-domain-smoke", value)

    def test_custom_domain_runtime_production_closure_marks_runtime_closed(self):
        review = platform_tenant_custom_domain_runtime_production_closure_queries.get_review(
            environment="production",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            activation_evidence_confirmed=True,
            resolver_source_confirmed=True,
            rollback_ready_confirmed=True,
            monitoring_confirmed=True,
            dns_tls_external_confirmed=True,
            support_handoff_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-tenant-custom-domain-production-closed")
        self.assertIn("Platform Store Management — Store Management Track Closure", review["next_tracks"])
        self.assertEqual(
            [item["key"] for item in review["deliverables"]],
            ["activation-evidence", "resolver-source", "rollback-ready", "monitoring", "no-dns-tls-runtime"],
        )

    def test_custom_domain_runtime_production_closure_blocks_without_resolver_source(self):
        review = platform_tenant_custom_domain_runtime_production_closure_queries.get_review(
            environment="production",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            activation_evidence_confirmed=True,
            resolver_source_confirmed=False,
            rollback_ready_confirmed=True,
            monitoring_confirmed=True,
            dns_tls_external_confirmed=True,
            support_handoff_confirmed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn(
            "platform-tenant-custom-domain-production-closure:resolver_source_confirmed:missing",
            review["blockers"],
        )

    def test_management_command_outputs_custom_domain_runtime_production_closure(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="custom-domain-production-closure",
            environment="production",
            tenant_slug="demo",
            custom_domain="loja.example.com",
            activation_evidence_confirmed=True,
            resolver_source_confirmed=True,
            rollback_ready_confirmed=True,
            monitoring_confirmed=True,
            dns_tls_external_confirmed=True,
            support_handoff_confirmed=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-custom-domain-production-closed", value)
        self.assertIn("deliverable key=resolver-source", value)

    def test_store_management_track_closure_marks_track_closed(self):
        review = platform_store_management_track_closure_queries.get_review(
            tenant_ops_closed_confirmed=True,
            owner_bootstrap_closed_confirmed=True,
            custom_domain_runtime_closed_confirmed=True,
            production_evidence_confirmed=True,
            docs_tests_confirmed=True,
            remaining_risks_accepted=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "platform-store-management-track-closed")
        self.assertIn("System ROI Re-Selection Review", review["next_tracks"])
        self.assertEqual(
            [item["key"] for item in review["deliverables"]],
            ["tenant-ops", "owner-bootstrap", "custom-domain-contract", "custom-domain-runtime", "docs-tests"],
        )

    def test_store_management_track_closure_blocks_without_risk_acceptance(self):
        review = platform_store_management_track_closure_queries.get_review(
            tenant_ops_closed_confirmed=True,
            owner_bootstrap_closed_confirmed=True,
            custom_domain_runtime_closed_confirmed=True,
            production_evidence_confirmed=True,
            docs_tests_confirmed=True,
            remaining_risks_accepted=False,
        )

        self.assertFalse(review["ready"])
        self.assertIn(
            "platform-store-management-track-closure:remaining_risks_accepted:missing",
            review["blockers"],
        )

    def test_management_command_outputs_store_management_track_closure(self):
        output = StringIO()
        call_command(
            "platform_tenant_admin_surface_review",
            review="store-management-track-closure",
            tenant_ops_closed_confirmed=True,
            owner_bootstrap_closed_confirmed=True,
            custom_domain_runtime_closed_confirmed=True,
            production_evidence_confirmed=True,
            docs_tests_confirmed=True,
            remaining_risks_accepted=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-store-management-track-closed", value)
        self.assertIn("deliverable key=custom-domain-runtime", value)
