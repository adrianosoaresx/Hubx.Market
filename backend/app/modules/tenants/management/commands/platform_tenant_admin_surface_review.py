from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.tenants.application.platform_store_management_queries import (
    platform_store_management_track_closure_queries,
    platform_tenant_create_contract_queries,
    platform_tenant_custom_domain_contract_queries,
    platform_tenant_custom_domain_runtime_activation_runbook_queries,
    platform_tenant_custom_domain_runtime_resolver_evidence_review_queries,
    platform_tenant_custom_domain_runtime_resolver_review_queries,
    platform_tenant_custom_domain_runtime_production_activation_evidence_queries,
    platform_tenant_custom_domain_runtime_production_gate_queries,
    platform_tenant_custom_domain_runtime_production_closure_queries,
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


class Command(BaseCommand):
    help = "Revisa o contrato inicial da surface platform de gerenciamento de lojas/tenants."

    def add_arguments(self, parser):
        parser.add_argument(
            "--review",
            choices=(
                "surface",
                "create-contract",
                "state-contract",
                "custom-domain-contract",
                "ops-closure",
                "owner-bootstrap",
                "custom-domain-runtime",
                "owner-bootstrap-admin-surface",
                "custom-domain-runtime-evidence",
                "custom-domain-runtime-runbook",
                "owner-bootstrap-admin-closure",
                "custom-domain-staging-evidence",
                "owner-bootstrap-production-evidence",
                "custom-domain-production-gate",
                "owner-bootstrap-production-closure",
                "custom-domain-production-activation",
                "store-management-track-closure",
                "custom-domain-production-closure",
            ),
            default="surface",
        )
        for name in (
            "platform-owner-gate-confirmed",
            "rbac-scope-confirmed",
            "audit-events-confirmed",
            "custom-domain-contract-confirmed",
            "destructive-actions-deferred",
            "tenant-isolation-confirmed",
            "platform-permission-confirmed",
            "unique-slug-subdomain-confirmed",
            "reserved-subdomains-confirmed",
            "audit-platform-scope-confirmed",
            "no-bootstrap-side-effects-confirmed",
            "custom-domain-contract-only-confirmed",
            "rollback-manual-confirmed",
            "platform-manage-permission-confirmed",
            "resolver-impact-confirmed",
            "no-commerce-side-effects-confirmed",
            "manual-rollback-confirmed",
            "maintenance-semantics-confirmed",
            "normalization-confirmed",
            "uniqueness-confirmed",
            "resolver-unchanged-confirmed",
            "dns-tls-out-of-scope-confirmed",
            "read-surface-confirmed",
            "create-surface-confirmed",
            "state-surface-confirmed",
            "custom-domain-surface-confirmed",
            "rbac-enforced-confirmed",
            "contract-only-boundaries-confirmed",
            "docs-tests-confirmed",
            "tenant-manage-permission-confirmed",
            "owner-identity-boundary-confirmed",
            "invitation-flow-confirmed",
            "no-password-manual-confirmed",
            "duplicate-owner-guard-confirmed",
            "custom-domain-unique-confirmed",
            "resolver-precedence-confirmed",
            "active-tenant-guard-confirmed",
            "safe-miss-confirmed",
            "observability-confirmed",
            "rollback-confirmed",
            "command-service-confirmed",
            "detail-entry-confirmed",
            "manage-permission-confirmed",
            "no-password-field-confirmed",
            "existing-owner-state-confirmed",
            "audit-feedback-confirmed",
            "resolver-flag-confirmed",
            "flag-off-evidence-confirmed",
            "flag-on-evidence-confirmed",
            "inactive-tenant-evidence-confirmed",
            "safe-miss-evidence-confirmed",
            "rollback-evidence-confirmed",
            "dns-tls-external-confirmed",
            "form-render-confirmed",
            "post-action-confirmed",
            "permission-denied-confirmed",
            "existing-owner-block-confirmed",
            "tests-docs-confirmed",
            "flag-off-confirmed",
            "flag-on-confirmed",
            "inactive-tenant-confirmed",
            "owner-created-confirmed",
            "unusable-password-confirmed",
            "platform-audit-confirmed",
            "tenant-audit-confirmed",
            "no-auto-login-confirmed",
            "rollback-contact-confirmed",
            "staging-evidence-confirmed",
            "dns-tls-confirmed",
            "feature-flag-confirmed",
            "rollback-owner-confirmed",
            "monitoring-window-confirmed",
            "support-comms-confirmed",
            "production-evidence-confirmed",
            "owner-access-ready-confirmed",
            "audit-trail-confirmed",
            "no-impersonation-confirmed",
            "operational-handoff-confirmed",
            "production-gate-go-confirmed",
            "flag-enabled-confirmed",
            "custom-domain-smoke-confirmed",
            "subdomain-smoke-confirmed",
            "rollback-ready-confirmed",
            "monitoring-captured-confirmed",
            "tenant-ops-closed-confirmed",
            "owner-bootstrap-closed-confirmed",
            "custom-domain-runtime-closed-confirmed",
            "remaining-risks-accepted",
            "activation-evidence-confirmed",
            "resolver-source-confirmed",
            "monitoring-confirmed",
            "support-handoff-confirmed",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")
        parser.add_argument("--environment", default="staging")
        parser.add_argument("--tenant-slug", default="")
        parser.add_argument("--custom-domain", default="")
        parser.add_argument("--owner-email", default="")
        parser.add_argument("--rollback-owner", default="")

    def handle(self, *args, **options):
        if options["review"] == "create-contract":
            payload = platform_tenant_create_contract_queries.get_review(
                platform_permission_confirmed=bool(options["platform_permission_confirmed"]),
                unique_slug_subdomain_confirmed=bool(options["unique_slug_subdomain_confirmed"]),
                reserved_subdomains_confirmed=bool(options["reserved_subdomains_confirmed"]),
                audit_platform_scope_confirmed=bool(options["audit_platform_scope_confirmed"]),
                no_bootstrap_side_effects_confirmed=bool(options["no_bootstrap_side_effects_confirmed"]),
                custom_domain_contract_only_confirmed=bool(options["custom_domain_contract_only_confirmed"]),
                rollback_manual_confirmed=bool(options["rollback_manual_confirmed"]),
            )
        elif options["review"] == "state-contract":
            payload = platform_tenant_state_contract_queries.get_review(
                platform_manage_permission_confirmed=bool(options["platform_manage_permission_confirmed"]),
                audit_platform_scope_confirmed=bool(options["audit_platform_scope_confirmed"]),
                resolver_impact_confirmed=bool(options["resolver_impact_confirmed"]),
                no_commerce_side_effects_confirmed=bool(options["no_commerce_side_effects_confirmed"]),
                manual_rollback_confirmed=bool(options["manual_rollback_confirmed"]),
                maintenance_semantics_confirmed=bool(options["maintenance_semantics_confirmed"]),
            )
        elif options["review"] == "custom-domain-contract":
            payload = platform_tenant_custom_domain_contract_queries.get_review(
                platform_manage_permission_confirmed=bool(options["platform_manage_permission_confirmed"]),
                normalization_confirmed=bool(options["normalization_confirmed"]),
                uniqueness_confirmed=bool(options["uniqueness_confirmed"]),
                audit_platform_scope_confirmed=bool(options["audit_platform_scope_confirmed"]),
                resolver_unchanged_confirmed=bool(options["resolver_unchanged_confirmed"]),
                dns_tls_out_of_scope_confirmed=bool(options["dns_tls_out_of_scope_confirmed"]),
                rollback_manual_confirmed=bool(options["rollback_manual_confirmed"]),
            )
        elif options["review"] == "ops-closure":
            payload = platform_tenant_ops_closure_queries.get_review(
                read_surface_confirmed=bool(options["read_surface_confirmed"]),
                create_surface_confirmed=bool(options["create_surface_confirmed"]),
                state_surface_confirmed=bool(options["state_surface_confirmed"]),
                custom_domain_surface_confirmed=bool(options["custom_domain_surface_confirmed"]),
                rbac_enforced_confirmed=bool(options["rbac_enforced_confirmed"]),
                audit_platform_scope_confirmed=bool(options["audit_platform_scope_confirmed"]),
                contract_only_boundaries_confirmed=bool(options["contract_only_boundaries_confirmed"]),
                docs_tests_confirmed=bool(options["docs_tests_confirmed"]),
            )
        elif options["review"] == "owner-bootstrap":
            payload = platform_tenant_owner_bootstrap_review_queries.get_review(
                tenant_manage_permission_confirmed=bool(options["tenant_manage_permission_confirmed"]),
                owner_identity_boundary_confirmed=bool(options["owner_identity_boundary_confirmed"]),
                invitation_flow_confirmed=bool(options["invitation_flow_confirmed"]),
                no_password_manual_confirmed=bool(options["no_password_manual_confirmed"]),
                audit_platform_scope_confirmed=bool(options["audit_platform_scope_confirmed"]),
                duplicate_owner_guard_confirmed=bool(options["duplicate_owner_guard_confirmed"]),
                no_commerce_side_effects_confirmed=bool(options["no_commerce_side_effects_confirmed"]),
            )
        elif options["review"] == "custom-domain-runtime":
            payload = platform_tenant_custom_domain_runtime_resolver_review_queries.get_review(
                custom_domain_unique_confirmed=bool(options["custom_domain_unique_confirmed"]),
                resolver_precedence_confirmed=bool(options["resolver_precedence_confirmed"]),
                active_tenant_guard_confirmed=bool(options["active_tenant_guard_confirmed"]),
                safe_miss_confirmed=bool(options["safe_miss_confirmed"]),
                dns_tls_out_of_scope_confirmed=bool(options["dns_tls_out_of_scope_confirmed"]),
                observability_confirmed=bool(options["observability_confirmed"]),
                rollback_confirmed=bool(options["rollback_confirmed"]),
            )
        elif options["review"] == "owner-bootstrap-admin-surface":
            payload = platform_tenant_owner_bootstrap_admin_surface_review_queries.get_review(
                command_service_confirmed=bool(options["command_service_confirmed"]),
                detail_entry_confirmed=bool(options["detail_entry_confirmed"]),
                manage_permission_confirmed=bool(options["manage_permission_confirmed"]),
                no_password_field_confirmed=bool(options["no_password_field_confirmed"]),
                existing_owner_state_confirmed=bool(options["existing_owner_state_confirmed"]),
                audit_feedback_confirmed=bool(options["audit_feedback_confirmed"]),
                no_commerce_side_effects_confirmed=bool(options["no_commerce_side_effects_confirmed"]),
            )
        elif options["review"] == "custom-domain-runtime-evidence":
            payload = platform_tenant_custom_domain_runtime_resolver_evidence_review_queries.get_review(
                resolver_flag_confirmed=bool(options["resolver_flag_confirmed"]),
                flag_off_evidence_confirmed=bool(options["flag_off_evidence_confirmed"]),
                flag_on_evidence_confirmed=bool(options["flag_on_evidence_confirmed"]),
                inactive_tenant_evidence_confirmed=bool(options["inactive_tenant_evidence_confirmed"]),
                safe_miss_evidence_confirmed=bool(options["safe_miss_evidence_confirmed"]),
                rollback_evidence_confirmed=bool(options["rollback_evidence_confirmed"]),
                dns_tls_external_confirmed=bool(options["dns_tls_external_confirmed"]),
            )
        elif options["review"] == "custom-domain-runtime-runbook":
            payload = platform_tenant_custom_domain_runtime_activation_runbook_queries.get_runbook(
                environment=options["environment"],
                tenant_slug=options["tenant_slug"],
                custom_domain=options["custom_domain"],
                rollback_owner=options["rollback_owner"],
            )
        elif options["review"] == "owner-bootstrap-admin-closure":
            payload = platform_tenant_owner_bootstrap_admin_surface_closure_queries.get_review(
                form_render_confirmed=bool(options["form_render_confirmed"]),
                post_action_confirmed=bool(options["post_action_confirmed"]),
                permission_denied_confirmed=bool(options["permission_denied_confirmed"]),
                existing_owner_block_confirmed=bool(options["existing_owner_block_confirmed"]),
                audit_platform_scope_confirmed=bool(options["audit_platform_scope_confirmed"]),
                no_password_field_confirmed=bool(options["no_password_field_confirmed"]),
                tests_docs_confirmed=bool(options["tests_docs_confirmed"]),
            )
        elif options["review"] == "custom-domain-staging-evidence":
            payload = platform_tenant_custom_domain_runtime_staging_evidence_queries.get_evidence(
                environment=options["environment"],
                tenant_slug=options["tenant_slug"],
                custom_domain=options["custom_domain"],
                flag_off_confirmed=bool(options["flag_off_confirmed"]),
                flag_on_confirmed=bool(options["flag_on_confirmed"]),
                inactive_tenant_confirmed=bool(options["inactive_tenant_confirmed"]),
                safe_miss_confirmed=bool(options["safe_miss_confirmed"]),
                rollback_confirmed=bool(options["rollback_confirmed"]),
                dns_tls_external_confirmed=bool(options["dns_tls_external_confirmed"]),
            )
        elif options["review"] == "owner-bootstrap-production-evidence":
            payload = platform_tenant_owner_bootstrap_production_evidence_queries.get_evidence(
                environment=options["environment"],
                tenant_slug=options["tenant_slug"],
                owner_email=options["owner_email"],
                owner_created_confirmed=bool(options["owner_created_confirmed"]),
                unusable_password_confirmed=bool(options["unusable_password_confirmed"]),
                platform_audit_confirmed=bool(options["platform_audit_confirmed"]),
                tenant_audit_confirmed=bool(options["tenant_audit_confirmed"]),
                no_auto_login_confirmed=bool(options["no_auto_login_confirmed"]),
                rollback_contact_confirmed=bool(options["rollback_contact_confirmed"]),
            )
        elif options["review"] == "custom-domain-production-gate":
            payload = platform_tenant_custom_domain_runtime_production_gate_queries.get_review(
                environment=options["environment"],
                tenant_slug=options["tenant_slug"],
                custom_domain=options["custom_domain"],
                staging_evidence_confirmed=bool(options["staging_evidence_confirmed"]),
                dns_tls_confirmed=bool(options["dns_tls_confirmed"]),
                feature_flag_confirmed=bool(options["feature_flag_confirmed"]),
                rollback_owner_confirmed=bool(options["rollback_owner_confirmed"]),
                monitoring_window_confirmed=bool(options["monitoring_window_confirmed"]),
                support_comms_confirmed=bool(options["support_comms_confirmed"]),
            )
        elif options["review"] == "owner-bootstrap-production-closure":
            payload = platform_tenant_owner_bootstrap_production_closure_queries.get_review(
                environment=options["environment"],
                tenant_slug=options["tenant_slug"],
                owner_email=options["owner_email"],
                production_evidence_confirmed=bool(options["production_evidence_confirmed"]),
                owner_access_ready_confirmed=bool(options["owner_access_ready_confirmed"]),
                audit_trail_confirmed=bool(options["audit_trail_confirmed"]),
                no_impersonation_confirmed=bool(options["no_impersonation_confirmed"]),
                operational_handoff_confirmed=bool(options["operational_handoff_confirmed"]),
            )
        elif options["review"] == "custom-domain-production-activation":
            payload = platform_tenant_custom_domain_runtime_production_activation_evidence_queries.get_evidence(
                environment=options["environment"],
                tenant_slug=options["tenant_slug"],
                custom_domain=options["custom_domain"],
                production_gate_go_confirmed=bool(options["production_gate_go_confirmed"]),
                flag_enabled_confirmed=bool(options["flag_enabled_confirmed"]),
                custom_domain_smoke_confirmed=bool(options["custom_domain_smoke_confirmed"]),
                subdomain_smoke_confirmed=bool(options["subdomain_smoke_confirmed"]),
                safe_miss_confirmed=bool(options["safe_miss_confirmed"]),
                rollback_ready_confirmed=bool(options["rollback_ready_confirmed"]),
                monitoring_captured_confirmed=bool(options["monitoring_captured_confirmed"]),
            )
        elif options["review"] == "store-management-track-closure":
            payload = platform_store_management_track_closure_queries.get_review(
                tenant_ops_closed_confirmed=bool(options["tenant_ops_closed_confirmed"]),
                owner_bootstrap_closed_confirmed=bool(options["owner_bootstrap_closed_confirmed"]),
                custom_domain_runtime_closed_confirmed=bool(options["custom_domain_runtime_closed_confirmed"]),
                production_evidence_confirmed=bool(options["production_evidence_confirmed"]),
                docs_tests_confirmed=bool(options["docs_tests_confirmed"]),
                remaining_risks_accepted=bool(options["remaining_risks_accepted"]),
            )
        elif options["review"] == "custom-domain-production-closure":
            payload = platform_tenant_custom_domain_runtime_production_closure_queries.get_review(
                environment=options["environment"],
                tenant_slug=options["tenant_slug"],
                custom_domain=options["custom_domain"],
                activation_evidence_confirmed=bool(options["activation_evidence_confirmed"]),
                resolver_source_confirmed=bool(options["resolver_source_confirmed"]),
                rollback_ready_confirmed=bool(options["rollback_ready_confirmed"]),
                monitoring_confirmed=bool(options["monitoring_confirmed"]),
                dns_tls_external_confirmed=bool(options["dns_tls_external_confirmed"]),
                support_handoff_confirmed=bool(options["support_handoff_confirmed"]),
            )
        else:
            payload = platform_tenant_admin_surface_queries.get_review(
                platform_owner_gate_confirmed=bool(options["platform_owner_gate_confirmed"]),
                rbac_scope_confirmed=bool(options["rbac_scope_confirmed"]),
                audit_events_confirmed=bool(options["audit_events_confirmed"]),
                custom_domain_contract_confirmed=bool(options["custom_domain_contract_confirmed"]),
                destructive_actions_deferred=bool(options["destructive_actions_deferred"]),
                tenant_isolation_confirmed=bool(options["tenant_isolation_confirmed"]),
            )
        self.stdout.write(f"[{str(payload['status']).upper()}] result={payload['result']} module={payload['module']} route={payload['route']}")
        for decision in payload["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for field in payload.get("required_fields", ()):
            self.stdout.write(f"required_field key={field['key']} summary={field['summary']}")
        for field in payload.get("optional_fields", ()):
            self.stdout.write(f"optional_field key={field['key']} summary={field['summary']}")
        for field in payload.get("fields", ()):
            self.stdout.write(f"field key={field['key']} summary={field['summary']}")
        for action in payload.get("allowed_actions", ()):
            scope = action.get("scope", "platform")
            self.stdout.write(f"allowed_action key={action['key']} scope={scope} summary={action['summary']}")
        for rule in payload.get("resolver_rules", ()):
            self.stdout.write(f"resolver_rule key={rule['key']} summary={rule['summary']}")
        for element in payload.get("surface_elements", ()):
            self.stdout.write(f"surface_element key={element['key']} summary={element['summary']}")
        for item in payload.get("evidence_items", ()):
            self.stdout.write(f"evidence_item key={item['key']} summary={item['summary']}")
        for item in payload.get("gate_items", ()):
            self.stdout.write(f"gate_item key={item['key']} summary={item['summary']}")
        for step in payload.get("steps", ()):
            self.stdout.write(f"runbook_step key={step['key']} summary={step['summary']}")
        for command in payload.get("commands", ()):
            self.stdout.write(f"runbook_command={command}")
        if payload.get("feature_flag"):
            self.stdout.write(f"feature_flag={payload['feature_flag']}")
        if payload.get("decision"):
            self.stdout.write(f"decision={payload['decision']}")
        if payload.get("environment"):
            self.stdout.write(
                f"runbook_target environment={payload['environment']} tenant_slug={payload.get('tenant_slug', '')} "
                f"custom_domain={payload.get('custom_domain', '')} rollback_owner={payload.get('rollback_owner', '')}"
            )
        if payload.get("owner_email"):
            self.stdout.write(f"owner_email={payload['owner_email']}")
        for deliverable in payload.get("deliverables", ()):
            self.stdout.write(f"deliverable key={deliverable['key']} summary={deliverable['summary']}")
        for deferred in payload.get("deferred_capabilities", ()):
            self.stdout.write(f"deferred_capability={deferred}")
        for exclusion in payload.get("excluded_actions", ()):
            self.stdout.write(f"excluded_action={exclusion}")
        for blocker in payload.get("blockers", ()):
            self.stdout.write(f"blocker={blocker}")
        for track in payload.get("next_tracks", ()):
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not payload["ready"]:
            raise CommandError("Platform tenant admin surface review is blocked.")
