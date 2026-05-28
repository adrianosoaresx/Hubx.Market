from __future__ import annotations

from dataclasses import dataclass


PLATFORM_TENANT_ADMIN_ROUTE = "/ops/platform/tenants/"

PLATFORM_TENANT_ADMIN_ACTIONS: tuple[dict[str, str], ...] = (
    {"key": "list", "scope": "platform", "summary": "listar lojas com status operacional"},
    {"key": "detail", "scope": "platform", "summary": "ver tenant, subdomínio, domínio customizado e estado"},
    {"key": "create", "scope": "platform", "summary": "criar loja com slug/subdomain únicos"},
    {"key": "activate", "scope": "platform", "summary": "ativar ou desativar tenant sem deletar dados"},
    {"key": "maintenance", "scope": "platform", "summary": "ligar ou desligar modo manutenção"},
    {"key": "custom-domain", "scope": "platform", "summary": "editar contrato de domínio customizado sem ativar resolução HTTP"},
)

PLATFORM_TENANT_ADMIN_EXCLUSIONS: tuple[str, ...] = (
    "deletar tenant",
    "editar catálogo/pedidos/pagamentos da loja",
    "impersonar owner/customer",
    "resolver custom_domain no middleware HTTP",
    "alterar plano/billing SaaS fora de subscriptions",
)

PLATFORM_TENANT_CREATE_REQUIRED_FIELDS: tuple[dict[str, str], ...] = (
    {"key": "name", "summary": "nome público/operacional da loja"},
    {"key": "slug", "summary": "identificador interno único do tenant"},
    {"key": "subdomain", "summary": "subdomínio único sob o domínio raiz"},
)

PLATFORM_TENANT_CREATE_OPTIONAL_FIELDS: tuple[dict[str, str], ...] = (
    {"key": "custom_domain", "summary": "domínio customizado contract-only"},
    {"key": "is_active", "summary": "estado inicial explícito, default ativo"},
    {"key": "maintenance_mode", "summary": "modo manutenção inicial, default desligado"},
)

PLATFORM_TENANT_CREATE_EXCLUSIONS: tuple[str, ...] = (
    "criar owner inicial automaticamente",
    "criar catálogo demo automaticamente",
    "ativar custom_domain no resolver HTTP",
    "criar assinatura/billing SaaS",
    "impersonar usuário da loja criada",
    "deletar ou sobrescrever tenant existente",
)

PLATFORM_TENANT_STATE_ACTIONS: tuple[dict[str, str], ...] = (
    {"key": "activate", "summary": "marcar tenant como ativo para resolução por subdomínio"},
    {"key": "deactivate", "summary": "marcar tenant como inativo sem deletar dados"},
    {"key": "maintenance-on", "summary": "ligar modo manutenção operacional"},
    {"key": "maintenance-off", "summary": "desligar modo manutenção operacional"},
)

PLATFORM_TENANT_STATE_EXCLUSIONS: tuple[str, ...] = (
    "deletar tenant",
    "alterar slug ou subdomain",
    "alterar custom_domain",
    "encerrar pedidos, pagamentos ou carrinhos",
    "criar redirects ou resolver HTTP novo",
    "notificar clientes automaticamente",
)

PLATFORM_TENANT_CUSTOM_DOMAIN_FIELDS: tuple[dict[str, str], ...] = (
    {"key": "custom_domain", "summary": "domínio normalizado em lowercase, sem protocolo, path ou porta"},
)

PLATFORM_TENANT_CUSTOM_DOMAIN_EXCLUSIONS: tuple[str, ...] = (
    "alterar middleware/resolver HTTP",
    "validar DNS automaticamente",
    "provisionar certificado TLS",
    "criar redirects",
    "trocar subdomain principal",
    "publicar domínio customizado como ativo",
)

PLATFORM_TENANT_OPS_DELIVERABLES: tuple[dict[str, str], ...] = (
    {"key": "inventory", "summary": "listagem platform-only de tenants"},
    {"key": "detail", "summary": "detalhe operacional do tenant"},
    {"key": "create", "summary": "criação mínima auditável de tenant"},
    {"key": "state", "summary": "ativação/desativação e manutenção auditáveis"},
    {"key": "custom-domain", "summary": "cadastro auditável de custom_domain contract-only"},
)

PLATFORM_TENANT_OPS_DEFERRED_CAPABILITIES: tuple[str, ...] = (
    "resolver custom_domain no middleware HTTP",
    "validar DNS e provisionar TLS",
    "criar owner inicial e convite no bootstrap da loja",
    "criar catálogo demo ou dados comerciais",
    "integrar plano/billing SaaS",
    "impersonar owner/customer",
    "deletar tenant",
)

PLATFORM_TENANT_OWNER_BOOTSTRAP_FIELDS: tuple[dict[str, str], ...] = (
    {"key": "owner_email", "summary": "e-mail do primeiro OwnerUser da loja"},
    {"key": "owner_name", "summary": "nome operacional opcional do responsável"},
    {"key": "owner_role", "summary": "role inicial fixa como owner/admin completo"},
)

PLATFORM_TENANT_OWNER_BOOTSTRAP_EXCLUSIONS: tuple[str, ...] = (
    "definir senha manualmente na criação",
    "logar/impersonar o owner automaticamente",
    "criar catálogo demo",
    "ativar billing SaaS",
    "recriar owner se já existir owner ativo para o tenant",
    "misturar Customer com OwnerUser",
)

PLATFORM_TENANT_CUSTOM_DOMAIN_RUNTIME_RULES: tuple[dict[str, str], ...] = (
    {"key": "exact-host-match", "summary": "resolver apenas match exato de host com custom_domain normalizado"},
    {"key": "active-tenant-only", "summary": "resolver apenas tenants ativos"},
    {"key": "subdomain-precedence", "summary": "preservar resolução por subdomínio como caminho canônico"},
    {"key": "no-dns-tls-provisioning", "summary": "não validar DNS nem provisionar TLS no resolver"},
    {"key": "safe-miss", "summary": "host sem match continua sem tenant em vez de fallback global"},
)

PLATFORM_TENANT_CUSTOM_DOMAIN_RUNTIME_EXCLUSIONS: tuple[str, ...] = (
    "provisionar DNS automaticamente",
    "emitir certificado TLS automaticamente",
    "criar redirects entre subdomínio e domínio customizado",
    "resolver domínio customizado inativo",
    "permitir wildcard custom_domain",
    "usar fallback para primeiro tenant",
)

PLATFORM_TENANT_OWNER_BOOTSTRAP_ADMIN_SURFACE_ELEMENTS: tuple[dict[str, str], ...] = (
    {"key": "detail-entry", "summary": "entrada no detalhe platform-only do tenant"},
    {"key": "owner-email", "summary": "campo de e-mail do owner inicial"},
    {"key": "owner-name", "summary": "campo opcional de nome"},
    {"key": "owner-role", "summary": "role restrita a owner/admin"},
    {"key": "existing-owner-state", "summary": "estado explícito quando já existe owner ativo"},
)

PLATFORM_TENANT_CUSTOM_DOMAIN_RUNTIME_EVIDENCE_ITEMS: tuple[dict[str, str], ...] = (
    {"key": "flag-off-smoke", "summary": "custom_domain ignorado com flag desligada"},
    {"key": "flag-on-smoke", "summary": "custom_domain resolve tenant ativo com flag ligada"},
    {"key": "inactive-tenant-smoke", "summary": "tenant inativo não resolve custom_domain"},
    {"key": "safe-miss-smoke", "summary": "host desconhecido não cai em fallback global"},
    {"key": "rollback", "summary": "desligar flag reverte para comportamento contract-only"},
)

