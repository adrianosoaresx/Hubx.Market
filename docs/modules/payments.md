# Payments

## Responsabilidade
Integrar pagamentos de pedidos.

## Entidades principais
- Payment
- PaymentTransaction

## Casos de uso
- gerar PIX
- processar cartão
- processar webhook

## Regras de negócio
- gateway inicial é Pagar.me

## Webhook readiness
- o módulo agora expõe um endpoint mínimo em `/payments/webhook/`
- o contrato atual é propositalmente pequeno e seguro:
  - aceita apenas `POST` com JSON
  - exige `X-Hubx-Webhook-Token` para payloads genéricos internos
  - para payloads estilo `Pagar.me`, já aceita validação por `X-Hub-Signature`
  - aceita identificação explícita do tenant por:
    - `tenant_slug`
    - ou `tenant_subdomain`
  - exige `order_number`
  - traduz apenas `payment.paid`
- o webhook do `Pagar.me` agora também pode validar a origem usando HMAC-SHA1 do body com a `PAGARME_SECRET_KEY`
- a normalização do payload agora acontece inteiramente dentro de `payments`
- `orders` continua recebendo apenas um contrato limpo e estável:
  - `tenant_id`
  - `order_number`
  - `payment_reference`
  - `payment_source_label`
- formatos atualmente aceitos:
  - genérico Hubx:
    - `event_type=payment.paid`
    - `event_type=payment.failed`
    - `tenant_slug` ou `tenant_subdomain`
    - `order_number`
  - estilo Pagar.me:
    - `type=charge.paid`
    - `type=charge.payment_failed`
    - `type=order.paid`
    - `type=order.payment_failed`
    - `data.id` e/ou `data.charges[].id`
    - `data.metadata.tenant_slug|tenant_subdomain`
    - `data.metadata.order_number`
  - estilo Stripe:
    - `type=payment_intent.succeeded`
    - `type=payment_intent.payment_failed`
    - `data.object.id`
    - `data.object.metadata.tenant_slug|tenant_subdomain`
    - `data.object.metadata.order_number`
- ele apenas:
  - valida o token compartilhado
  - resolve o tenant ativo
  - encaminha eventos positivos para `orders.application.customer_order_payment_commands.confirm_external_payment(...)`
  - encaminha eventos negativos para `orders.application.customer_order_payment_commands.fail_external_payment(...)`
- isso mantém:
  - `payments` como origem do evento externo
  - `orders` como dono do lifecycle do pedido
  - views finas na camada `interfaces/`

## Gateway readiness mínima
- o módulo `payments` agora também possui `PaymentAttempt` como trilho persistido entre:
  - `order created`
  - pagamento ainda pendente
  - futuros eventos `payment.paid` / `payment.failed`
- essa entidade guarda de forma leve:
  - `tenant`
  - `order`
  - `payment_method_code`
  - `provider_code`
  - `provider_label`
  - `status`
  - `amount`
  - `external_reference`
- o contrato atual continua conservador:
  - checkout pode abrir a tentativa pendente
  - webhook reconcilia a mesma tentativa quando houver referência externa
  - `orders` continua dono do lifecycle do pedido
  - `payments` passa a ser dono explícito da trilha da tentativa de pagamento
- a abertura da `PaymentAttempt` agora também exige `tenant_id` explícito:
  - não inicia trilha pendente por lookup global de `order_number`
  - sem tenant resolvido, falha fechado
- para reduzir ambiguidade sob concorrência, agora existe no banco a garantia de no máximo **uma `PaymentAttempt` pendente por pedido**
- a command layer também trata corrida de criação de tentativa reaproveitando a pendente vencedora quando outra transação chegar primeiro

## First gateway bootstrap contract
- o módulo `payments` agora também expõe um comando mínimo para transformar uma `PaymentAttempt` pendente em contrato de saída para um gateway real
- esse bootstrap continua seguro e idempotente:
  - só aceita tentativa ainda `pending`
  - gera e persiste `provider_request_key`
  - registra `bootstrapped_at`
  - não confirma pagamento
  - não toca `orders`
- esse bootstrap agora também exige `tenant_id` explícito:
  - não monta contrato externo por lookup global de `attempt_key`
  - sem tenant resolvido, falha fechado
- o contrato de saída atual inclui:
  - `provider_code`
  - `provider_label`
  - `provider_request_key`
  - `payment_attempt_key`
  - `order_number`
  - `amount`
  - `currency_code`
  - `customer_name`
  - `customer_email`
  - `metadata` com `tenant_slug`, `tenant_subdomain`, `order_number` e `payment_attempt_key`
- a intenção é dar ao futuro adapter de gateway um payload único e estável, sem vazar detalhes do provider para `orders`

## First provider adapter lite
- o módulo `payments` agora também possui um adapter estrutural leve para consumir o contrato de bootstrap e devolver uma intenção/cobrança externa simulada de forma estável
- esse adapter ainda não integra SDK real; ele serve para:
  - exercitar a boundary de saída
  - manter a integração externa dentro de `payments`
  - evitar que `checkout` ou `orders` conheçam detalhes do provider
- o comando atual:
  - aceita uma `PaymentAttempt` pendente
  - reaproveita o contrato idempotente de bootstrap
  - devolve `external_reference` e `action_url`
  - persiste esses sinais no `metadata` da tentativa
  - preserva a tentativa em `pending` até um evento real `payment.paid` ou `payment.failed`
- a criação da intent externa agora também exige `tenant_id` explícito:
  - não abre checkout externo por lookup global de `attempt_key`
  - sem tenant resolvido, responde como indisponível

## Hosted payment redirect readiness
- o módulo `payments` agora também expõe um redirect interno mínimo em `/payments/hosted/<attempt_key>/`
- esse endpoint:
  - resolve a `PaymentAttempt` pendente
  - usa o provider adapter configurado para obter a `action_url`
  - redireciona o navegador para o ambiente hospedado de pagamento
