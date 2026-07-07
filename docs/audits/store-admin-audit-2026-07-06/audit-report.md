# Auditoria do admin da loja

Data: 2026-07-06  
Escopo: `/ops/` tenant-scoped do Hubx Market, com foco em funcionamento das telas, lacunas para controle efetivo da loja, isolamento multi-tenant, permissões, eventos/auditoria e experiência operacional.

## Perguntas obrigatórias antes de implementar

1. **Qual módulo é responsável por essa regra?**  
   A auditoria atravessa `accounts` para owner/RBAC e dashboard, `tenants` para branding/plataforma, `catalog`, `customers`, `orders`, `payments`, `shipping`, `coupons`, `reviews`, `newsletter`, `pages`, `api_keys`, `subscriptions` e `audit`.

2. **Existe documentação sobre essa área?**  
   Sim. Foram consultados os documentos obrigatórios de arquitetura, domínio, dados, eventos, ciclo de requisição, fronteiras de módulo e UI listados no `AGENTS.md`.

3. **Isso respeita multi-tenant?**  
   Em boa parte sim, mas há pontos que ainda toleram ausência de `tenant_id` em comandos administrativos legados, especialmente em `customers` e `orders`.

4. **Isso quebra alguma fronteira de módulo?**  
   Não foi identificada quebra estrutural nova nesta auditoria. O risco principal é alguns comandos de aplicação dependerem demais do gate HTTP em vez de validarem tenant/permissão localmente.

5. **Isso afeta eventos do sistema?**  
   Sim. Produtos, branding, tenants, owners, refunds e shipping já registram eventos/auditoria em partes importantes. Algumas ações operacionais de customers/orders/shipping precisam de consistência maior em auditabilidade.

6. **Isso afeta o ciclo de requisição?**  
   Sim. O ciclo esperado para `/ops/` passa por tenant resolution, owner context, gate/RBAC, view fina, service/application, persistence, audit/events e response. As lacunas de CSRF e permissões ficam exatamente nessa borda HTTP/service.

7. **Isso exige atualização de documentação?**  
   Se houver correção estrutural de RBAC, tenant strictness, eventos ou novas capacidades de admin, atualizar `docs/modules/*`, `docs/module-boundaries.md`, `docs/request-lifecycle.md`, `docs/events-map.md` e, se necessário, `DECISIONS.md`.

## Evidências coletadas

- `python manage.py check`: sem issues.
- Suite admin relacionada: 272 testes, todos verdes.
- Navegação real via browser local em `http://hubx-checkout-demo.localhost:8000/ops/`.
- Screenshots:
  - `01-admin-dashboard-viewport.png`: dashboard e navegação principal.
  - `02-owners-actions-no-csrf.png`: lista de owners com ações inline.
  - `03-owner-action-csrf-403.png`: clique em ação inline gera 403 CSRF.
  - `04-shipping-provider-no-csrf.png`: tela de provider de shipping com form sem CSRF.
  - `05-product-create-csrf-ok.png`: criação de produto com CSRF, preço e estoque.

## Mapa funcional encontrado

O admin cobre um MVP operacional amplo:

- Dashboard da loja e navegação por permissões.
- Branding da loja.
- Catálogo: listagem, criação, edição, detalhe, desativação, analytics e métricas.
- Clientes: listagem, detalhe, flags de follow-up, reengajamento e prioridade.
- Pedidos: listagem, detalhe, status, fulfillment, cancelamento, exceções de estoque e métricas.
- Pagamentos: visão financeira e aprovação interna de refund.
- Shipping: fila, marcar enviado/entregue, provider settings e métricas.
- Coupons: listagem e criação.
- Reviews: listagem, criação e moderação.
- Newsletter: leitura/listagem.
- Pages: listagem, criação e edição.
- Owners: listagem, criação/edição, convite, ações de notificação e MFA.
- Audit: listagem e export tenant-scoped.
- API keys: quotas read-only.
- Subscriptions: leitura.
- Platform admin: tenants, onboarding, acquisitions e bootstrap de owner.

## Achados principais

## Correções aplicadas

Status após correção:

