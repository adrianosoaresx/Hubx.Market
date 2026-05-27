# Audit

## Responsabilidade
Registrar eventos auditáveis administrativos e operacionais relevantes.

## Entidades principais
- AuditLog

## Casos de uso
- registrar evento auditável tenant-scoped
- registrar evento platform-scope apenas quando explicitamente permitido
- listar eventos auditáveis por tenant em admin
- filtrar por módulo, ação e texto operacional

## Regras de negócio
- eventos tenant-owned exigem `tenant_id`
- eventos platform-scope exigem opt-in explícito no command
- metadados devem ser sanitizados para valores simples
- audit log não executa correções nem efeitos colaterais
- instrumentação automática por módulo deve entrar em waves específicas
- instrumentação inicial deve cobrir apenas ações administrativas sensíveis

## Interfaces

- Admin read-only: `/ops/audit/`

## Application services

- `audit_log_commands.record_event(...)`
- `admin_audit_log_queries.list_logs(...)`
- `audit_evidence_export_queries.export(...)`

## Status

Platform Production Governance Foundation:

- modelo `AuditLog`
- writer tenant-scoped
- platform-scope explícito
- admin read-only tenant-scoped
- sem hooks automáticos globais

Platform Governance Instrumentation:

- `coupons.application.admin_coupon_commands.create_coupon(...)` registra `coupon.created`
- `pages.application.admin_page_commands.create_page(...)` registra `page.created`
- `pages.application.admin_page_commands.update_page(...)` registra `page.updated`
- `reviews.application.admin_review_commands.moderate_review(...)` registra `review.approved` ou `review.rejected`
- escopo limitado a ações administrativas com impacto comercial, público ou de confiança
- fora de escopo: middleware global, log de leitura, diff genérico de models e logging técnico

Platform Governance Permissions:

- ações auditadas sensíveis agora consultam `accounts.application.admin_permissions` quando recebem `actor_role`
- eventos negados por permissão não gravam `AuditLog`, porque a ação de domínio não aconteceu
- auditoria continua registrando ações executadas, não tentativas bloqueadas genéricas

Platform Owner Access Management:

- `accounts.application.admin_owner_commands.create_owner(...)` registra `owner.created`
- `accounts.application.admin_owner_commands.update_owner_access(...)` registra `owner.access_updated`
- toggle de notificações owner-facing também registra `owner.access_updated`
- eventos usam `module=accounts` e `entity_type=OwnerUser`

## Platform Audit Evidence Export Review

- evidências de auditoria agora podem ser exportadas por comando read-only.
- comando:
  - `python manage.py export_audit_evidence --tenant-id=<tenant_id> --format=jsonl`
- formatos suportados:
  - `jsonl`;
  - `csv`.
- filtros suportados:
  - `--module`;
  - `--action`;
  - `--since`;
  - `--until`;
  - `--limit`.
- metadata só é incluída quando `--include-metadata` é usado.
- eventos platform-scope exigem `--platform-scope` explícito.

### Regras

- export tenant-owned exige `tenant_id`.
- export platform-scope nunca mistura eventos de tenant.
- saída é textual para anexar em change log, incident review ou pacote de evidência.
- o comando não grava `AuditLog`, não altera eventos e não reprocessa ações.

### Escopo deliberado

- sem endpoint HTTP de download nesta fase.
- sem assinar/criptografar artefato.
- sem upload para S3/R2.
- sem export cross-tenant agregado.
- sem redaction avançado além do metadata opt-in.

## Platform Audit Evidence Admin Surface Review

- `/ops/audit/` agora oferece ação read-only para exportar evidência JSONL do tenant resolvido.
- rota:
  - `/ops/audit/export/`
- a surface reutiliza `audit_evidence_export_queries.export(...)`.
- filtros de módulo/ação da listagem são preservados no link de exportação.
- o endpoint retorna `400` quando não há tenant resolvido.

### Regras

- a rota fica sob `/ops/audit/` e herda o gate/permissão `audit.view`.
- export HTTP não permite platform-scope.
- export HTTP não mistura tenants.
- metadata não é incluída por padrão.