- o redirect agora exige request com tenant resolvido:
  - não opera mais como lookup global por `attempt_key`
  - sem `tenant_id` explícito, devolve indisponibilidade segura
- a intenção é:
  - não expor a URL crua do provider direto da customer area
  - manter a boundary externa concentrada em `payments`
  - permitir fallback seguro para `back_url` relativo quando a tentativa não puder mais ser usada
- quando a intent externa falha ou o redirect não pode ser aberto, a `PaymentAttempt` agora também registra breadcrumbs operacionais na timeline para facilitar recovery e troubleshooting da retomada
- o resumo operacional da tentativa também já consegue sinalizar quando um estado `pending` ficou tempo demais sem atualização recente, ajudando a distinguir acompanhamento normal de possível estado órfão
- quando esse `pending` envelhecido ainda possui retomada segura disponível, a query layer também passa a recomendar explicitamente a próxima ação operacional mais segura:
  - reabrir o hosted payment quando ainda houver tentativa reaproveitável
  - ou orientar que o estado já merece revisão operacional antes de qualquer novo passo
- a summary query da tentativa também passou a sinalizar **drift operacional** entre `Order` e `PaymentAttempt`, especialmente quando:
  - o pedido já está confirmado, mas a tentativa ainda aparece `pending`
  - ou a tentativa já aparece `paid`, mas o pedido ainda não avançou para estado confirmado

## Hosted payment return readiness
- o módulo `payments` agora também expõe um retorno interno mínimo em `/payments/return/<attempt_key>/`
- esse retorno continua conservador:
  - não confirma pagamento por URL de retorno
  - não altera `orders`
  - apenas registra um `status_hint` e metadados do retorno na `PaymentAttempt`
- esse retorno também exige request com tenant resolvido:
  - não registra hints em tentativas descobertas globalmente por `attempt_key`
  - sem tenant válido, responde como indisponível
- o objetivo é permitir que o produto:
  - receba o usuário de volta do provider
  - mostre feedback previsível
  - continue aguardando a confirmação segura via evento real (`webhook`) antes de avançar o pedido

## First real provider integration lite
- o gateway inicial real continua sendo `Pagar.me`
- quando `PAGARME_SECRET_KEY` estiver configurada, o adapter de `payments` deixa de usar a intenção fake e passa a criar um link hospedado real em `https://api.pagar.me/core/v5/paymentlinks`
- a autenticação segue o contrato oficial por `Basic Auth` com a chave secreta
- o payload atual continua propositalmente mínimo:
  - `type=order`
  - `name`
  - `order_code`
  - `payment_settings.accepted_payment_methods`
  - `payment_settings.pix_settings` quando o método for `pix`
  - `cart_settings.items` com um item sintético representando o total do pedido
  - `cart_settings.items[].amount`
  - `cart_settings.items[].default_quantity`
- a intenção criada continua isolada em `payments`:
  - `checkout` não conhece SDK nem endpoint do provider
  - `orders` não recebe payload bruto do gateway
- quando a chave ainda não estiver configurada, o sistema mantém fallback no adapter lite para não quebrar fluxos de desenvolvimento

## Test environment payment pilot checklist

### Configuração mínima
- configurar no ambiente:
  - `PAYMENTS_PROVIDER_DEFAULT=pagarme`
  - `PAGARME_SECRET_KEY=<test secret key>` ou `PAGARME_API_KEY=<test secret key>`
  - `PAGARME_API_BASE_URL=https://api.pagar.me/core/v5`
  - `PAGARME_WEBHOOK_SIGNATURE_HEADER=X-Hub-Signature`
- manter `PAYMENTS_WEBHOOK_TOKEN` apenas como fallback para payloads genéricos e cenários internos
- publicar uma URL de webhook acessível pelo provider apontando para:
  - `/payments/webhook/`
- antes do piloto, também é possível validar o bloqueio operacional atual com:
  - `python manage.py payment_sandbox_readiness --webhook-url https://<public-host>/payments/webhook/`

### Fluxo oficial do piloto
1. criar pedido inicial via `checkout`
2. confirmar que a `PaymentAttempt` pendente foi aberta
3. abrir `Abrir pagamento hospedado` na customer area
4. confirmar que `payments` criou ou reaproveitou a intenção externa
5. concluir ou falhar o pagamento no ambiente de teste do provider
6. aguardar o webhook assinado
7. validar reconciliação em `orders` e `payments`

### Critérios de aceite
- `PaymentAttempt` nasce com:
  - `status=pending`
  - `provider_code=pagarme`
- o redirect hospedado devolve `action_url` real do provider
- o webhook do `Pagar.me` é aceito apenas com assinatura válida
- em caso de sucesso:
  - `Order.status = paid`
  - `payment_status = Pagamento confirmado`
  - `PaymentAttempt.status = paid`
- em caso de falha:
  - `Order.status` continua `pending`
  - `payment_status = Pagamento falhou`
  - `PaymentAttempt.status = failed`
- estoque só muda em confirmação real de pagamento

### Logs úteis para o piloto
- `payments.provider_intent.created`
- `payments.provider_intent.reused`
- `payments.provider_intent.failed`
- `payments.hosted_redirect.ready`
- `payments.hosted_redirect.unavailable`
- `payments.hosted_return.recorded`
- `payments.webhook.processed`
- `payments.webhook.invalid_signature`

### Validação controlada do webhook
- para fechar o happy path sem depender do pagamento manual completo, o projeto agora expõe:
  - `python manage.py payment_sandbox_validate_webhook --tenant-slug <slug> --order-number <numero>`