- ações inline POST de owners, customers, orders e shipping agora renderizam `csrfmiddlewaretoken`;
- testes de regressão validam CSRF nas forms inline desses módulos;
- `/ops/api-keys/` e `/ops/subscriptions/` agora participam do gate granular de `/ops/`;
- `customers.manage`, `orders.manage` e `shipping.manage` foram adicionadas à matriz RBAC;
- writes administrativos de customers, orders e shipping agora exigem `tenant_id` e role explícita com permissão de gerenciamento no command service;
- ações visuais de customers, orders e shipping ficam ocultas para roles sem permissão de gerenciamento;
- documentação de RBAC/fronteiras foi atualizada em `docs/modules/accounts.md` e `docs/module-boundaries.md`.

### P1 - Ações inline POST do admin quebram por falta de CSRF

Várias ações do admin são renderizadas como HTML em Python com `<form method="post">`, mas sem `csrfmiddlewaretoken`. Em navegador real, elas falham com 403.

Evidência:

- Owners: 3 forms na lista, 3 sem CSRF; clique em "Pausar notificações" retornou 403 CSRF.
- Shipping provider: 1 form, 1 sem CSRF; POST estrito retorna 403.
- Django `Client(enforce_csrf_checks=True)` reproduziu os 403.

Locais afetados:

- `backend/app/modules/accounts/interfaces/owner_views.py:107`
- `backend/app/modules/accounts/interfaces/owner_views.py:112`
- `backend/app/modules/customers/interfaces/views.py:203`
- `backend/app/modules/customers/interfaces/views.py:208`
- `backend/app/modules/customers/interfaces/views.py:213`
- `backend/app/modules/customers/interfaces/views.py:245`
- `backend/app/modules/customers/interfaces/views.py:250`
- `backend/app/modules/customers/interfaces/views.py:255`
- `backend/app/modules/customers/interfaces/views.py:282`
- `backend/app/modules/customers/interfaces/views.py:287`
- `backend/app/modules/customers/interfaces/views.py:292`
- `backend/app/modules/customers/interfaces/views.py:297`
- `backend/app/modules/customers/interfaces/views.py:302`
- `backend/app/modules/customers/interfaces/views.py:307`
- `backend/app/modules/orders/interfaces/views.py:171`
- `backend/app/modules/orders/interfaces/views.py:182`
- `backend/app/modules/orders/interfaces/views.py:193`
- `backend/app/modules/orders/interfaces/views.py:225`
- `backend/app/modules/orders/interfaces/views.py:231`
- `backend/app/modules/orders/interfaces/views.py:441`
- `backend/app/modules/orders/interfaces/views.py:451`
- `backend/app/modules/orders/interfaces/views.py:461`
- `backend/app/modules/orders/interfaces/views.py:468`
- `backend/app/modules/orders/interfaces/views.py:475`
- `backend/app/modules/orders/interfaces/views.py:482`
- `backend/app/modules/orders/interfaces/views.py:489`
- `backend/app/modules/orders/interfaces/views.py:496`
- `backend/app/modules/orders/interfaces/views.py:503`
- `backend/app/modules/shipping/interfaces/views.py:104`
- `backend/app/modules/shipping/interfaces/views.py:116`
- `backend/app/modules/shipping/interfaces/views.py:234`

Observação técnica:

- `ui/templates/shared/components/data_display/table.html:18` renderiza `{{ cell }}`.
- `ui/templates/shared/components/composite/data_table_toolbar.html:44` renderiza `{{ bulk_actions }}`.
- Como essas células recebem `SafeString`, o token precisa ser inserido pela própria célula/form ou a ação deve ser movida para partial/template com `{% csrf_token %}`.

Recomendação:

- Criar helper único para forms inline de `/ops/` que receba `csrf_token`, action, method, hidden fields e botões.
- Passar `get_token(request)` para builders de ações inline.
- Adicionar testes com `Client(enforce_csrf_checks=True)` para cada grupo de ação administrativa.

### P1/P2 - RBAC de `/ops/` ainda depende de feature flag e fallback permissivo

O gate HTTP de `/ops/` só é aplicado quando `HUBX_OPS_AUTH_GATE_ENFORCED=1`, mas o default de settings é `0`. Além disso, a checagem local de permissão aceita contexto sem role como compatibilidade legada.

Evidência:

- `backend/config/settings/base.py:68` define `HUBX_OPS_AUTH_GATE_ENFORCED` como desligado por padrão.
- `backend/app/modules/accounts/application/admin_permissions.py:118` mantém `permission-context-missing`.
- `backend/app/modules/accounts/interfaces/middleware.py:31` lista prefixos protegidos quando o gate está ativo.
- `/ops/api-keys/` e `/ops/subscriptions/` não aparecem em `OPS_PERMISSION_PREFIXES`, embora as views façam checagem de permissão para exibir dados.

