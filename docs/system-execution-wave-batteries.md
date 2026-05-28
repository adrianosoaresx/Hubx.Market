# System Execution Wave Batteries

Data: `2026-05-27`

Este documento pausa a execução linear de waves e consolida:

- o que já existe no sistema;
- o que ainda falta para produção/uso real;
- baterias de ondas autocontidas;
- regra de passagem automática entre baterias.

Ele deve ser usado junto com:

- `docs/system-module-status-audit.md`
- `docs/modules-index.md`
- `docs/module-boundaries.md`
- `docs/request-lifecycle.md`
- `DECISIONS.md`

---

## Estado atual resumido

### Plataforma e segurança

Já desenvolvido:

- tenant resolution por subdomínio;
- RBAC/admin ops com evidências de readiness/produção;
- owner MFA/Vault/KMS/Audit com trilha extensa de readiness, evidência, rotação e closure;
- `AuditLog` tenant-scoped, writer e admin read-only;
- API keys tenant-scoped com hash, runtime auth, DRF adapter, permission, throttle, métricas, dashboard e alert rules.

Ainda falta:

- ativação real controlada de parceiro por API key;
- quotas comerciais/billing para API pública;
- UX admin mais rica de API keys se houver carga operacional;
- instrumentação automática ampla de audit em módulos críticos;
- subscriptions/plans ainda são skeleton frente ao restante da plataforma.

### Storefront e conversão

Já desenvolvido:

- catálogo storefront com busca, filtros/facets, sort, ranking e analytics;
- PDP com reviews, badges, featured review e sinais de conversão;
- páginas institucionais tenant-owned com SEO básico;
- newsletter opt-in básico;
- carrinho com add-to-cart, idempotência, quantity/stock guards, cupons e handoff para checkout;
- checkout com delivery/payment guardrails, copy/trust e reconciliação de conflito de estoque.

Ainda falta:

- otimização de conversão baseada em dados reais;
- testes de smoke/end-to-end de storefront em ambiente real;
- page builder/menu/footer dinâmico seguem fora;
- automações lifecycle/campanhas de newsletter seguem fora.

### Commerce core

Já desenvolvido:

- pedidos com snapshots;
- pagamentos com tentativa, webhook, hosted return, pending/stale observability, refund approval/execution skeleton e evidências sandbox;
- cupons com modelo, validação, ledger, reversal e visibilidade admin;
- shipping com tracking, provider settings, delivery promise e métricas;
- customers/admin com modelos e surfaces básicas.

Ainda falta:

- provider/payment production activation real;
- shipping quote real por CEP/transportadora;
- conciliação financeira produtiva com evidências reais;
- refunds reais em produção;
- runbooks finais de operação cross-module.

### Engagement

Já desenvolvido:

- reviews com modelo, elegibilidade, submissão customer, moderação admin, status e surfaces de PDP/cards;
- newsletter opt-in/read-only admin;
- notifications com provider readiness, delivery commands, logs, métricas e tasks.

Ainda falta:

- campanhas/lifecycle messaging;
- notificações transacionais reais em produção com evidência de deliverability;
- automações de retenção e segmentação.

---

## Critérios para escolher a próxima bateria

Priorizar baterias que:

1. validam uso real sem aumentar superfície;
2. destravam produção/receita;
3. reduzem risco operacional mensurável;
4. fecham skeletons críticos;
5. evitam refinamento marginal em áreas já boas o suficiente.

Evitar baterias que:

- criam novo domínio antes de ativar o que já existe;
- adicionam features sem evidência de uso;
- misturam billing, operação e runtime numa mesma wave;
- enfraquecem tenant-scope, boundaries ou observabilidade.

---

## Battery A — API Key Partner Activation

Objetivo:

- validar a primeira ativação real/controlada de parceiro usando API pública de catálogo já documentada.

Por que agora:

- governança, endpoints, observabilidade, docs, pacote e evidência já estão fechados;
- é menor risco do que abrir novos endpoints ou quotas comerciais;
- transforma capacidade técnica em uso real.

Ondas:

1. API Key Partner Activation Smoke Contract Review — **concluída**
2. API Key Partner Activation Smoke Execution — **concluída**
3. API Key Partner Activation Evidence Capture — **concluída**
4. API Key Partner Activation Post-Smoke Monitoring — **concluída**
5. API Key Partner Activation Closure Review — **concluída**

Critério de conclusão:

- smoke de list/detail executado em ambiente alvo;
- evidência sanitizada capturada;
- sem credencial em log/doc;
- métricas e alertas observáveis;
- decisão Go/No-Go registrada.

Próxima bateria automática:

- se houver tráfego/uso real e pressão comercial: **Battery B — API Key Commercial Quotas**;
- se não houver pressão comercial: **Battery C — Payments Production Readiness**.

---

## Battery B — API Key Commercial Quotas

Objetivo:

- definir e implementar o contrato mínimo de quotas comerciais para API pública.

Por que não antes:

- quotas sem uso real viram complexidade prematura;
- onboarding e smoke devem provar necessidade antes.

Ondas:

1. API Key Commercial Quotas Contract Review — **concluída em contrato, modelo ainda pendente**
2. API Key Quota Model Minimal Execution — **concluída**
3. API Key Quota Enforcement Runtime Review — **concluída**
4. API Key Quota Enforcement Execution — **concluída**
5. API Key Quota Admin Visibility Review — **concluída**
6. API Key Quota Admin Visibility Execution — **concluída**
7. API Key Commercial Quotas Closure Review — **concluída**

Critério de conclusão:

- quota tenant/key/endpoint definida;
- enforcement testado;
- UX/admin read-only mínima;
- métricas e erro de quota claros;
- sem billing completo acoplado prematuramente.

Próxima bateria automática:

- **Battery C — Payments Production Readiness**.

---

## Battery C — Payments Production Readiness

Objetivo:

- sair de evidência sandbox/review para ativação produtiva controlada do ciclo de pagamento/refund.

Por que é crítica:

- checkout e pedidos já dependem de pagamentos para produção real;
- refund/reversal tem base, mas produção exige gate, evidência e monitoramento.

Ondas:

1. Payment Provider Production Gate Refresh Review — **concluída**
2. Payment Provider Production Activation Evidence — **concluída**
3. Payment Webhook Production Smoke Review — **concluída**
4. Payment Refund Production Gate Review — **concluída**
5. Payment Refund Production Smoke Evidence — **concluída**
6. Payment Financial Reconciliation Production Review — **concluída**
7. Payments Production Closure Review — **concluída**

Critério de conclusão:

- provider real validado;
- webhook pago/falha validado;
- refund real ou gate explícito documentado;
- reconciliação financeira mínima validada;
- rollback/runbook pronto.

Próxima bateria automática:

- **Battery D — Shipping Quote Productionization**.

---

## Battery D — Shipping Quote Productionization

Objetivo:

- evoluir shipping de tracking/promise para quote real e método de entrega produtivo.

Ondas:

1. Shipping Quote Provider Contract Review — **concluída**
2. Shipping Quote Adapter Skeleton Execution — **concluída**
3. Shipping Quote Checkout Integration Review — **concluída**
4. Shipping Quote Checkout Execution — **concluída**
5. Shipping Quote Failure UX Review — **concluída**
6. Shipping Quote Observability Execution — **concluída**
7. Shipping Quote Closure Review — **concluída**

Critério de conclusão:

- quote tenant-scoped;
- fallback honesto quando provider falhar;
- checkout não cria pedido sem delivery válido;
- observabilidade mínima.

Próxima bateria automática:

- **Battery E — Subscriptions & Tenant Billing Foundation**.

---

## Battery E — Subscriptions & Tenant Billing Foundation

Objetivo:

- tirar `subscriptions` do estado skeleton e criar base de plano/assinatura do SaaS.

Ondas:

1. Subscription Domain Contract Review — **concluída**
2. Subscription Plan Model Execution — **concluída**
3. Tenant Subscription State Execution — **concluída**
4. Subscription Admin Read Surface Review — **concluída**
5. Subscription Admin Read Surface Execution — **concluída**
6. Subscription Enforcement Boundary Review — **concluída**
7. Subscriptions Foundation Closure Review — **concluída**

Critério de conclusão:

- plano e assinatura tenant-scoped;
- sem acoplar billing provider completo cedo demais;
- admin consegue ver estado;
- boundaries de enforcement documentadas.

Próxima bateria automática:

- **Battery F — Audit Instrumentation Expansion**.

---

## Battery F — Audit Instrumentation Expansion

Objetivo:

- ampliar audit trail para ações críticas ainda não instrumentadas.

Ondas:

1. Audit Critical Actions Inventory Review
2. Audit Payment/Admin Actions Instrumentation
3. Audit API Key Actions Instrumentation
4. Audit Catalog/Admin Actions Instrumentation
5. Audit Cross-Module Evidence Review
6. Audit Instrumentation Closure Review

Critério de conclusão:

- 2–4 ações críticas novas instrumentadas;
- sem virar logging genérico;
- metadata sensível redigida;
- queries admin continuam tenant-scoped.

Status:

- **concluída**.

Entregue:

- `payments.refund.approved` e `payments.refund.execution_recorded`;
- `catalog.product.visibility_updated`;
- confirmação de cobertura existente de API keys;
- closure executável `audit_instrumentation_expansion`;
- testes tenant-scoped e sem segredo/hash/payload provider em metadata.

Próxima bateria automática:

- **Battery G — Notifications Production Delivery**.

---

## Battery G — Notifications Production Delivery

Objetivo:

- validar envio transacional real com provider e evidência de deliverability.

Ondas:

1. Notification Provider Production Gate Review
2. Notification Transactional Email Smoke Execution
3. Notification Delivery Evidence Capture
4. Notification Bounce/Failure Handling Review
5. Notification Production Monitoring Review
6. Notification Production Closure Review

Critério de conclusão:

- envio real validado;
- falhas/bounces classificados;
- logs e métricas confirmados;
- sem vazamento de dados de customer.

Status:

- **concluída**.