- esse comando:
  - monta um payload estilo `Pagar.me`
  - assina o body com `PAGARME_SECRET_KEY`
  - envia o `POST` para `/payments/webhook/` dentro do próprio app
  - imprime o resultado final da reconciliação em:
    - `Order.status`
    - `Order.payment_status`
    - `PaymentAttempt.status`
- para validar a negativa:
  - `python manage.py payment_sandbox_validate_webhook --tenant-slug <slug> --order-number <numero> --event failed`

### Falhas esperadas e leitura rápida
- `provider-intent-unavailable`
  - chave ausente
  - payload rejeitado pelo provider
  - tentativa não está mais `pending`
- `payment-webhook-invalid-signature`
  - assinatura do `Pagar.me` não bate com o body recebido
- `payment-webhook-invalid-payload`
  - evento sem `tenant_slug|tenant_subdomain` ou `order_number`
- `payment-webhook-tenant-unavailable`
  - tenant não foi resolvido com os dados do payload
- `hosted-payment-unavailable`
  - tentativa já não está usável ou a criação do link falhou

### Observações do piloto
- usar somente chaves de teste na primeira ativação
- confirmar no dashboard do provider quais eventos estão realmente habilitados para a URL do webhook
- durante o piloto, observar especialmente a variação entre:
  - `order.paid`
  - `order.payment_failed`
  - `charge.paid`
  - `charge.payment_failed`
- a URL de retorno hospedada continua sendo apenas hint de navegação; a confirmação segura segue no webhook

## Operational observability lite
- a `PaymentAttempt` agora mantém uma timeline operacional leve em `metadata.timeline`
- essa timeline registra apenas marcos úteis para operação e suporte, como:
  - criação da tentativa
  - bootstrap idempotente para o provider
  - criação do link hospedado
  - abertura do checkout hospedado
  - retorno hospedado
  - webhook `paid` / `failed`
- a intenção continua enxuta:
  - sem stack nova de observabilidade
  - sem auditoria pesada
  - sem mover o lifecycle para fora de `payments`
- o objetivo é deixar a trilha mais legível para:
  - troubleshooting em sandbox contínuo
  - leitura rápida da tentativa mais recente
  - suporte operacional antes de produção
- além disso, a tentativa agora também pode guardar `checkout_session_key` quando nascer a partir da conclusão real do checkout
- isso fortalece a leitura cross-module entre:
  - `CheckoutSession`
  - `Order`
  - `PaymentAttempt`
  - `OrderStatusHistory`

## Payment alert signal instrumentation lite
- além dos logs e da timeline operacional, o módulo agora também registra sinais críticos de alerta em um ponto único dentro de `payments`
- a implementação continua propositalmente leve:
  - sem stack nova de observabilidade
  - sem acoplar Prometheus direto ao módulo neste momento
  - com contadores e último snapshot mantidos via cache da aplicação
- isso cria uma base simples para alerting operacional real sem depender só de leitura manual de logs

### Sinais instrumentados agora
- `provider_intent.failed`
  - quando o provider real não consegue criar a intenção externa
- `hosted_redirect.unavailable`
  - quando a abertura do checkout hospedado não consegue avançar
- `webhook.invalid_signature`
  - quando um webhook estilo `Pagar.me` chega com assinatura inválida
- `webhook.tenant_unavailable`
  - quando o payload até normaliza, mas o tenant não é resolvido com segurança
- `provider_rollout.blocked`
  - quando o rollout controlado bloqueia checkout real com fallback `block`
- `payment_confirmation.stock_conflict`
  - quando a confirmação do pagamento encontra conflito de estoque na reconciliação

### Leitura operacional
- cada sinal guarda pelo menos:
  - contador acumulado
  - último horário
  - `tenant_id`
  - `order_number`
  - `attempt_key`
  - `provider_code`
  - `reason_code`
- a intenção é permitir o próximo passo de alerting sem precisar reinventar os sinais críticos da trilha
- logs continuam úteis para detalhe; o registrador de sinais passa a cobrir o resumo acionável

### Export para monitoramento do ambiente
- o módulo agora também expõe um endpoint interno de métricas em:
  - `/payments/metrics/alert-signals/`
- o formato atual segue a convenção de exposição do Prometheus
- o endpoint é propositalmente enxuto:
  - exporta `hubx_payments_alert_signal_total`
  - exporta `hubx_payments_alert_signal_last_timestamp_seconds`
  - usa apenas o label `signal_code` para evitar cardinalidade alta
- a leitura rica por tenant, pedido e tentativa continua nos logs e snapshots internos; a métrica fica focada em alerting
- para proteção operacional, o acesso exige:
  - header `X-Hubx-Observability-Token`
  - valor configurado em `PAYMENTS_OBSERVABILITY_TOKEN`
- para facilitar o scrape em Prometheus, o exporter também aceita:
  - `Authorization: Bearer <PAYMENTS_OBSERVABILITY_TOKEN>`

### Primeiras regras de alerta
- o repositório agora inclui uma primeira versão de regras em:
  - `infra/observability/prometheus/payments-alert-rules.yml`
- alertas iniciais cobertos:
  - falha recorrente de `provider_intent.failed`
  - recorrência de `hosted_redirect.unavailable`
  - ocorrência de `webhook.invalid_signature`
  - recorrência de `webhook.tenant_unavailable`
  - ocorrência de `payment_confirmation.stock_conflict`
- também há um exemplo de scrape para Prometheus em:
  - `infra/observability/prometheus/payments-scrape.example.yml`
- a proposta continua conservadora:
  - baixa cardinalidade nas métricas
  - thresholds simples para primeira operação
  - detalhe operacional continua em logs, timeline e snapshots

### Dashboard e activation runbook
- o dashboard inicial da trilha fica em:
  - `infra/observability/grafana/payments-alert-signals-dashboard.json`