PLATFORM_TENANT_CUSTOM_DOMAIN_RUNTIME_RUNBOOK_STEPS: tuple[dict[str, str], ...] = (
    {"key": "preflight", "summary": "confirmar tenant ativo, custom_domain único e ALLOWED_HOSTS do domínio"},
    {"key": "flag-off-smoke", "summary": "testar host customizado com flag desligada e esperar sem tenant"},
    {"key": "flag-on-smoke", "summary": "ligar HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED e testar resolução"},
    {"key": "inactive-smoke", "summary": "confirmar que tenant inativo não resolve custom_domain"},
    {"key": "safe-miss-smoke", "summary": "confirmar host desconhecido sem fallback global"},
    {"key": "rollback", "summary": "desligar flag e confirmar retorno ao comportamento contract-only"},
)

PLATFORM_TENANT_CUSTOM_DOMAIN_RUNTIME_RUNBOOK_COMMANDS: tuple[str, ...] = (
    "python manage.py test backend.app.modules.tenants.tests.test_tenant_and_middleware",
    "python manage.py check",
    "set HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED=True",
)

PLATFORM_TENANT_OWNER_BOOTSTRAP_CLOSURE_ITEMS: tuple[dict[str, str], ...] = (
    {"key": "detail-form", "summary": "form exibido no detalhe quando não há owner ativo"},
    {"key": "blocked-state", "summary": "estado bloqueado exibido quando já existe owner ativo"},
    {"key": "post-action", "summary": "POST delegado ao command service"},
    {"key": "audit", "summary": "AuditLog platform-scope obrigatório preservado"},
    {"key": "no-password", "summary": "nenhum campo de senha na UI"},
)

PLATFORM_TENANT_CUSTOM_DOMAIN_STAGING_EVIDENCE_ITEMS: tuple[dict[str, str], ...] = (
    {"key": "staging-target", "summary": "tenant/domínio alvo definidos para staging"},
    {"key": "flag-off-result", "summary": "flag desligada mantém custom_domain sem resolução"},
    {"key": "flag-on-result", "summary": "flag ligada resolve custom_domain para tenant ativo"},
    {"key": "inactive-result", "summary": "tenant inativo não resolve custom_domain"},
    {"key": "safe-miss-result", "summary": "host sem match não usa fallback global"},
    {"key": "rollback-result", "summary": "rollback por flag off confirmado"},
)

PLATFORM_TENANT_OWNER_BOOTSTRAP_PRODUCTION_EVIDENCE_ITEMS: tuple[dict[str, str], ...] = (
    {"key": "target-tenant", "summary": "tenant produtivo alvo identificado"},
    {"key": "owner-created", "summary": "OwnerUser inicial criado/confirmado"},
    {"key": "unusable-password", "summary": "User Django sem senha manual utilizável"},
    {"key": "platform-audit", "summary": "AuditLog platform-scope gravado"},
    {"key": "tenant-audit", "summary": "AuditLog tenant-scoped de accounts gravado"},
    {"key": "login-not-automatic", "summary": "sem sessão automática ou impersonação"},
)

PLATFORM_TENANT_CUSTOM_DOMAIN_PRODUCTION_GATE_ITEMS: tuple[dict[str, str], ...] = (
    {"key": "staging-evidence", "summary": "evidência staging completa"},
    {"key": "tenant-target", "summary": "tenant/domínio produtivo alvo definidos"},
    {"key": "dns-tls-external", "summary": "DNS/TLS confirmados fora do app"},
    {"key": "feature-flag", "summary": "flag de ativação/rollback definida"},
    {"key": "rollback-owner", "summary": "responsável por rollback definido"},
    {"key": "monitoring-window", "summary": "janela de observação pós-ativação definida"},
)

PLATFORM_TENANT_OWNER_BOOTSTRAP_PRODUCTION_CLOSURE_ITEMS: tuple[dict[str, str], ...] = (
    {"key": "production-evidence", "summary": "evidência produtiva completa"},
    {"key": "owner-access", "summary": "owner inicial pronto para fluxo de acesso sem senha manual"},
    {"key": "audit-trail", "summary": "trilha auditável platform e tenant-scoped preservada"},
    {"key": "no-impersonation", "summary": "sem sessão automática ou impersonação"},
    {"key": "handoff", "summary": "handoff operacional documentado"},
)

PLATFORM_TENANT_CUSTOM_DOMAIN_PRODUCTION_ACTIVATION_ITEMS: tuple[dict[str, str], ...] = (
    {"key": "production-gate", "summary": "gate produtivo retornou GO"},
    {"key": "flag-enabled", "summary": "feature flag habilitada no ambiente alvo"},
    {"key": "custom-domain-smoke", "summary": "custom_domain resolve tenant ativo"},
    {"key": "subdomain-smoke", "summary": "subdomínio canônico segue resolvendo"},
    {"key": "safe-miss-smoke", "summary": "host desconhecido permanece sem fallback"},
    {"key": "rollback-ready", "summary": "rollback por flag off confirmado"},
    {"key": "monitoring-captured", "summary": "janela pós-ativação capturada"},
)

PLATFORM_STORE_MANAGEMENT_TRACK_CLOSURE_ITEMS: tuple[dict[str, str], ...] = (
    {"key": "tenant-ops", "summary": "surface platform de tenants fechada"},
    {"key": "owner-bootstrap", "summary": "bootstrap de owner fechado até produção"},
    {"key": "custom-domain-contract", "summary": "cadastro de custom_domain auditável entregue"},
    {"key": "custom-domain-runtime", "summary": "resolver runtime com flag e evidências produtivas"},
    {"key": "docs-tests", "summary": "documentação e testes atualizados"},
)

PLATFORM_TENANT_CUSTOM_DOMAIN_PRODUCTION_CLOSURE_ITEMS: tuple[dict[str, str], ...] = (
    {"key": "activation-evidence", "summary": "evidência produtiva de ativação capturada"},
    {"key": "resolver-source", "summary": "tenant_resolution_source validado para custom_domain"},
    {"key": "rollback-ready", "summary": "rollback por flag off pronto"},
    {"key": "monitoring", "summary": "monitoramento pós-ativação capturado"},
    {"key": "no-dns-tls-runtime", "summary": "DNS/TLS seguem externos ao app"},
)


@dataclass(frozen=True)
class PlatformTenantAdminDecision:
    key: str
    status: str
    summary: str


def _blockers(prefix: str, signals: dict[str, bool]) -> tuple[str, ...]:
    return tuple(f"{prefix}:{key}:missing" for key, value in signals.items() if not value)


@dataclass
class PlatformTenantAdminSurfaceQueryService:
    def get_review(
        self,
        *,
        platform_owner_gate_confirmed: bool = False,
        rbac_scope_confirmed: bool = False,
        audit_events_confirmed: bool = False,
        custom_domain_contract_confirmed: bool = False,
        destructive_actions_deferred: bool = False,
        tenant_isolation_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "platform_owner_gate_confirmed": bool(platform_owner_gate_confirmed),
            "rbac_scope_confirmed": bool(rbac_scope_confirmed),
            "audit_events_confirmed": bool(audit_events_confirmed),
            "custom_domain_contract_confirmed": bool(custom_domain_contract_confirmed),
            "destructive_actions_deferred": bool(destructive_actions_deferred),
            "tenant_isolation_confirmed": bool(tenant_isolation_confirmed),
        }
        blockers = _blockers("platform-tenant-admin-surface", signals)
        ready = not blockers
        status = "ready" if ready else "blocked"
        return {
            "result": f"platform-tenant-admin-surface-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": PLATFORM_TENANT_ADMIN_ROUTE,
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("route", "selected", PLATFORM_TENANT_ADMIN_ROUTE),
                PlatformTenantAdminDecision("surface", "platform-only", "não pertence ao admin tenant-scoped da loja"),
                PlatformTenantAdminDecision("custom-domain", "contract-only", "edição não ativa resolução HTTP"),
                PlatformTenantAdminDecision("delete", "deferred", "tenant não deve ser deletado pela surface inicial"),
            ),
            "allowed_actions": PLATFORM_TENANT_ADMIN_ACTIONS,
            "excluded_actions": PLATFORM_TENANT_ADMIN_EXCLUSIONS,
            "blockers": blockers,
            "next_tracks": (
                "Platform Store Management — Tenant Admin Read-Only Surface Execution",
            )
            if ready
            else (
                "Platform Store Management — Tenant Admin Contract Hardening",
            ),
        }