Entregue:

- provider production gate;
- smoke transacional real via `EmailLog`;
- evidência sanitizada com recipient mascarado;
- classificação de bounces/falhas;
- monitoring/closure por snapshot tenant-scoped;
- comando `notification_production_delivery`.

Próxima bateria automática:

- **Battery H — Customer Retention Lifecycle**.

---

## Battery H — Customer Retention Lifecycle

Objetivo:

- sair de newsletter opt-in para lifecycle messaging mínimo.

Ondas:

1. Lifecycle Messaging Contract Review
2. Newsletter Segment Query Execution
3. Post-Purchase Email Intent Review
4. Lifecycle Notification Integration Execution
5. Lifecycle Opt-Out Boundary Review
6. Retention Lifecycle Closure Review

Critério de conclusão:

- comunicação consentida;
- integração com notifications via application service/evento;
- opt-out respeitado;
- sem automação complexa prematura.

Status:

- **concluída**.

Entregue:

- segment query de newsletter subscribed;
- intent `customer.post_purchase.follow_up`;
- command service para planejar `EmailLog` pós-compra;
- boundary de opt-out;
- closure executável `customer_retention_lifecycle`.

Próxima bateria automática:

- **Battery I — Storefront Data-Driven Conversion**.

---

## Battery I — Storefront Data-Driven Conversion

Objetivo:

- usar analytics já existentes para priorizar melhorias reais de PDP/listagem.

Ondas:

1. Storefront Conversion Metrics Baseline Review
2. PDP CTA Funnel Evidence Review
3. Search/Facet Drop-Off Review
4. Product Card Conversion Experiment Contract
5. Storefront Conversion Experiment Execution
6. Storefront Conversion Closure Review

Critério de conclusão:

- baseline mensurável;
- uma melhoria executada com hipótese clara;
- sem redesenhar storefront inteiro.

Status:

- **concluída**.

Entregue:

- baseline de eventos discovery/PDP/CTA;
- funil PDP CTA;
- revisão de busca/facet sem resultado;
- contrato e execução do experimento `product_card_priority_v1`;
- closure executável `storefront_conversion`.

Próxima bateria automática:

- **Battery J — System Production Closure**.

---

## Battery J — System Production Closure

Objetivo:

- consolidar readiness geral do sistema para produção real.

Ondas:

1. System Production Readiness Matrix Refresh
2. Cross-Module Runbook Gap Review
3. Production Smoke Checklist Execution
4. Observability Coverage Closure Review
5. Rollback/Incident Drill Review
6. System Production Go/No-Go Review

Critério de conclusão:

- matriz por módulo atualizada;
- smoke checklist executável;
- runbooks críticos revisados;
- decisão Go/No-Go objetiva.

Status:

- **concluída**.

Entregue:

- matriz cross-module de readiness;
- review de runbook gaps;
- checklist declarativo de smoke produtivo;
- closure de observabilidade;
- drill de rollback/incidente;
- decisão Go/No-Go por `system_production_closure`.

Próxima bateria automática:

- se Go: iniciar trilha de crescimento/comercial;
- se No-Go: abrir bateria corretiva específica pelo maior blocker.

---

## Regra de execução automática

Ao concluir uma bateria:

1. executar closure review da própria bateria;
2. registrar decisão em `DECISIONS.md`;
3. atualizar `docs/system-module-status-audit.md`;
4. rodar testes/checks relevantes;
5. escolher automaticamente a próxima bateria por esta ordem:
   - blocker produtivo crítico;
   - maior ROI com menor superfície nova;
   - skeleton mais importante para produção;
   - melhoria customer-facing mensurável;
   - refinamento operacional.

Se a bateria falhar:

- não iniciar a próxima;
- criar uma bateria corretiva mínima;
- resolver apenas o blocker;
- repetir closure.

---

## Próxima bateria recomendada agora

**System ROI Re-Selection Review**

Primeira onda:

**Payments Production Readiness**

Motivo:

- Battery A foi fechada com ativação/evidência de parceiro;
- Battery B foi fechada com modelo, enforcement, métrica, audit e visibilidade admin;
- quotas comerciais não criam billing/plano nesta etapa;
- próximo maior ROI volta a ser produção operacional de pagamentos ou re-seleção sistêmica.

Status da re-seleção:

- `System ROI Post-Quota Re-Selection Review` recomenda **Payments Production Readiness Review** quando provider produtivo, refund e conciliação ainda forem blockers.
- após Platform Store Management closure, `system_roi_reselection` recomenda **System Validation Pass 2 — Storefront/Admin Smoke & Template Regression** quando regressões visíveis de navegação/templates estiverem confirmadas antes de novas expansões.
- `system_template_regression_smoke` executa a primeira validação dessa trilha e bloqueia retorno de `/orders/`, ausência do botão de login e 404 em `/accounts/account/orders/`.
- o próximo salto de produto adiciona **Platform Self-Service Tenant Onboarding MVP** em `/ops/platform/onboarding/`, ainda sem billing real, upload de logo, DNS/TLS automático ou self-service público do lojista.