- o painel cobre:
  - volume na última hora para os sinais mais críticos
  - série temporal de incremento por sinal
  - tabela do último timestamp observado por `signal_code`
- o exemplo de roteamento do Alertmanager fica em:
  - `infra/observability/alertmanager/payments-routing.example.yml`
- o runbook curto de ativação operacional fica em:
  - `infra/observability/README.md`
- a sequência sugerida é:
  1. configurar `PAYMENTS_OBSERVABILITY_TOKEN`
  2. publicar o scrape no Prometheus
  3. carregar as alert rules
  4. configurar o Alertmanager
  5. importar o dashboard no Grafana

## Controlled rollout readiness
- a integração real agora também respeita um gate explícito de rollout antes de sair do fallback lite
- esse gate usa três sinais de configuração:
  - `PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE`
    - `off`
    - `sandbox`
    - `controlled`
    - `live`
  - `PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS`
    - lista de `slug` ou `subdomain` autorizados quando o modo for `controlled`
  - `PAYMENTS_REAL_PROVIDER_FALLBACK_MODE`
    - `lite`
    - `block`
- leitura prática:
  - `sandbox`: provider real continua liberado para ambiente de teste
  - `controlled`: só tenants allowlisted usam provider real
  - `live`: provider real liberado para todos os tenants
  - `off`: força fallback
- quando o tenant ficar fora do rollout:
  - `lite` mantém adapter estrutural de fallback
  - `block` não abre checkout externo e registra o bloqueio na timeline da `PaymentAttempt`
- isso deixa a ativação:
  - reversível
  - explícita
  - observável por tenant
  - sem espalhar regra de rollout para `checkout`, `orders` ou `accounts`

## Controlled rollout runbook

### Pré-condições
- confirmar que o trilho sandbox já está saudável para o tenant de teste:
  - `PaymentAttempt` nasce como `pending`
  - hosted checkout abre
  - webhook `paid` e `failed` reconciliam corretamente
- confirmar no ambiente:
  - `PAYMENTS_PROVIDER_DEFAULT=pagarme`
  - `PAGARME_SECRET_KEY` configurada
  - `PAGARME_API_BASE_URL` correta
  - `PAGARME_WEBHOOK_SIGNATURE_HEADER` correta
- confirmar que a URL pública do webhook continua ativa e cadastrada no provider

### Ativação controlada por tenant
1. definir:
   - `PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=controlled`
   - `PAYMENTS_REAL_PROVIDER_FALLBACK_MODE=block` ou `lite`
2. incluir o tenant em `PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS` usando:
   - `slug`
   - ou `subdomain`
3. validar configuração com:
   - `python manage.py payment_sandbox_readiness --webhook-url https://<host-publico>/payments/webhook/`
4. executar um pedido de teste real no tenant allowlisted
5. acompanhar:
   - `payments.provider_intent.created`
   - `payments.hosted_redirect.ready`
   - `payments.webhook.processed`
   - estado final em `Order` e `PaymentAttempt`

### Estratégia de fallback
- `PAYMENTS_REAL_PROVIDER_FALLBACK_MODE=lite`
  - o tenant fora do rollout continua com adapter estrutural
  - útil quando queremos preservar a continuidade do fluxo sem abrir checkout real
- `PAYMENTS_REAL_PROVIDER_FALLBACK_MODE=block`
  - o tenant fora do rollout não abre checkout externo
  - a tentativa registra `provider_rollout_blocked` na timeline
  - útil quando queremos evitar qualquer ambiguidade operacional fora da allowlist

### Critérios mínimos de aceite
- tenant allowlisted:
  - cria `provider_intent` real
  - abre `action_url` real do provider
  - recebe webhook assinado com sucesso
  - mantém `Order` e `PaymentAttempt` reconciliados
- tenant fora da allowlist:
  - respeita `fallback_mode`
  - não burla o gate por engano
  - registra contexto de rollout em `PaymentAttempt.metadata.provider_rollout`

### Sinais de monitoramento inicial
- logs:
  - `payments.provider_intent.created`
  - `payments.provider_intent.reused`
  - `payments.provider_intent.blocked.rollout`
  - `payments.provider_intent.failed`
  - `payments.hosted_redirect.ready`
  - `payments.hosted_redirect.unavailable`
  - `payments.webhook.processed`
  - `payments.webhook.invalid_signature`
- leitura de dados:
  - `PaymentAttempt.status`
  - `PaymentAttempt.metadata.timeline`
  - `PaymentAttempt.metadata.provider_rollout`
  - `Order.status`
  - `Order.payment_status`
  - `Order.payment_reference`

### Rollback operacional
- rollback rápido por tenant:
  - remover o tenant de `PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS`
- rollback amplo mantendo fallback:
  - trocar `PAYMENTS_REAL_PROVIDER_FALLBACK_MODE`
    - `block` → `lite`
    - ou `lite` → `block`
- desligamento global:
  - `PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=off`
- depois do rollback, validar:
  - novos checkouts não usam provider real fora do comportamento esperado
  - timeline da `PaymentAttempt` continua registrando bloqueio/fallback de forma legível

### Leitura prática de incidentes
- `provider-intent-unavailable`
  - olhar chave, payload, rollout e status da tentativa
- `provider_rollout_blocked`
  - tenant fora da allowlist com `fallback=block`
- `payment-webhook-invalid-signature`
  - revisar assinatura/header e segredo configurado
- `payment-webhook-tenant-unavailable`
  - revisar `tenant_slug` / `tenant_subdomain` enviados pelo provider

### Recomendação operacional
- começar sempre com poucos tenants
- preferir `controlled + block` quando a equipe quiser máxima previsibilidade
- migrar para `controlled + lite` apenas se fizer sentido manter continuidade sem checkout real
- só considerar `live` depois que:
  - sandbox contínuo estiver estável
  - rollout controlado passar sem incidentes materiais