@dataclass
class PlatformTenantCreateContractQueryService:
    def get_review(
        self,
        *,
        platform_permission_confirmed: bool = False,
        unique_slug_subdomain_confirmed: bool = False,
        reserved_subdomains_confirmed: bool = False,
        audit_platform_scope_confirmed: bool = False,
        no_bootstrap_side_effects_confirmed: bool = False,
        custom_domain_contract_only_confirmed: bool = False,
        rollback_manual_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "platform_permission_confirmed": bool(platform_permission_confirmed),
            "unique_slug_subdomain_confirmed": bool(unique_slug_subdomain_confirmed),
            "reserved_subdomains_confirmed": bool(reserved_subdomains_confirmed),
            "audit_platform_scope_confirmed": bool(audit_platform_scope_confirmed),
            "no_bootstrap_side_effects_confirmed": bool(no_bootstrap_side_effects_confirmed),
            "custom_domain_contract_only_confirmed": bool(custom_domain_contract_only_confirmed),
            "rollback_manual_confirmed": bool(rollback_manual_confirmed),
        }
        blockers = _blockers("platform-tenant-create-contract", signals)
        ready = not blockers
        status = "ready" if ready else "blocked"
        return {
            "result": f"platform-tenant-create-contract-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": f"{PLATFORM_TENANT_ADMIN_ROUTE}new/",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("write-scope", "platform-only", "criação de tenant é operação de plataforma"),
                PlatformTenantAdminDecision("required-fields", "minimal", "name, slug e subdomain são obrigatórios"),
                PlatformTenantAdminDecision("audit", "required", "write deve registrar AuditLog platform-scope explícito"),
                PlatformTenantAdminDecision("bootstrap", "deferred", "owner, catálogo demo e billing ficam fora do create inicial"),
                PlatformTenantAdminDecision("custom-domain", "contract-only", "custom_domain não altera resolução HTTP"),
            ),
            "required_fields": PLATFORM_TENANT_CREATE_REQUIRED_FIELDS,
            "optional_fields": PLATFORM_TENANT_CREATE_OPTIONAL_FIELDS,
            "excluded_actions": PLATFORM_TENANT_CREATE_EXCLUSIONS,
            "blockers": blockers,
            "next_tracks": (
                "Platform Store Management — Tenant Create Command Execution",
            )
            if ready
            else (
                "Platform Store Management — Tenant Create Contract Hardening",
            ),
        }


@dataclass
class PlatformTenantStateManagementContractQueryService:
    def get_review(
        self,
        *,
        platform_manage_permission_confirmed: bool = False,
        audit_platform_scope_confirmed: bool = False,
        resolver_impact_confirmed: bool = False,
        no_commerce_side_effects_confirmed: bool = False,
        manual_rollback_confirmed: bool = False,
        maintenance_semantics_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "platform_manage_permission_confirmed": bool(platform_manage_permission_confirmed),
            "audit_platform_scope_confirmed": bool(audit_platform_scope_confirmed),
            "resolver_impact_confirmed": bool(resolver_impact_confirmed),
            "no_commerce_side_effects_confirmed": bool(no_commerce_side_effects_confirmed),
            "manual_rollback_confirmed": bool(manual_rollback_confirmed),
            "maintenance_semantics_confirmed": bool(maintenance_semantics_confirmed),
        }
        blockers = _blockers("platform-tenant-state-contract", signals)
        ready = not blockers
        status = "ready" if ready else "blocked"
        return {
            "result": f"platform-tenant-state-contract-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/state/",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("permission", "manage", "mudança de estado exige platform.tenants.manage"),
                PlatformTenantAdminDecision("audit", "required", "toda mudança de estado registra AuditLog platform-scope"),
                PlatformTenantAdminDecision("activation", "resolver-impact", "is_active afeta resolução por subdomínio"),
                PlatformTenantAdminDecision("maintenance", "operational-flag", "maintenance_mode é estado operacional, não deleção"),
                PlatformTenantAdminDecision("side-effects", "none", "não toca commerce, owners, billing ou notificações"),
            ),
            "allowed_actions": PLATFORM_TENANT_STATE_ACTIONS,
            "excluded_actions": PLATFORM_TENANT_STATE_EXCLUSIONS,
            "blockers": blockers,
            "next_tracks": (
                "Platform Store Management — Tenant State Command Execution",
            )
            if ready
            else (
                "Platform Store Management — Tenant State Contract Hardening",
            ),
        }


@dataclass
class PlatformTenantCustomDomainContractQueryService:
    def get_review(
        self,
        *,
        platform_manage_permission_confirmed: bool = False,
        normalization_confirmed: bool = False,
        uniqueness_confirmed: bool = False,
        audit_platform_scope_confirmed: bool = False,
        resolver_unchanged_confirmed: bool = False,
        dns_tls_out_of_scope_confirmed: bool = False,
        rollback_manual_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "platform_manage_permission_confirmed": bool(platform_manage_permission_confirmed),
            "normalization_confirmed": bool(normalization_confirmed),
            "uniqueness_confirmed": bool(uniqueness_confirmed),
            "audit_platform_scope_confirmed": bool(audit_platform_scope_confirmed),
            "resolver_unchanged_confirmed": bool(resolver_unchanged_confirmed),
            "dns_tls_out_of_scope_confirmed": bool(dns_tls_out_of_scope_confirmed),
            "rollback_manual_confirmed": bool(rollback_manual_confirmed),
        }
        blockers = _blockers("platform-tenant-custom-domain-contract", signals)
        ready = not blockers
        status = "ready" if ready else "blocked"
        return {
            "result": f"platform-tenant-custom-domain-contract-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/custom-domain/",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("permission", "manage", "edição exige platform.tenants.manage"),
                PlatformTenantAdminDecision("runtime", "contract-only", "edição não altera resolver HTTP"),
                PlatformTenantAdminDecision("normalization", "required", "domínio deve ser normalizado antes de persistir"),
                PlatformTenantAdminDecision("uniqueness", "required", "custom_domain deve ser único entre tenants"),
                PlatformTenantAdminDecision("audit", "required", "mudança registra AuditLog platform-scope"),
            ),
            "fields": PLATFORM_TENANT_CUSTOM_DOMAIN_FIELDS,
            "excluded_actions": PLATFORM_TENANT_CUSTOM_DOMAIN_EXCLUSIONS,
            "blockers": blockers,
            "next_tracks": (
                "Platform Store Management — Custom Domain Command Execution",
            )
            if ready
            else (
                "Platform Store Management — Custom Domain Contract Hardening",
            ),
        }