Impacto:

- Em ambiente mal configurado, o admin pode ficar navegável sem enforcement HTTP forte.
- Em serviços que confiam apenas no gate, o sistema fica menos fail-closed.
- API keys quotas e subscriptions precisam de cobertura explícita no gate para consistência.

Recomendação:

- Manter `HUBX_OPS_AUTH_GATE_ENFORCED=1` como obrigatório em staging/prod e validado em readiness.
- Tornar ausência de role deny-by-default para ações administrativas, preservando compatibilidade apenas em rotas internas/testes explicitamente marcados.
- Adicionar prefixos de `/ops/api-keys/` e `/ops/subscriptions/` ao gate.

### P2 - Alguns comandos administrativos ainda toleram ausência de tenant/permissão

Customers e orders possuem repositórios administrativos que só filtram por tenant quando `tenant_id` é informado. Isso é documentado como compatibilidade em algumas áreas, mas para admin da loja o ideal é falhar fechado.

Evidência:

- `backend/app/modules/customers/application/admin_customer_commands.py:33`
- `backend/app/modules/orders/application/admin_order_commands.py:56`

Impacto:

- Um bug de resolução de tenant ou rota reaproveitada sem tenant poderia operar em registros globais por slug/número.
- A regra do projeto diz que dado de loja deve respeitar `tenant_id` e nunca permitir acesso cruzado entre tenants.

Recomendação:

- Para writes de `/ops/`, exigir `tenant_id` sempre.
- Separar fluxos globais/plataforma em services específicos, com permissão plataforma explícita.
- Inserir permission checks nos comandos de customers/orders/shipping quando houver mudança de estado, não apenas nas views/gate.

### P2 - Lacunas para controle efetivo da loja

O admin já serve como cockpit MVP, mas ainda não entrega controle completo de loja em produção.

Lacunas por área:

- Catálogo: não há UI completa para categorias, marcas, tags, múltiplas variantes, imagens/mídia, import/export em massa e ledger de ajuste de estoque.
- Pedidos: há status/fulfillment, mas falta fluxo operacional mais completo de separação, histórico de eventos visível, impressão/packing slip e ações em lote seguras.
- Pagamentos: aprovação de refund é interna; falta execução/reconciliação com provider, captura/retry e visão de chargebacks/disputas.
- Shipping: falta integração real de transportadora, geração de etiqueta, rastreio sincronizado e SLA operacional.
- Coupons: há criar/listar, mas falta editar, pausar/reativar, expirar e analisar performance.
- Newsletter: read-only; falta export, segmentação, opt-out admin e campanhas.
- Pages: falta arquivamento/versionamento, navegação/menu e preview mais robusto.
- API keys: quotas read-only; falta UI para criar, revogar, rotacionar e auditar chaves.
- Subscriptions: read-only; falta gestão operacional de plano, cobrança e enforcement comercial.

### P3 - UX operacional

Pontos positivos:

- Dashboard e navegação respeitam uma linguagem densa e operacional, adequada para admin.
- Identidade do tenant aparece no primeiro viewport.
- Product create tem CSRF e respeita preço/estoque em `ProductVariant`.

Riscos:

- Tabelas com muitas ações inline ficam densas e podem dificultar uso repetido.
- Ações de mudança de estado precisam de confirmação/feedback consistente.
- Algumas superfícies reaproveitam templates genéricos de customers/orders para domínios diferentes, o que pode gerar semântica visual fraca.
- A auditoria visual foi desktop-first; faltam validações mobile, teclado e leitor de tela.

## Prioridade recomendada

1. Corrigir CSRF das ações inline e adicionar testes estritos.
2. Fechar RBAC/gate para `api-keys` e `subscriptions`, e negar ausência de role em writes.
3. Exigir `tenant_id` em todos os writes de `/ops/`.
4. Completar permissões locais nos comandos de customers/orders/shipping.
5. Priorizar lacunas operacionais: catálogo avançado, pagamentos/refunds reais, shipping integrado e gestão de API keys.

## Veredito

O admin está bem encaminhado como MVP operacional e a base modular é sólida. A principal surpresa é que parte das ações visíveis não funciona no navegador por CSRF, apesar dos testes verdes. Para controle efetivo de loja, o próximo passo deve ser fechar essas bordas HTTP/RBAC/tenant antes de expandir funcionalidades.