## Production incident & alerting runbook

### Objetivo
- detectar cedo sinais de degradação na trilha:
  - `checkout`
  - `payments`
  - `orders`
- responder rápido sem ambiguidade operacional
- preservar a capacidade de rollback por tenant ou global

### Sinais que devem virar alerta operacional
- recorrência anormal de:
  - `payments.provider_intent.failed`
  - `payments.hosted_redirect.unavailable`
  - `payments.webhook.invalid_signature`
  - `payments.webhook.tenant_unavailable`
- crescimento de pedidos em `pending` com:
  - `PaymentAttempt` sem evolução
  - webhook esperado não reconciliado
- crescimento de tentativas com:
  - `provider_rollout_blocked`
  - `provider-intent-unavailable`

### Classificação sugerida de incidente
- **Sev 1**
  - pagamentos não conseguem avançar para tenants já ativos
  - webhook não reconcilia pedidos de forma consistente
  - risco de impacto amplo no fechamento de compra
- **Sev 2**
  - falhas intermitentes de intent ou redirect
  - falhas isoladas de assinatura ou resolução de tenant
  - impacto controlado, mas com risco de expansão
- **Sev 3**
  - ruído operacional sem perda imediata de fluxo
  - falha pontual já contida por fallback ou block

### Fluxo de resposta
1. confirmar escopo:
   - tenant único
   - grupo pequeno
   - impacto amplo
2. identificar último estado confiável:
   - `CheckoutSession`
   - `Order`
   - `PaymentAttempt`
   - `OrderStatusHistory`
3. verificar logs-chave:
   - `payments.provider_intent.*`
   - `payments.hosted_redirect.*`
   - `payments.webhook.*`
4. decidir contenção:
   - remover tenant da allowlist
   - mudar para `fallback=lite`
   - mudar para `rollout_mode=off`
5. validar recuperação:
   - novas tentativas seguem o comportamento esperado
   - pedidos novos não ficam presos sem trilha operacional clara

### Autoridade de rollback
- **rollback por tenant**
  - quando o incidente estiver isolado
  - ação preferida: remover tenant da allowlist
- **rollback amplo**
  - quando houver falha estrutural na integração
  - ação preferida:
    - `PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=off`
    - ou troca controlada de `fallback_mode`

### Como validar recuperação
- novo pedido de teste respeita o gate esperado
- `PaymentAttempt` volta a registrar timeline coerente
- `Order` e `PaymentAttempt` permanecem reconciliados
- não há crescimento anormal de:
  - `pending` sem evolução
  - `provider_rollout_blocked` inesperado
  - `invalid_signature`

### Leitura rápida por tipo de falha
- **Intent**
  - olhar segredo, payload, rollout e resposta do provider
- **Webhook**
  - olhar assinatura, tenant, `order_number` e ordem do evento
- **Rollback**
  - confirmar se a configuração carregada no ambiente realmente mudou
- **Pending preso**
  - localizar:
    - `checkout_session_key`
    - `order_number`
    - `payment_reference`
    - último evento da timeline

### Recomendação operacional mínima antes de produção
- ter pelo menos:
  - alertas baseados nesses sinais
  - responsável claro por rollback
  - checklist de validação pós-incidente
  - tenant piloto com acompanhamento manual próximo

## Wave AR — Payment Product Experience Review
- a revisão do eixo `payments` como produto mostra que a base transacional e operacional já está bem mais forte do que a experiência percebida pelo cliente
- o módulo já cobre bem:
  - criação de `PaymentAttempt`
  - checkout hospedado
  - retorno hospedado
  - webhook
  - rollout controlado por tenant
  - sinais para alerta e runbook operacional
- a próxima evolução não deve reabrir provider/gateway agora
- o ganho mais claro está em transformar estado técnico de pagamento em leitura de produto mais óbvia para o cliente

### O que já está forte
- **fronteira transacional**
  - `payments` segue responsável por tentativa, provider, webhook, redirect/return e métricas
  - `checkout`, `orders` e `accounts` consomem sinais sem assumir regra interna do gateway
- **multi-tenant**
  - redirect/return e consultas usam `tenant_id`
  - rollout real continua controlado por tenant
  - métricas e alertas preservam contexto de tenant
- **recuperação**
  - pedidos pendentes já conseguem expor retomada de pagamento hospedado
  - tentativas antigas/presas já geram sinais operacionais e superfície de recovery
- **observabilidade**
  - falhas de intent, redirect, assinatura, tenant e pending preso já têm sinais documentados

### Gaps de experiência percebida
- **estado do pagamento**
  - a operação sabe diferenciar `pending`, `paid`, `failed`, stale e drift
  - mas o cliente ainda pode perceber isso como “pagamento pendente/falhou” sem contexto suficiente do que fazer agora
- **retorno do provider**
  - o retorno hospedado registra hint e volta para o produto
  - mas a narrativa de “voltamos, ainda estamos verificando” pode ficar mais explícita na superfície do pedido
- **falha e retry**
  - a retomada existe
  - mas ainda vale revisar a microcopy para separar melhor:
    - tentativa falhou
    - pedido continua salvo
    - próximo clique seguro
- **pendência longa**
  - stale state já existe
  - mas a mensagem pode ficar menos operacional e mais orientada à ação do cliente

### Decisão prática
- considerar o motor de pagamentos suficientemente preparado para esta fase de produto
- priorizar agora uma revisão curta de mensagens e estados customer-facing
- manter fora de escopo por enquanto:
  - novo provider
  - parcelamento avançado
  - conciliação financeira
  - mudanças em webhook
  - mudanças em rollout/alertas