@dataclass
class PlatformTenantOpsClosureQueryService:
    def get_review(
        self,
        *,
        read_surface_confirmed: bool = False,
        create_surface_confirmed: bool = False,
        state_surface_confirmed: bool = False,
        custom_domain_surface_confirmed: bool = False,
        rbac_enforced_confirmed: bool = False,
        audit_platform_scope_confirmed: bool = False,
        contract_only_boundaries_confirmed: bool = False,
        docs_tests_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "read_surface_confirmed": bool(read_surface_confirmed),
            "create_surface_confirmed": bool(create_surface_confirmed),
            "state_surface_confirmed": bool(state_surface_confirmed),
            "custom_domain_surface_confirmed": bool(custom_domain_surface_confirmed),
            "rbac_enforced_confirmed": bool(rbac_enforced_confirmed),
            "audit_platform_scope_confirmed": bool(audit_platform_scope_confirmed),
            "contract_only_boundaries_confirmed": bool(contract_only_boundaries_confirmed),
            "docs_tests_confirmed": bool(docs_tests_confirmed),
        }
        blockers = _blockers("platform-tenant-ops-closure", signals)
        ready = not blockers
        status = "closed" if ready else "blocked"
        return {
            "result": f"platform-tenant-ops-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": PLATFORM_TENANT_ADMIN_ROUTE,
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("scope", "closed", "surface inicial cobre inventário, detalhe, create, state e custom_domain"),
                PlatformTenantAdminDecision("rbac", "required", "writes exigem platform.tenants.manage"),
                PlatformTenantAdminDecision("audit", "required", "writes registram AuditLog platform-scope"),
                PlatformTenantAdminDecision("custom-domain", "deferred-runtime", "cadastro existe, resolver/DNS/TLS seguem fora do recorte"),
                PlatformTenantAdminDecision("delete", "deferred", "tenant deletion permanece fora da surface inicial"),
            ),
            "deliverables": PLATFORM_TENANT_OPS_DELIVERABLES,
            "deferred_capabilities": PLATFORM_TENANT_OPS_DEFERRED_CAPABILITIES,
            "blockers": blockers,
            "next_tracks": (
                "Platform Store Management — Owner Bootstrap Review",
                "Platform Store Management — Custom Domain Runtime Resolver Review",
            )
            if ready
            else (
                "Platform Store Management — Tenant Ops Closure Hardening",
            ),
        }


@dataclass
class PlatformTenantOwnerBootstrapReviewQueryService:
    def get_review(
        self,
        *,
        tenant_manage_permission_confirmed: bool = False,
        owner_identity_boundary_confirmed: bool = False,
        invitation_flow_confirmed: bool = False,
        no_password_manual_confirmed: bool = False,
        audit_platform_scope_confirmed: bool = False,
        duplicate_owner_guard_confirmed: bool = False,
        no_commerce_side_effects_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "tenant_manage_permission_confirmed": bool(tenant_manage_permission_confirmed),
            "owner_identity_boundary_confirmed": bool(owner_identity_boundary_confirmed),
            "invitation_flow_confirmed": bool(invitation_flow_confirmed),
            "no_password_manual_confirmed": bool(no_password_manual_confirmed),
            "audit_platform_scope_confirmed": bool(audit_platform_scope_confirmed),
            "duplicate_owner_guard_confirmed": bool(duplicate_owner_guard_confirmed),
            "no_commerce_side_effects_confirmed": bool(no_commerce_side_effects_confirmed),
        }
        blockers = _blockers("platform-tenant-owner-bootstrap", signals)
        ready = not blockers
        status = "ready" if ready else "blocked"
        return {
            "result": f"platform-tenant-owner-bootstrap-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/owner-bootstrap/",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("boundary", "accounts-through-tenants", "tenants orquestra o bootstrap e accounts persiste OwnerUser"),
                PlatformTenantAdminDecision("identity", "owner-user", "OwnerUser é separado de Customer"),
                PlatformTenantAdminDecision("password", "invitation-only", "sem senha manual no cadastro platform"),
                PlatformTenantAdminDecision("audit", "required", "bootstrap deve registrar AuditLog platform-scope"),
                PlatformTenantAdminDecision("idempotency", "guarded", "não cria segundo owner inicial se já existir owner ativo"),
            ),
            "fields": PLATFORM_TENANT_OWNER_BOOTSTRAP_FIELDS,
            "excluded_actions": PLATFORM_TENANT_OWNER_BOOTSTRAP_EXCLUSIONS,
            "blockers": blockers,
            "next_tracks": (
                "Platform Store Management — Owner Bootstrap Command Execution",
            )
            if ready
            else (
                "Platform Store Management — Owner Bootstrap Contract Hardening",
            ),
        }


@dataclass
class PlatformTenantCustomDomainRuntimeResolverReviewQueryService:
    def get_review(
        self,
        *,
        custom_domain_unique_confirmed: bool = False,
        resolver_precedence_confirmed: bool = False,
        active_tenant_guard_confirmed: bool = False,
        safe_miss_confirmed: bool = False,
        dns_tls_out_of_scope_confirmed: bool = False,
        observability_confirmed: bool = False,
        rollback_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "custom_domain_unique_confirmed": bool(custom_domain_unique_confirmed),
            "resolver_precedence_confirmed": bool(resolver_precedence_confirmed),
            "active_tenant_guard_confirmed": bool(active_tenant_guard_confirmed),
            "safe_miss_confirmed": bool(safe_miss_confirmed),
            "dns_tls_out_of_scope_confirmed": bool(dns_tls_out_of_scope_confirmed),
            "observability_confirmed": bool(observability_confirmed),
            "rollback_confirmed": bool(rollback_confirmed),
        }
        blockers = _blockers("platform-tenant-custom-domain-runtime", signals)
        ready = not blockers
        status = "ready" if ready else "blocked"
        return {
            "result": f"platform-tenant-custom-domain-runtime-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": "TenantResolutionMiddleware",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("runtime", "resolver-enabled-by-code", "middleware pode consultar custom_domain em wave própria"),
                PlatformTenantAdminDecision("precedence", "subdomain-first", "subdomínio segue como caminho canônico e compatível"),
                PlatformTenantAdminDecision("match", "exact-host-only", "sem wildcard e sem fallback global"),
                PlatformTenantAdminDecision("dns-tls", "external", "DNS/TLS são evidência operacional externa"),
                PlatformTenantAdminDecision("rollback", "feature-gated", "resolver deve poder ser desligado por setting/flag"),
            ),
            "resolver_rules": PLATFORM_TENANT_CUSTOM_DOMAIN_RUNTIME_RULES,
            "excluded_actions": PLATFORM_TENANT_CUSTOM_DOMAIN_RUNTIME_EXCLUSIONS,
            "blockers": blockers,
            "next_tracks": (
                "Platform Store Management — Custom Domain Runtime Resolver Execution",
            )
            if ready
            else (
                "Platform Store Management — Custom Domain Runtime Resolver Hardening",
            ),
        }