### Escopo deliberado

- sem UI avançada de período/formato.
- sem export platform-scope via browser.
- sem job assíncrono de exportação.
- sem storage externo.

## Platform Audit Evidence Closure Review

- a trilha de exportação de evidências auditáveis está tecnicamente fechada nesta fase.
- comando:
  - `python manage.py audit_evidence_closure --tenant-id=<tenant_id> --fail-on-blockers`
- o closure valida:
  - export command read-only;
  - surface admin tenant-scoped;
  - riscos residuais;
  - próximas trilhas de plataforma.

### Decisão de encerramento

- `audit` é o módulo dono de exportação formal de evidências.
- command-line cobre JSONL/CSV, platform-scope explícito e filtros operacionais.
- `/ops/audit/export/` cobre o caso admin tenant-scoped mínimo.
- próxima evolução deve sair do eixo export básico.

### Próximas trilhas sugeridas

- `Platform Owner MFA/SSO Review`;
- `Platform Admin Permission Matrix Persistence Review`;
- `Platform Operations Dashboard Review`.

## Owner MFA Audit Evidence Export Review

- export de evidência MFA owner/admin agora possui review tenant-scoped antes da execution.
- query service:
  - `audit.application.owner_mfa_audit_evidence_export_review_queries`
- comando:
  - `python manage.py owner_mfa_audit_evidence_export_review --tenant-id=<tenant_id> --expected-actions-confirmed --export-scope-documented --redaction-reviewed --recipient-approved`
- a review valida:
  - export canônico via `audit_evidence_export_queries`;
  - `module=accounts`;
  - `tenant_id` obrigatório;
  - presença de ações MFA em `AuditLog`;
  - escopo, redaction e destinatário aprovados.

### Regras

- `accounts` registra eventos MFA, mas não exporta evidência formal.
- metadata permanece fora do sample por padrão.
- review não grava `AuditLog`, não consulta tabelas internas de `accounts` e não gera artefato final.
- platform-scope não faz parte deste recorte.

### Próxima trilha sugerida

- `Owner MFA Audit Evidence Export Execution`.

## Owner MFA Audit Evidence Export Execution

- export formal de evidência MFA owner/admin agora possui command tenant-scoped dedicado.
- query service:
  - `audit.application.owner_mfa_audit_evidence_export_execution_queries`
- comando:
  - `python manage.py export_owner_mfa_audit_evidence --tenant-id=<tenant_id> --expected-actions-confirmed --export-scope-documented --redaction-reviewed --recipient-approved --format=jsonl`
- a execution:
  - exige review `READY`;
  - usa `audit_evidence_export_queries` como exportador canônico;
  - filtra `module=accounts`;
  - mantém apenas ações cujo `action` contém `mfa`;
  - remove metadata da saída;
  - suporta `jsonl` e `csv`.

### Escopo deliberado

- sem platform-scope.
- sem include-metadata.
- sem assinatura, criptografia ou storage externo.
- sem consultar tabelas internas de `accounts`.
- sem registrar novo `AuditLog` durante export.

## Owner MFA Audit Evidence Export Closure Review

- export MFA owner/admin agora possui closure operacional após geração do artefato.
- query service:
  - `audit.application.owner_mfa_audit_evidence_export_closure_queries`
- comando:
  - `python manage.py owner_mfa_audit_evidence_export_closure --tenant-id=<tenant_id> --expected-actions-confirmed --export-scope-documented --redaction-reviewed --recipient-approved --artifact-delivered --retention-owner-confirmed --storage-decision-recorded --residual-risks-accepted`
- o closure valida:
  - export execution concluído;
  - artefato entregue ao destinatário aprovado;
  - owner de retenção definido;
  - decisão de storage/assinatura registrada;
  - riscos residuais aceitos.

### Escopo deliberado

- sem reimprimir conteúdo do export.
- sem assinar, criptografar ou armazenar artefato automaticamente.
- sem alterar `AuditLog`.
- sem platform-scope.
- sem consultar tabelas internas de `accounts`.