### Próxima wave
- **Wave AS — Payment State Messaging Review**
- foco:
  - revisar a copy de estado, retorno, falha e retomada que aparece no detalhe do pedido
  - decidir o menor recorte seguro antes de qualquer execução

## Wave AS — Payment State Messaging Review
- a revisão das mensagens customer-facing mostra que o sistema já expõe sinais suficientes para orientar o cliente
- o principal ajuste agora é reduzir termos operacionais demais e deixar cada estado responder:
  - o que aconteceu
  - se o pedido continua salvo
  - qual é o próximo passo seguro
  - se ainda existe verificação externa em andamento

### Superfícies revisadas
- **`payments.application.payment_attempt_queries`**
  - monta `status_label`, `operational_title`, `operational_description` e timeline da tentativa
  - ainda usa linguagem útil para operação, mas um pouco pesada para cliente final
- **`payments.application.hosted_return_commands`**
  - registra o retorno hospedado e diferencia retorno genérico, sucesso pendente de verificação e falha
  - a semântica técnica está correta, mas a experiência precisa ser traduzida no detalhe do pedido
- **`accounts.application.account_customer_area_queries`**
  - transforma estado de pedido/pagamento em copy da área do cliente
  - concentra o melhor ponto de ajuste porque é a superfície final que o cliente lê
- **`order_detail_page`**
  - apenas renderiza os blocos recebidos
  - não precisa mudar para este recorte

### Estados prioritários
- **pagamento pendente normal**
  - mensagem deve explicar que o pedido foi registrado e aguarda evolução do pagamento
  - evitar parecer erro
- **retorno hospedado recebido**
  - mensagem deve explicar que a pessoa voltou do ambiente de pagamento e que a confirmação pode depender de verificação/webhook
  - evitar prometer pagamento aprovado antes da reconciliação
- **tentativa falhou**
  - mensagem deve separar falha da tentativa de perda do pedido
  - reforçar que o pedido continua salvo para retomada
- **pendência longa**
  - mensagem deve ser menos operacional e mais orientada à ação
  - ainda pode preservar “revisão operacional” quando não houver ação automática segura
- **retomada hospedada**
  - CTA/helper deve reforçar continuidade segura, não “conserto manual”

### Menor recorte seguro
- ajustar primeiro somente a copy gerada por:
  - `_pending_recovery_guidance`
  - `_order_pending_recovery_guidance`
  - `_current_state_helper`
  - `_build_order_detail_actions_payload`
  - `_apply_order_detail_payment_attempt_enrichment`
- preservar sem mudança:
  - templates
  - `PaymentAttempt`
  - webhook
  - hosted redirect/return
  - criação de nova sessão de retry
  - regras de tenant

### Decisão prática
- a próxima execução deve ser uma mudança pequena de copy em `accounts.application.account_customer_area_queries`
- `payments` continua como fonte técnica dos sinais
- `accounts` continua responsável por traduzir esses sinais para a experiência do cliente
- isso respeita a fronteira entre módulos e evita transformar o módulo de pagamentos em camada de apresentação

### Próxima wave
- **Wave AT — Payment State Messaging Copy Execution**
- foco:
  - executar o menor ajuste de linguagem no detalhe do pedido
  - tornar pendência, retorno, falha e retomada mais claros sem alterar comportamento transacional

## Wave AT — Payment State Messaging Copy Execution
- o primeiro ajuste customer-facing de pagamentos foi executado no detalhe do pedido
- a mudança ficou concentrada em `accounts.application.account_customer_area_queries`
- `payments` segue como fonte técnica dos sinais; `accounts` traduz esses sinais para linguagem de produto

### Escopo executado
- **estado atual do pedido**
  - pagamento pendente agora explica que o pedido já foi registrado e aguarda evolução/verificação externa
  - falha deixa mais claro que a tentativa não avançou, mas o pedido continua salvo
- **recovery de tentativa pendente**
  - pendência longa agora fala em confirmação ausente e retomada segura
  - quando existe hosted payment, o texto orienta reabrir o ambiente seguro antes de iniciar outra tentativa
  - quando existe retry, o texto explica que uma nova sessão cria um caminho limpo
- **pedido pendente antigo**
  - mensagens ficaram menos operacionais e mais orientadas a suporte/continuidade
  - o pedido salvo é reforçado como garantia de continuidade
- **ações**
  - hosted payment passa a usar “pagamento seguro” em vez de linguagem excessivamente técnica de “hospedado”
  - retry reforça que o pedido continua salvo
  - confirmação manual ficou mais explícita como ação para pagamento confirmado fora do fluxo automático
- **enriquecimento narrativo da tentativa**
  - resumo deixa de dizer apenas “tentativa atual”
  - passa a dizer “pagamento em acompanhamento” e traduz último evento como atualização registrada

### O que não mudou
- template do detalhe do pedido
- `PaymentAttempt`
- webhook
- hosted redirect/return
- criação de sessão de retry
- tenant scope
- regras transacionais de pedido/estoque

### Leitura prática
- a experiência de pagamento fica menos técnica para o cliente
- estados delicados agora respondem melhor:
  - o pedido está salvo?
  - devo esperar verificação?
  - devo retomar?
  - devo iniciar uma nova tentativa?
  - preciso de suporte?

### Próxima wave
- **Wave AU — Payment Return Result UX Review**
- foco:
  - revisar como os `result` de retorno hospedado e indisponibilidade aparecem depois do redirect
  - decidir se falta uma mensagem explícita na página do pedido para “voltamos do provider, estamos verificando”

## Wave AU — Payment Return Result UX Review
- a revisão do retorno do provider mostra que o fluxo já tem uma superfície explícita no topo do detalhe do pedido
- `payments` redireciona para `back_url` com `result`
- `accounts.interfaces.views._build_order_detail_feedback_context` traduz esse `result` em `page_feedback`
- `order_detail_page` renderiza o feedback antes do grid principal do pedido