@dataclass
class PlatformTenantOwnerBootstrapAdminSurfaceReviewQueryService:
    def get_review(
        self,
        *,
        command_service_confirmed: bool = False,
        detail_entry_confirmed: bool = False,
        manage_permission_confirmed: bool = False,
        no_password_field_confirmed: bool = False,
        existing_owner_state_confirmed: bool = False,
        audit_feedback_confirmed: bool = False,
        no_commerce_side_effects_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "command_service_confirmed": bool(command_service_confirmed),
            "detail_entry_confirmed": bool(detail_entry_confirmed),
            "manage_permission_confirmed": bool(manage_permission_confirmed),
            "no_password_field_confirmed": bool(no_password_field_confirmed),
            "existing_owner_state_confirmed": bool(existing_owner_state_confirmed),
            "audit_feedback_confirmed": bool(audit_feedback_confirmed),
            "no_commerce_side_effects_confirmed": bool(no_commerce_side_effects_confirmed),
        }
        blockers = _blockers("platform-tenant-owner-bootstrap-admin-surface", signals)
        ready = not blockers
        status = "ready" if ready else "blocked"
        return {
            "result": f"platform-tenant-owner-bootstrap-admin-surface-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/owner-bootstrap/",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("surface", "detail-action", "bootstrap deve aparecer no detalhe platform-only do tenant"),
                PlatformTenantAdminDecision("permission", "manage", "POST exige platform.tenants.manage"),
                PlatformTenantAdminDecision("password", "not-collected", "UI não coleta senha manual"),
                PlatformTenantAdminDecision("existing-owner", "explicit-state", "tenant com owner ativo mostra estado bloqueado"),
                PlatformTenantAdminDecision("side-effects", "none-commerce", "não cria catálogo, billing ou sessão"),
            ),
            "surface_elements": PLATFORM_TENANT_OWNER_BOOTSTRAP_ADMIN_SURFACE_ELEMENTS,
            "blockers": blockers,
            "next_tracks": (
                "Platform Store Management — Owner Bootstrap Admin Surface Execution",
            )
            if ready
            else (
                "Platform Store Management — Owner Bootstrap Admin Surface Hardening",
            ),
        }


@dataclass
class PlatformTenantCustomDomainRuntimeResolverEvidenceReviewQueryService:
    def get_review(
        self,
        *,
        resolver_flag_confirmed: bool = False,
        flag_off_evidence_confirmed: bool = False,
        flag_on_evidence_confirmed: bool = False,
        inactive_tenant_evidence_confirmed: bool = False,
        safe_miss_evidence_confirmed: bool = False,
        rollback_evidence_confirmed: bool = False,
        dns_tls_external_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "resolver_flag_confirmed": bool(resolver_flag_confirmed),
            "flag_off_evidence_confirmed": bool(flag_off_evidence_confirmed),
            "flag_on_evidence_confirmed": bool(flag_on_evidence_confirmed),
            "inactive_tenant_evidence_confirmed": bool(inactive_tenant_evidence_confirmed),
            "safe_miss_evidence_confirmed": bool(safe_miss_evidence_confirmed),
            "rollback_evidence_confirmed": bool(rollback_evidence_confirmed),
            "dns_tls_external_confirmed": bool(dns_tls_external_confirmed),
        }
        blockers = _blockers("platform-tenant-custom-domain-runtime-evidence", signals)
        ready = not blockers
        status = "ready" if ready else "blocked"
        return {
            "result": f"platform-tenant-custom-domain-runtime-evidence-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": "TenantResolutionMiddleware",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("evidence", "required", "ativação runtime exige pacote de smoke/rollback"),
                PlatformTenantAdminDecision("flag", "rollback", "flag é o mecanismo de rollback imediato"),
                PlatformTenantAdminDecision("safe-miss", "required", "host desconhecido deve continuar sem tenant"),
                PlatformTenantAdminDecision("inactive", "blocked", "tenant inativo não resolve custom_domain"),
                PlatformTenantAdminDecision("dns-tls", "external", "DNS/TLS continuam evidência fora do app"),
            ),
            "evidence_items": PLATFORM_TENANT_CUSTOM_DOMAIN_RUNTIME_EVIDENCE_ITEMS,
            "blockers": blockers,
            "next_tracks": (
                "Platform Store Management — Custom Domain Runtime Resolver Activation Runbook",
            )
            if ready
            else (
                "Platform Store Management — Custom Domain Runtime Evidence Hardening",
            ),
        }


@dataclass
class PlatformTenantCustomDomainRuntimeActivationRunbookQueryService:
    def get_runbook(
        self,
        *,
        environment: object = "staging",
        tenant_slug: object = "",
        custom_domain: object = "",
        rollback_owner: object = "",
    ) -> dict[str, object]:
        normalized_environment = str(environment or "staging").strip().lower()[:40]
        normalized_tenant_slug = str(tenant_slug or "").strip()[:150]
        normalized_custom_domain = str(custom_domain or "").strip().lower()[:255]
        normalized_rollback_owner = str(rollback_owner or "").strip()[:180]
        blockers = []
        if not normalized_environment:
            blockers.append("platform-tenant-custom-domain-runtime-runbook:environment:missing")
        if not normalized_tenant_slug:
            blockers.append("platform-tenant-custom-domain-runtime-runbook:tenant_slug:missing")
        if not normalized_custom_domain:
            blockers.append("platform-tenant-custom-domain-runtime-runbook:custom_domain:missing")
        ready = not blockers
        return {
            "result": "platform-tenant-custom-domain-runtime-runbook-ready" if ready else "platform-tenant-custom-domain-runtime-runbook-blocked",
            "ready": ready,
            "status": "ready" if ready else "blocked",
            "module": "tenants",
            "route": "TenantResolutionMiddleware",
            "environment": normalized_environment,
            "tenant_slug": normalized_tenant_slug,
            "custom_domain": normalized_custom_domain,
            "rollback_owner": normalized_rollback_owner or "platform/on-call",
            "feature_flag": "HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED",
            "decisions": (
                PlatformTenantAdminDecision("activation", "manual", "runbook não altera ambiente automaticamente"),
                PlatformTenantAdminDecision("flag", "required", "ativação depende de HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED"),
                PlatformTenantAdminDecision("rollback", "flag-off", "rollback imediato é desligar a flag"),
                PlatformTenantAdminDecision("dns-tls", "external", "DNS/TLS permanecem evidência externa"),
            ),
            "steps": PLATFORM_TENANT_CUSTOM_DOMAIN_RUNTIME_RUNBOOK_STEPS,
            "commands": PLATFORM_TENANT_CUSTOM_DOMAIN_RUNTIME_RUNBOOK_COMMANDS,
            "blockers": tuple(blockers),
            "next_tracks": (
                "Platform Store Management — Custom Domain Runtime Staging Activation Evidence",
            )
            if ready
            else (
                "Platform Store Management — Custom Domain Runtime Runbook Hardening",
            ),
        }


@dataclass
class PlatformTenantOwnerBootstrapAdminSurfaceClosureQueryService:
    def get_review(
        self,
        *,
        form_render_confirmed: bool = False,
        post_action_confirmed: bool = False,
        permission_denied_confirmed: bool = False,
        existing_owner_block_confirmed: bool = False,
        audit_platform_scope_confirmed: bool = False,
        no_password_field_confirmed: bool = False,
        tests_docs_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "form_render_confirmed": bool(form_render_confirmed),
            "post_action_confirmed": bool(post_action_confirmed),
            "permission_denied_confirmed": bool(permission_denied_confirmed),
            "existing_owner_block_confirmed": bool(existing_owner_block_confirmed),
            "audit_platform_scope_confirmed": bool(audit_platform_scope_confirmed),
            "no_password_field_confirmed": bool(no_password_field_confirmed),
            "tests_docs_confirmed": bool(tests_docs_confirmed),
        }
        blockers = _blockers("platform-tenant-owner-bootstrap-admin-closure", signals)
        ready = not blockers
        status = "closed" if ready else "blocked"
        return {
            "result": f"platform-tenant-owner-bootstrap-admin-surface-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/owner-bootstrap/",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("surface", "closed", "bootstrap inicial está exposto no detalhe platform-only"),
                PlatformTenantAdminDecision("password", "not-collected", "UI não coleta senha manual"),
                PlatformTenantAdminDecision("audit", "preserved", "command service preserva AuditLog platform-scope"),
                PlatformTenantAdminDecision("boundary", "accounts-owned", "OwnerUser/User continuam em accounts"),
                PlatformTenantAdminDecision("scope", "no-commerce", "sem side effects em catálogo, billing ou sessão"),
            ),
            "deliverables": PLATFORM_TENANT_OWNER_BOOTSTRAP_CLOSURE_ITEMS,
            "blockers": blockers,
            "next_tracks": (
                "Platform Store Management — Owner Bootstrap Production Evidence",
            )
            if ready
            else (
                "Platform Store Management — Owner Bootstrap Admin Surface Hardening",
            ),
        }


