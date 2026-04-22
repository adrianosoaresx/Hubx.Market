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