### Results cobertos hoje
- **`hosted-payment-unavailable`**
  - aparece quando o redirect/return não consegue operar com segurança
  - hoje comunica indisponibilidade, mas ainda usa “pagamento hospedado”
- **`hosted-payment-returned`**
  - aparece quando a pessoa voltou do ambiente externo sem hint conclusivo
  - hoje explica que seguimos aguardando confirmação do provider
- **`hosted-payment-return-pending-verification`**
  - aparece quando o provider retornou hint positivo
  - hoje evita prometer confirmação final antes do webhook/evento seguro
- **`hosted-payment-return-failed`**
  - aparece quando o retorno indica falha/cancelamento
  - hoje orienta revisar o pedido e tentar novamente

### O que está correto
- o fluxo respeita tenant pelo request host antes de registrar retorno
- o retorno não confirma pagamento sozinho
- a mensagem fica na página certa: detalhe do pedido
- a área do cliente continua sendo a camada de apresentação
- `payments` continua responsável apenas por registrar retorno e devolver o `result`

### Gaps de UX
- **linguagem técnica**
  - ainda há termos como “provider” e “pagamento hospedado”
  - depois da Wave AT, isso destoou da linguagem mais clara de “pagamento seguro”
- **verificação pendente**
  - o caso positivo deveria reforçar melhor:
    - você voltou do ambiente seguro
    - ainda estamos verificando
    - o pedido continua salvo
    - nenhuma ação extra é necessária imediatamente
- **falha/cancelamento**
  - pode separar melhor:
    - a tentativa não concluiu
    - o pedido continua salvo
    - a pessoa pode retomar quando quiser
- **teste de feedback**
  - há testes bons para redirect/return em `payments`
  - falta uma âncora mais direta em `accounts` garantindo que cada `result` renderiza a mensagem customer-facing esperada

### Decisão prática
- não é necessário alterar o fluxo de redirect/return agora
- o menor próximo recorte seguro é ajustar apenas o mapping de `page_feedback` em `accounts.interfaces.views`
- adicionar testes de renderização para os `result` de retorno hospedado
- preservar sem mudança:
  - `HostedPaymentReturnView`
  - `HostedPaymentRedirectView`
  - `PaymentAttempt`
  - webhook
  - templates
  - tenant scope

### Próxima wave
- **Wave AV — Payment Return Result Copy Execution**
- foco:
  - trocar linguagem técnica por linguagem de pagamento seguro/verificação
  - cobrir os results principais com testes na área do cliente

## Wave AV — Payment Return Result Copy Execution
- a copy dos resultados de retorno hospedado foi ajustada na área do cliente
- o fluxo técnico permaneceu inalterado
- a execução ficou restrita ao mapping de `page_feedback` em `accounts.interfaces.views`

### Escopo executado
- **`hosted-payment-unavailable`**
  - passa a falar em “pagamento seguro indisponível”
  - reforça que o pedido continua salvo
- **`hosted-payment-returned`**
  - passa a explicar que a pessoa voltou do pagamento seguro
  - reforça que a confirmação segura ainda está sendo aguardada
- **`hosted-payment-return-pending-verification`**
  - mantém o cuidado de não prometer pagamento aprovado antes da reconciliação
  - informa que nenhuma ação extra é necessária imediatamente
- **`hosted-payment-return-failed`**
  - comunica que a tentativa não concluiu ou foi cancelada
  - reforça que o pedido continua salvo para revisão e nova tentativa

### Testes
- a área do cliente agora cobre diretamente os principais `result` de retorno hospedado
- isso protege a camada customer-facing sem depender apenas dos testes de redirect/return em `payments`

### O que não mudou
- `HostedPaymentReturnView`
- `HostedPaymentRedirectView`
- `PaymentAttempt`
- webhook
- templates
- tenant scope
- regras de confirmação de pagamento

### Leitura prática
- depois de voltar do ambiente seguro, o cliente recebe uma mensagem mais clara sobre:
  - continuidade do pedido
  - verificação pendente
  - ausência de ação imediata quando aplicável
  - possibilidade de tentar novamente quando houve falha

### Próxima wave
- **Wave AW — Payment Product Experience Wrap-Up Review**
- foco:
  - revisar se o eixo de experiência de pagamentos já pode ser encerrado nesta fase
  - separar o que ficou para roadmap futuro de métodos reais, parcelamento e conciliação

## Wave AW — Payment Product Experience Wrap-Up Review
- o eixo de experiência de pagamentos pode ser considerado encerrado nesta fase
- a trilha saiu de uma base operacional forte para uma experiência customer-facing mais clara
- não há neste momento um próximo recorte pequeno e urgente dentro do mesmo eixo sem abrir temas maiores de produto/financeiro

### O que ficou pronto nesta fase
- **motor operacional**
  - `PaymentAttempt`
  - hosted redirect
  - hosted return
  - webhook
  - rollout por tenant
  - alert signals e runbook operacional
- **estado customer-facing**
  - pagamento pendente comunica pedido salvo e verificação externa possível
  - falha comunica tentativa não concluída sem sugerir perda do pedido
  - pendência longa orienta retomada segura ou suporte
- **retomada**
  - hosted payment comunica ambiente seguro
  - retry comunica nova sessão limpa
  - pedido salvo permanece explícito
- **retorno do ambiente seguro**
  - indisponibilidade, retorno genérico, verificação pendente e falha/cancelamento têm feedback próprio
  - retorno positivo não promete confirmação antes da reconciliação segura
- **fronteiras**
  - `payments` continua responsável por sinais técnicos e integração
  - `accounts` traduz esses sinais para a experiência do cliente
  - `orders` permanece dono do estado do pedido