@dataclass
class PlatformTenantCustomDomainRuntimeStagingEvidenceQueryService:
    def get_evidence(
        self,
        *,
        environment: object = "staging",
        tenant_slug: object = "",
        custom_domain: object = "",
        flag_off_confirmed: bool = False,
        flag_on_confirmed: bool = False,
        inactive_tenant_confirmed: bool = False,
        safe_miss_confirmed: bool = False,
        rollback_confirmed: bool = False,
        dns_tls_external_confirmed: bool = False,
    ) -> dict[str, object]:
        normalized_environment = str(environment or "staging").strip().lower()[:40]
        normalized_tenant_slug = str(tenant_slug or "").strip()[:150]
        normalized_custom_domain = str(custom_domain or "").strip().lower()[:255]
        signals = {
            "flag_off_confirmed": bool(flag_off_confirmed),
            "flag_on_confirmed": bool(flag_on_confirmed),
            "inactive_tenant_confirmed": bool(inactive_tenant_confirmed),
            "safe_miss_confirmed": bool(safe_miss_confirmed),
            "rollback_confirmed": bool(rollback_confirmed),
            "dns_tls_external_confirmed": bool(dns_tls_external_confirmed),
        }
        blockers = list(_blockers("platform-tenant-custom-domain-staging-evidence", signals))
        if not normalized_environment:
            blockers.append("platform-tenant-custom-domain-staging-evidence:environment:missing")
        if not normalized_tenant_slug:
            blockers.append("platform-tenant-custom-domain-staging-evidence:tenant_slug:missing")
        if not normalized_custom_domain:
            blockers.append("platform-tenant-custom-domain-staging-evidence:custom_domain:missing")
        ready = not blockers
        return {
            "result": "platform-tenant-custom-domain-staging-evidence-ready" if ready else "platform-tenant-custom-domain-staging-evidence-blocked",
            "ready": ready,
            "status": "ready" if ready else "blocked",
            "module": "tenants",
            "route": "TenantResolutionMiddleware",
            "environment": normalized_environment,
            "tenant_slug": normalized_tenant_slug,
            "custom_domain": normalized_custom_domain,
            "feature_flag": "HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("environment", "staging", "evidência limitada ao ambiente informado"),
                PlatformTenantAdminDecision("flag-off", "confirmed", "comportamento contract-only deve ser provado"),
                PlatformTenantAdminDecision("flag-on", "confirmed", "resolução custom_domain deve ser provada"),
                PlatformTenantAdminDecision("rollback", "confirmed", "rollback por flag off deve ser provado"),
                PlatformTenantAdminDecision("dns-tls", "external", "DNS/TLS seguem fora do app"),
            ),
            "evidence_items": PLATFORM_TENANT_CUSTOM_DOMAIN_STAGING_EVIDENCE_ITEMS,
            "blockers": tuple(blockers),
            "next_tracks": (
                "Platform Store Management — Custom Domain Runtime Production Gate Review",
            )
            if ready
            else (
                "Platform Store Management — Custom Domain Runtime Staging Evidence Hardening",
            ),
        }


@dataclass
class PlatformTenantOwnerBootstrapProductionEvidenceQueryService:
    def get_evidence(
        self,
        *,
        environment: object = "production",
        tenant_slug: object = "",
        owner_email: object = "",
        owner_created_confirmed: bool = False,
        unusable_password_confirmed: bool = False,
        platform_audit_confirmed: bool = False,
        tenant_audit_confirmed: bool = False,
        no_auto_login_confirmed: bool = False,
        rollback_contact_confirmed: bool = False,
    ) -> dict[str, object]:
        normalized_environment = str(environment or "production").strip().lower()[:40]
        normalized_tenant_slug = str(tenant_slug or "").strip()[:150]
        normalized_owner_email = str(owner_email or "").strip().lower()[:254]
        signals = {
            "owner_created_confirmed": bool(owner_created_confirmed),
            "unusable_password_confirmed": bool(unusable_password_confirmed),
            "platform_audit_confirmed": bool(platform_audit_confirmed),
            "tenant_audit_confirmed": bool(tenant_audit_confirmed),
            "no_auto_login_confirmed": bool(no_auto_login_confirmed),
            "rollback_contact_confirmed": bool(rollback_contact_confirmed),
        }
        blockers = list(_blockers("platform-tenant-owner-bootstrap-production-evidence", signals))
        if not normalized_environment:
            blockers.append("platform-tenant-owner-bootstrap-production-evidence:environment:missing")
        if not normalized_tenant_slug:
            blockers.append("platform-tenant-owner-bootstrap-production-evidence:tenant_slug:missing")
        if not normalized_owner_email:
            blockers.append("platform-tenant-owner-bootstrap-production-evidence:owner_email:missing")
        ready = not blockers
        return {
            "result": "platform-tenant-owner-bootstrap-production-evidence-ready" if ready else "platform-tenant-owner-bootstrap-production-evidence-blocked",
            "ready": ready,
            "status": "ready" if ready else "blocked",
            "module": "tenants",
            "route": f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/owner-bootstrap/",
            "environment": normalized_environment,
            "tenant_slug": normalized_tenant_slug,
            "owner_email": normalized_owner_email,
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("environment", "production", "evidência limitada ao ambiente informado"),
                PlatformTenantAdminDecision("identity", "owner-user", "OwnerUser inicial deve existir no tenant alvo"),
                PlatformTenantAdminDecision("password", "unusable", "senha manual não deve existir"),
                PlatformTenantAdminDecision("audit", "dual", "auditoria platform e tenant-scoped deve existir"),
                PlatformTenantAdminDecision("session", "none", "sem login automático ou impersonação"),
            ),
            "evidence_items": PLATFORM_TENANT_OWNER_BOOTSTRAP_PRODUCTION_EVIDENCE_ITEMS,
            "blockers": tuple(blockers),
            "next_tracks": (
                "Platform Store Management — Owner Bootstrap Production Closure",
            )
            if ready
            else (
                "Platform Store Management — Owner Bootstrap Production Evidence Hardening",
            ),
        }


@dataclass
class PlatformTenantCustomDomainRuntimeProductionGateQueryService:
    def get_review(
        self,
        *,
        environment: object = "production",
        tenant_slug: object = "",
        custom_domain: object = "",
        staging_evidence_confirmed: bool = False,
        dns_tls_confirmed: bool = False,
        feature_flag_confirmed: bool = False,
        rollback_owner_confirmed: bool = False,
        monitoring_window_confirmed: bool = False,
        support_comms_confirmed: bool = False,
    ) -> dict[str, object]:
        normalized_environment = str(environment or "production").strip().lower()[:40]
        normalized_tenant_slug = str(tenant_slug or "").strip()[:150]
        normalized_custom_domain = str(custom_domain or "").strip().lower()[:255]
        signals = {
            "staging_evidence_confirmed": bool(staging_evidence_confirmed),
            "dns_tls_confirmed": bool(dns_tls_confirmed),
            "feature_flag_confirmed": bool(feature_flag_confirmed),
            "rollback_owner_confirmed": bool(rollback_owner_confirmed),
            "monitoring_window_confirmed": bool(monitoring_window_confirmed),
            "support_comms_confirmed": bool(support_comms_confirmed),
        }
        blockers = list(_blockers("platform-tenant-custom-domain-production-gate", signals))
        if not normalized_environment:
            blockers.append("platform-tenant-custom-domain-production-gate:environment:missing")
        if not normalized_tenant_slug:
            blockers.append("platform-tenant-custom-domain-production-gate:tenant_slug:missing")
        if not normalized_custom_domain:
            blockers.append("platform-tenant-custom-domain-production-gate:custom_domain:missing")
        ready = not blockers
        decision = "GO" if ready else "NO-GO"
        return {
            "result": "platform-tenant-custom-domain-production-gate-go" if ready else "platform-tenant-custom-domain-production-gate-no-go",
            "ready": ready,
            "status": "go" if ready else "no-go",
            "decision": decision,
            "module": "tenants",
            "route": "TenantResolutionMiddleware",
            "environment": normalized_environment,
            "tenant_slug": normalized_tenant_slug,
            "custom_domain": normalized_custom_domain,
            "feature_flag": "HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("decision", decision, "gate produtivo do resolver custom_domain"),
                PlatformTenantAdminDecision("dns-tls", "external", "DNS/TLS devem estar confirmados fora do app"),
                PlatformTenantAdminDecision("flag", "required", "ativação depende da feature flag"),
                PlatformTenantAdminDecision("rollback", "required", "rollback owner deve estar definido"),
                PlatformTenantAdminDecision("monitoring", "required", "janela pós-ativação deve existir"),
            ),
            "gate_items": PLATFORM_TENANT_CUSTOM_DOMAIN_PRODUCTION_GATE_ITEMS,
            "blockers": tuple(blockers),
            "next_tracks": (
                "Platform Store Management — Custom Domain Runtime Production Activation Evidence",
            )
            if ready
            else (
                "Platform Store Management — Custom Domain Runtime Production Gate Hardening",
            ),
        }


@dataclass
class PlatformTenantOwnerBootstrapProductionClosureQueryService:
    def get_review(
        self,
        *,
        environment: object = "production",
        tenant_slug: object = "",
        owner_email: object = "",
        production_evidence_confirmed: bool = False,
        owner_access_ready_confirmed: bool = False,
        audit_trail_confirmed: bool = False,
        no_impersonation_confirmed: bool = False,
        operational_handoff_confirmed: bool = False,
    ) -> dict[str, object]:
        normalized_environment = str(environment or "production").strip().lower()[:40]
        normalized_tenant_slug = str(tenant_slug or "").strip()[:150]
        normalized_owner_email = str(owner_email or "").strip().lower()[:254]
        signals = {
            "production_evidence_confirmed": bool(production_evidence_confirmed),
            "owner_access_ready_confirmed": bool(owner_access_ready_confirmed),
            "audit_trail_confirmed": bool(audit_trail_confirmed),
            "no_impersonation_confirmed": bool(no_impersonation_confirmed),
            "operational_handoff_confirmed": bool(operational_handoff_confirmed),
        }
        blockers = list(_blockers("platform-tenant-owner-bootstrap-production-closure", signals))
        if not normalized_environment:
            blockers.append("platform-tenant-owner-bootstrap-production-closure:environment:missing")
        if not normalized_tenant_slug:
            blockers.append("platform-tenant-owner-bootstrap-production-closure:tenant_slug:missing")
        if not normalized_owner_email:
            blockers.append("platform-tenant-owner-bootstrap-production-closure:owner_email:missing")
        ready = not blockers
        status = "closed" if ready else "blocked"
        return {
            "result": f"platform-tenant-owner-bootstrap-production-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": f"{PLATFORM_TENANT_ADMIN_ROUTE}<tenant_slug>/owner-bootstrap/",
            "environment": normalized_environment,
            "tenant_slug": normalized_tenant_slug,
            "owner_email": normalized_owner_email,
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("closure", "closed" if ready else "blocked", "closure produtivo do owner bootstrap"),
                PlatformTenantAdminDecision("access", "invitation-flow", "acesso segue por fluxo sem senha manual"),
                PlatformTenantAdminDecision("audit", "preserved", "auditoria platform e tenant-scoped preservada"),
                PlatformTenantAdminDecision("session", "none", "sem login automático ou impersonação"),
                PlatformTenantAdminDecision("handoff", "required", "handoff operacional deve estar registrado"),
            ),
            "deliverables": PLATFORM_TENANT_OWNER_BOOTSTRAP_PRODUCTION_CLOSURE_ITEMS,
            "blockers": tuple(blockers),
            "next_tracks": (
                "Platform Store Management — Store Management Track Closure",
            )
            if ready
            else (
                "Platform Store Management — Owner Bootstrap Production Closure Hardening",
            ),
        }


@dataclass
class PlatformTenantCustomDomainRuntimeProductionActivationEvidenceQueryService:
    def get_evidence(
        self,
        *,
        environment: object = "production",
        tenant_slug: object = "",
        custom_domain: object = "",
        production_gate_go_confirmed: bool = False,
        flag_enabled_confirmed: bool = False,
        custom_domain_smoke_confirmed: bool = False,
        subdomain_smoke_confirmed: bool = False,
        safe_miss_confirmed: bool = False,
        rollback_ready_confirmed: bool = False,
        monitoring_captured_confirmed: bool = False,
    ) -> dict[str, object]:
        normalized_environment = str(environment or "production").strip().lower()[:40]
        normalized_tenant_slug = str(tenant_slug or "").strip()[:150]
        normalized_custom_domain = str(custom_domain or "").strip().lower()[:255]
        signals = {
            "production_gate_go_confirmed": bool(production_gate_go_confirmed),
            "flag_enabled_confirmed": bool(flag_enabled_confirmed),
            "custom_domain_smoke_confirmed": bool(custom_domain_smoke_confirmed),
            "subdomain_smoke_confirmed": bool(subdomain_smoke_confirmed),
            "safe_miss_confirmed": bool(safe_miss_confirmed),
            "rollback_ready_confirmed": bool(rollback_ready_confirmed),
            "monitoring_captured_confirmed": bool(monitoring_captured_confirmed),
        }
        blockers = list(_blockers("platform-tenant-custom-domain-production-activation", signals))
        if not normalized_environment:
            blockers.append("platform-tenant-custom-domain-production-activation:environment:missing")
        if not normalized_tenant_slug:
            blockers.append("platform-tenant-custom-domain-production-activation:tenant_slug:missing")
        if not normalized_custom_domain:
            blockers.append("platform-tenant-custom-domain-production-activation:custom_domain:missing")
        ready = not blockers
        return {
            "result": "platform-tenant-custom-domain-production-activation-evidence-ready" if ready else "platform-tenant-custom-domain-production-activation-evidence-blocked",
            "ready": ready,
            "status": "ready" if ready else "blocked",
            "module": "tenants",
            "route": "TenantResolutionMiddleware",
            "environment": normalized_environment,
            "tenant_slug": normalized_tenant_slug,
            "custom_domain": normalized_custom_domain,
            "feature_flag": "HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("activation", "evidence", "evidência pós-ativação produtiva"),
                PlatformTenantAdminDecision("gate", "go-required", "gate produtivo GO deve preceder ativação"),
                PlatformTenantAdminDecision("smoke", "required", "custom_domain, subdomain e safe miss devem ser provados"),
                PlatformTenantAdminDecision("rollback", "ready", "rollback por flag off deve estar pronto"),
                PlatformTenantAdminDecision("monitoring", "captured", "janela de monitoramento deve estar capturada"),
            ),
            "evidence_items": PLATFORM_TENANT_CUSTOM_DOMAIN_PRODUCTION_ACTIVATION_ITEMS,
            "blockers": tuple(blockers),
            "next_tracks": (
                "Platform Store Management — Custom Domain Runtime Production Closure",
            )
            if ready
            else (
                "Platform Store Management — Custom Domain Runtime Production Activation Hardening",
            ),
        }