### O que ficou fora de escopo intencionalmente
- novos métodos reais de pagamento
- parcelamento avançado por provider
- conciliação financeira/backoffice
- estorno/cancelamento/refund como produto
- tela administrativa financeira
- automações de suporte para pagamento preso
- expansão visual do painel de pagamento no detalhe do pedido

### Leitura objetiva
- a experiência atual já responde melhor:
  - “meu pedido está salvo?”
  - “o pagamento confirmou?”
  - “voltei do pagamento, e agora?”
  - “falhou, perdi o pedido?”
  - “posso tentar de novo?”
- o que sobra já não parece ajuste de copy ou boundary
- sobra roadmap funcional maior de pagamentos/financeiro

### Decisão prática
- encerrar o eixo de **Payment Product Experience** nesta fase
- não continuar insistindo em micro-ajustes de pagamento agora
- o próximo passo deve voltar ao roadmap funcional mais amplo do produto

### Próxima wave
- **Wave AX — Shipping Product Experience Review**
- foco:
  - revisar frete/entrega como experiência de produto
  - mapear clareza de prazo, custo, estado de envio e pós-compra sem mexer ainda em integração de frete

## Wave FD — Payments Operational Parity Review
- a revisão de paridade operacional mostrou que `payments` já tinha bons artefatos técnicos:
  - métricas Prometheus
  - alert rules
  - dashboard Grafana
  - routing Alertmanager
  - readiness sandbox
  - validação de webhook sandbox
- a lacuna principal era a ausência de um runbook dedicado consolidando ativação, diagnóstico e observabilidade.

### Escopo executado
- `docs/modules/payments-operational-runbook.md`
- consolidação de:
  - variáveis de ambiente críticas
  - readiness sandbox
  - validação de webhook
  - endpoint de métricas
  - alertas iniciais
  - diagnóstico rápido

### Leitura operacional
- não houve mudança em regra transacional.
- não houve mudança em webhook, hosted redirect ou confirmação de pagamento.
- o ganho foi tornar a operação de payments tão explícita quanto shipping.

### Próxima macro-abordagem recomendada
- **Payments Retention/Reconciliation Review**
- motivo:
  - o runbook existe; a próxima lacuna operacional provável é revisar retenção/consulta de tentativas e sinais para suporte/conciliação.

## Wave FE — Payments Attempt Triage Execution
- foi criado comando operacional de listagem de `PaymentAttempt`.
- a decisão foi não implementar pruning de tentativas financeiras neste momento.

### Escopo executado
- management command `list_payment_attempts`
- filtros:
  - `--tenant-id`
  - `--status`
  - `--stale-hours`
  - `--limit`
- runbook atualizado com triagem de tentativas
- testes de:
  - filtro por tenant/status
  - filtro de pendências antigas

### Leitura operacional
- `PaymentAttempt` é registro sensível para suporte, conciliação e rastreabilidade financeira.
- apagar tentativas exige política mais clara de retenção/legal/financeiro.
- por enquanto, o ganho seguro é facilitar investigação de:
  - pendências longas
  - tentativas falhas
  - divergências entre pedido e tentativa

### Próxima macro-abordagem recomendada
- **Payments Attempt Metrics Review**
- motivo:
  - agora há triagem CLI; o próximo passo natural é expor volume de tentativas por status/tenant para observabilidade operacional.

## Wave FF — Payments Attempt Metrics Execution
- o exporter Prometheus de payments passou a incluir volume de `PaymentAttempt` por tenant/status.
- a métrica complementa os alert signals, que continuam focados em falhas críticas/eventos.

### Escopo executado
- métrica:
  - `hubx_payments_attempt_total{tenant_id,status}`
- alerta:
  - `HubxPaymentsPendingAttemptsHigh`
- dashboard:
  - painel “PaymentAttempts por status”
- runbook/observability atualizados
- teste do endpoint de métricas ampliado

### Leitura operacional
- agora é possível acompanhar backlog de tentativas pendentes sem depender só de CLI.
- a métrica mantém `tenant_id`, preservando investigação por loja.
- não houve mudança em confirmação de pagamento, webhook ou criação de tentativa.

### Próxima macro-abordagem recomendada
- **Payments Operational Wrap-Up Review**
- motivo:
  - payments já tem runbook, triagem CLI e métrica de tentativas; vale revisar se o pacote operacional desta fase está completo.

## Wave FG — Payments Operational Wrap-Up Review
- o pacote operacional de payments pode ser considerado completo para esta fase.
- a abordagem não mexeu no fluxo financeiro/transacional; fortaleceu operação, suporte e observabilidade.

### O que ficou pronto
- runbook dedicado:
  - `docs/modules/payments-operational-runbook.md`
- readiness sandbox:
  - `payment_sandbox_readiness`
- validação de webhook:
  - `payment_sandbox_validate_webhook`
- triagem de tentativas:
  - `list_payment_attempts`
- métricas:
  - `hubx_payments_alert_signal_total`
  - `hubx_payments_alert_signal_last_timestamp_seconds`
  - `hubx_payments_attempt_total`
- observabilidade:
  - scrape Prometheus
  - alert rules
  - dashboard Grafana
  - routing Alertmanager

### O que fica fora de escopo
- pruning de `PaymentAttempt`
- conciliação financeira/backoffice completa
- refund/estorno
- relatórios contábeis
- retenção legal/financeira formal

### Leitura objetiva
- payments agora tem paridade operacional razoável com shipping.
- o próximo domínio crítico para o mesmo tratamento é `notifications`, porque entrega de comunicação também já tem métricas/artefatos e tende a precisar de runbook/triagem operacional clara.

### Próxima macro-abordagem recomendada
- **Notifications Operational Parity Review**
- motivo:
  - notifications já possui pipeline e observabilidade; falta confirmar se tem runbook e comandos suficientes para operar incidentes de entrega.