@dataclass
class PlatformStoreManagementTrackClosureQueryService:
    def get_review(
        self,
        *,
        tenant_ops_closed_confirmed: bool = False,
        owner_bootstrap_closed_confirmed: bool = False,
        custom_domain_runtime_closed_confirmed: bool = False,
        production_evidence_confirmed: bool = False,
        docs_tests_confirmed: bool = False,
        remaining_risks_accepted: bool = False,
    ) -> dict[str, object]:
        signals = {
            "tenant_ops_closed_confirmed": bool(tenant_ops_closed_confirmed),
            "owner_bootstrap_closed_confirmed": bool(owner_bootstrap_closed_confirmed),
            "custom_domain_runtime_closed_confirmed": bool(custom_domain_runtime_closed_confirmed),
            "production_evidence_confirmed": bool(production_evidence_confirmed),
            "docs_tests_confirmed": bool(docs_tests_confirmed),
            "remaining_risks_accepted": bool(remaining_risks_accepted),
        }
        blockers = _blockers("platform-store-management-track-closure", signals)
        ready = not blockers
        status = "closed" if ready else "blocked"
        return {
            "result": f"platform-store-management-track-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": PLATFORM_TENANT_ADMIN_ROUTE,
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("track", "closed" if ready else "blocked", "closure geral da trilha Platform Store Management"),
                PlatformTenantAdminDecision("scope", "production-ready-controlled", "uso produtivo controlado, não automação irrestrita"),
                PlatformTenantAdminDecision("runtime", "feature-gated", "custom domain runtime segue controlado por flag"),
                PlatformTenantAdminDecision("boundaries", "preserved", "accounts, DNS/TLS e commerce seguem em seus módulos/fronteiras"),
                PlatformTenantAdminDecision("risks", "accepted", "riscos remanescentes devem estar explicitamente aceitos"),
            ),
            "deliverables": PLATFORM_STORE_MANAGEMENT_TRACK_CLOSURE_ITEMS,
            "blockers": blockers,
            "next_tracks": (
                "System ROI Re-Selection Review",
            )
            if ready
            else (
                "Platform Store Management — Track Closure Hardening",
            ),
        }


@dataclass
class PlatformTenantCustomDomainRuntimeProductionClosureQueryService:
    def get_review(
        self,
        *,
        environment: object = "production",
        tenant_slug: object = "",
        custom_domain: object = "",
        activation_evidence_confirmed: bool = False,
        resolver_source_confirmed: bool = False,
        rollback_ready_confirmed: bool = False,
        monitoring_confirmed: bool = False,
        dns_tls_external_confirmed: bool = False,
        support_handoff_confirmed: bool = False,
    ) -> dict[str, object]:
        normalized_environment = str(environment or "production").strip().lower()[:40]
        normalized_tenant_slug = str(tenant_slug or "").strip()[:150]
        normalized_custom_domain = str(custom_domain or "").strip().lower()[:255]
        signals = {
            "activation_evidence_confirmed": bool(activation_evidence_confirmed),
            "resolver_source_confirmed": bool(resolver_source_confirmed),
            "rollback_ready_confirmed": bool(rollback_ready_confirmed),
            "monitoring_confirmed": bool(monitoring_confirmed),
            "dns_tls_external_confirmed": bool(dns_tls_external_confirmed),
            "support_handoff_confirmed": bool(support_handoff_confirmed),
        }
        blockers = list(_blockers("platform-tenant-custom-domain-production-closure", signals))
        if not normalized_environment:
            blockers.append("platform-tenant-custom-domain-production-closure:environment:missing")
        if not normalized_tenant_slug:
            blockers.append("platform-tenant-custom-domain-production-closure:tenant_slug:missing")
        if not normalized_custom_domain:
            blockers.append("platform-tenant-custom-domain-production-closure:custom_domain:missing")
        ready = not blockers
        status = "closed" if ready else "blocked"
        return {
            "result": f"platform-tenant-custom-domain-production-{status}",
            "ready": ready,
            "status": status,
            "module": "tenants",
            "route": "TenantResolutionMiddleware",
            "environment": normalized_environment,
            "tenant_slug": normalized_tenant_slug,
            "custom_domain": normalized_custom_domain,
            "feature_flag": "HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED",
            "signals": signals,
            "decisions": (
                PlatformTenantAdminDecision("closure", "closed" if ready else "blocked", "closure produtivo do custom domain runtime"),
                PlatformTenantAdminDecision("resolver", "custom-domain-source", "origem custom_domain deve estar validada"),
                PlatformTenantAdminDecision("rollback", "flag-off", "rollback segue por flag off"),
                PlatformTenantAdminDecision("monitoring", "captured", "monitoramento pós-ativação capturado"),
                PlatformTenantAdminDecision("dns-tls", "external", "DNS/TLS permanecem fora do app"),
            ),
            "deliverables": PLATFORM_TENANT_CUSTOM_DOMAIN_PRODUCTION_CLOSURE_ITEMS,
            "blockers": tuple(blockers),
            "next_tracks": (
                "Platform Store Management — Store Management Track Closure",
            )
            if ready
            else (
                "Platform Store Management — Custom Domain Runtime Production Closure Hardening",
            ),
        }


platform_tenant_admin_surface_queries = PlatformTenantAdminSurfaceQueryService()
platform_tenant_create_contract_queries = PlatformTenantCreateContractQueryService()
platform_tenant_state_contract_queries = PlatformTenantStateManagementContractQueryService()
platform_tenant_custom_domain_contract_queries = PlatformTenantCustomDomainContractQueryService()
platform_tenant_ops_closure_queries = PlatformTenantOpsClosureQueryService()
platform_tenant_owner_bootstrap_review_queries = PlatformTenantOwnerBootstrapReviewQueryService()
platform_tenant_custom_domain_runtime_resolver_review_queries = (
    PlatformTenantCustomDomainRuntimeResolverReviewQueryService()
)
platform_tenant_owner_bootstrap_admin_surface_review_queries = (
    PlatformTenantOwnerBootstrapAdminSurfaceReviewQueryService()
)
platform_tenant_custom_domain_runtime_resolver_evidence_review_queries = (
    PlatformTenantCustomDomainRuntimeResolverEvidenceReviewQueryService()
)
platform_tenant_custom_domain_runtime_activation_runbook_queries = (
    PlatformTenantCustomDomainRuntimeActivationRunbookQueryService()
)
platform_tenant_owner_bootstrap_admin_surface_closure_queries = (
    PlatformTenantOwnerBootstrapAdminSurfaceClosureQueryService()
)
platform_tenant_custom_domain_runtime_staging_evidence_queries = (
    PlatformTenantCustomDomainRuntimeStagingEvidenceQueryService()
)
platform_tenant_owner_bootstrap_production_evidence_queries = (
    PlatformTenantOwnerBootstrapProductionEvidenceQueryService()
)
platform_tenant_custom_domain_runtime_production_gate_queries = (
    PlatformTenantCustomDomainRuntimeProductionGateQueryService()
)
platform_tenant_owner_bootstrap_production_closure_queries = (
    PlatformTenantOwnerBootstrapProductionClosureQueryService()
)
platform_tenant_custom_domain_runtime_production_activation_evidence_queries = (
    PlatformTenantCustomDomainRuntimeProductionActivationEvidenceQueryService()
)
platform_store_management_track_closure_queries = PlatformStoreManagementTrackClosureQueryService()
platform_tenant_custom_domain_runtime_production_closure_queries = (
    PlatformTenantCustomDomainRuntimeProductionClosureQueryService()
)
