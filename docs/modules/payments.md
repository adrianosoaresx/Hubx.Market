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
- provider inicial configurado é Asaas para checkout hospedado de pedidos.
- Pagar.me permanece como provider alternativo e base existente de refund sandbox-first.
- detalhes de provider ficam em `payments.infrastructure`; `checkout` e `orders` recebem apenas contratos estáveis.

## Webhook readiness
- o módulo agora expõe um endpoint mínimo em `/payments/webhook/`
- o contrato atual é propositalmente pequeno e seguro:
  - aceita apenas `POST` com JSON
  - exige `X-Hubx-Webhook-Token` para payloads genéricos internos
  - para payloads estilo `Pagar.me`, já aceita validação por `X-Hub-Signature`
  - para payloads Asaas, aceita token via `asaas-access-token`, `x-asaas-token` ou token compartilhado Hubx
  - aceita identificação explícita do tenant por:
    - `tenant_slug`
    - ou `tenant_subdomain`
  - exige `order_number`
  - traduz apenas `payment.paid`
- o webhook do `Pagar.me` agora também pode validar a origem usando HMAC-SHA1 do body com a `PAGARME_SECRET_KEY`
- o webhook do `Asaas` normaliza eventos `PAYMENT_RECEIVED`/`PAYMENT_CONFIRMED` como `payment.paid` e eventos de atraso, deleção, refund ou chargeback como `payment.failed`
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
  - estilo Asaas:
    - `event=PAYMENT_RECEIVED`
    - `event=PAYMENT_CONFIRMED`
    - `event=PAYMENT_OVERDUE`
    - `event=PAYMENT_DELETED`
    - `event=PAYMENT_REFUNDED`
    - `event=PAYMENT_CHARGEBACK_REQUESTED`
    - `payment.id`
    - `payment.externalReference=hubx-market:<tenant_subdomain>:<order_number>`
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

## Asaas hosted payment adapter
- `PAYMENTS_PROVIDER_DEFAULT=asaas` é o default para ambientes novos.
- o adapter Asaas cria cliente e pagamento hospedado usando:
  - `ASAAS_API_KEY`
  - `ASAAS_SANDBOX`
  - `ASAAS_BASE_URL`
  - `ASAAS_WEBHOOK_TOKEN`
- o adapter envia autenticação pelo header `access_token`.
- `pix`, `boleto` e `credit_card` são mapeados para `PIX`, `BOLETO` e `CREDIT_CARD`; outros métodos caem em `UNDEFINED`.
- o app redireciona para `invoiceUrl`/URL hospedada retornada pelo Asaas e não coleta cartão, CVV, validade ou token de cartão.
- a referência externa segue `hubx-market:<tenant_subdomain>:<order_number>` para permitir normalização idempotente do webhook.
- refund Asaas usa `POST /payments/{id}/refund` de forma conservadora; respostas assíncronas ou status desconhecido permanecem como `accepted` no ledger.
- segredos não devem ser versionados; em sandbox, o projeto usa os mesmos nomes de variáveis já existentes em outros serviços Hubx.

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

## Wave FH — Payments Customer Experience Re-entry Review
- reabrimos a hipótese de continuar em **Payments customer experience** depois do fechamento de checkout/recovery.
- a revisão encontrou que o eixo já foi trabalhado em duas camadas:
  - experiência customer-facing (`Payment Product Experience`)
  - operação/suporte (`Payments Operational Parity`, triagem e métricas)

### O que já existe
- retorno hospedado diferencia:
  - indisponibilidade
  - retorno genérico
  - verificação pendente
  - falha/cancelamento
- área do cliente comunica:
  - pedido salvo
  - pagamento pendente
  - falha sem perda do pedido
  - retomada segura quando aplicável
- operação possui:
  - `PaymentAttempt`
  - webhook
  - hosted redirect/return
  - comando `list_payment_attempts`
  - métrica `hubx_payments_attempt_total`
  - dashboard/runbook/alertas

### Leitura objetiva
- continuar agora em payments tenderia a virar microcopy, painéis ou estados adicionais sem ganho proporcional.
- os próximos ganhos relevantes já são temas maiores:
  - métodos reais de pagamento
  - conciliação financeira/backoffice
  - refund/estorno
  - tela financeira administrativa
  - SLA de pagamento preso

## Wave FI — Payments Customer Experience Stop/Continue Decision
- decisão:
  - **não continuar implementando payments customer experience agora**
- motivo:
  - a experiência atual já responde às dúvidas principais do cliente
  - a operação já tem sinais mínimos para suporte
  - novas waves pequenas teriam retorno marginal

### Próxima abordagem recomendada
- voltar ao roadmap funcional amplo e escolher uma área com lacuna mais clara de produto.
- candidatos melhores que payments neste momento:
  - `storefront/PDP conversion`
  - `admin merchant operations`
  - `catalog publishing quality`
  - `shipping/fulfillment customer clarity`

## Wave FJ — Checkout/Payment Execution Readiness Review
- reabrimos `payments` pelo eixo transacional depois do fechamento de `Cart Reliability`.
- a hipótese inicial era que pagamento real, webhook e baixa pós-pagamento ainda fossem uma lacuna grande.
- a revisão mostrou que o sistema já possui um fluxo end-to-end relevante:
  - `PaymentAttempt` tenant-scoped
  - redirect hospedado para provider
  - return hospedado com verificação pendente
  - webhook `payment.paid` / `payment.failed`
  - reconciliação da tentativa
  - confirmação do pedido
  - baixa operacional de estoque após pagamento confirmado

### Contrato atual
- `payments` é dono de:
  - tentativa de pagamento
  - bootstrap de contrato com provider
  - criação/reuso de intent externa
  - recebimento e normalização de webhook
  - sinais operacionais de alerta
- `orders` é dono de:
  - confirmação/falha do pagamento no pedido
  - transição do pedido para `paid`
  - histórico operacional do pedido
  - validação final de inventário no momento da confirmação
  - baixa operacional de estoque pós-pagamento
- `catalog` continua dono dos dados de variante e estoque persistido.

### Leitura objetiva
- não faz sentido criar outro esqueleto de pagamento agora.
- o caminho crítico já existe e está parcialmente coberto por testes.
- a próxima evolução segura é endurecer o contrato de confirmação paga, especialmente quando o webhook pago encontra conflito de estoque.

### Riscos restantes
- o retorno hospedado continua apenas registrando hint; a confirmação real depende do webhook.
- não há motor de reserva/alocação antes do pagamento.
- refund/estorno e reversão financeira continuam fora desta fase.
- conciliação financeira/backoffice ainda é um produto maior, não uma micro-wave.

### Próxima wave recomendada
- **Checkout/Payment Execution Wave 2 — Paid Webhook Inventory Conflict Hardening**
- foco:
  - adicionar cobertura explícita para webhook `payment.paid` quando a confirmação encontra conflito de estoque
  - garantir que o pedido não vira `paid`
  - garantir que a tentativa não vira `paid`
  - garantir que o alerta operacional seja registrado

## Wave FK — Paid Webhook Inventory Conflict Hardening
- a wave confirmou que o comportamento transacional já estava correto.
- o webhook `payment.paid` delega a confirmação para `orders`.
- quando `orders` retorna `payment-confirmation-stock-conflict`, `payments` responde `409` e registra sinal operacional.

### Escopo executado
- teste de contrato para webhook pago com estoque indisponível no momento da confirmação.
- garantias cobertas:
  - pedido permanece `pending`
  - `payment_status` não vira confirmado
  - `PaymentAttempt` permanece `pending`
  - `external_reference` da tentativa não é reconciliada como paga
  - `paid_at` continua vazio
  - estoque não sofre nova mutação
  - histórico `payment_paid_external` não é criado
  - email de confirmação não é registrado
  - `payment_confirmation.stock_conflict` é emitido com tenant, pedido, provider e reason code

### Leitura objetiva
- não houve necessidade de mudar o command service.
- a lacuna era de proteção regressiva, não de regra.
- o fluxo pago com conflito final agora está coberto como boundary entre `payments`, `orders` e `catalog`.

### Próxima wave recomendada
- **Checkout/Payment Execution Wave 3 — Hosted Return Verification UX Review**
- foco:
  - revisar se o retorno hospedado com sucesso pendente comunica bem que webhook ainda é a fonte de verdade
  - decidir se basta UX/copy existente ou se precisamos de uma consulta segura da tentativa/pedido para reduzir ansiedade do cliente

## Wave FL — Hosted Return Verification UX Review
- a revisão confirmou que o retorno hospedado já está tratado como sinal informativo, não como confirmação financeira.
- `hosted_return_commands.register_return(...)` registra o hint do provider na tentativa e retorna estados customer-facing.
- `accounts.interfaces.views` traduz esses estados em feedback no detalhe do pedido.

### Estados revisados
- `hosted-payment-returned`
  - comunica que o cliente voltou do ambiente seguro
  - reforça que o pedido continua salvo enquanto a confirmação segura não chega
- `hosted-payment-return-pending-verification`
  - comunica que houve avanço no ambiente de pagamento
  - reforça que o pedido só muda depois da confirmação segura
  - evita pedir ação extra do cliente
- `hosted-payment-return-failed`
  - comunica falha/cancelamento sem perder o pedido
  - preserva retomada segura
- `hosted-payment-unavailable`
  - comunica indisponibilidade sem alterar estado financeiro

### Decisão
- manter o webhook como única fonte de verdade para confirmar pagamento.
- não consultar provider diretamente no detalhe do pedido nesta fase.
- não converter `status=succeeded` no retorno hospedado em `Order.paid`.
- não reconciliar `PaymentAttempt` como pago a partir do return.

### Motivo
- retorno hospedado é navegação do browser e pode chegar antes, depois ou sem o webhook.
- provider return pode trazer apenas hint, não liquidação confiável.
- consultar provider no detalhe adicionaria latência, acoplamento e risco de regra financeira em surface customer-facing.
- a copy atual já reduz ansiedade sem prometer confirmação.

### Próxima wave recomendada
- **Checkout/Payment Execution Wave 4 — Payment Pending Operational State Review**
- foco:
  - revisar se pedido/tentativa em verificação pendente têm estado operacional suficiente para suporte
  - decidir se precisamos de um estado explícito de “pagamento em verificação” ou se `PaymentAttempt.timeline` + detalhe do pedido já bastam

## Wave FM — Payment Pending Operational State Review
- a revisão avaliou se o fluxo precisa de um novo status persistido, como `verifying`, `awaiting_webhook` ou `pending_verification`.
- conclusão:
  - **não criar novo status agora**.
- o estado operacional pendente já é composto por:
  - `PaymentAttempt.status=pending`
  - `PaymentAttempt.metadata.timeline`
  - `latest_event_code`
  - `latest_event_at`
  - `provider_return`
  - `provider_intent`
  - idade da tentativa pendente
  - detecção de drift entre tentativa e pedido

### Superfícies revisadas
- detalhe do pedido na área do cliente:
  - mostra “Trilha do pagamento”
  - mostra timeline da tentativa
  - mostra stale state quando a tentativa pendente envelhece
  - mostra drift quando pedido e tentativa divergem
  - mantém CTA hospedado quando há tentativa pendente retomável
- comando operacional:
  - `list_payment_attempts`
  - permite filtrar por tenant, status e pendência antiga
- métricas:
  - `hubx_payments_attempt_total{tenant_id,status}`
  - permite observar backlog de tentativas pendentes por tenant

### Decisão
- manter `pending` como status persistido único para tentativa ainda não reconciliada.
- tratar “em verificação” como leitura derivada de timeline/return, não como estado financeiro.
- não adicionar migration nem novo enum de status nesta fase.
- não alterar `Order.payment_status` para “em verificação” apenas por browser return.

### Motivo
- um novo status intermediário criaria transições adicionais sem mudar a fonte de verdade.
- o webhook continua sendo o marco que decide `paid` ou `failed`.
- a timeline já preserva granularidade operacional sem contaminar o estado financeiro.
- suporte já consegue enxergar pendência, idade, provider, referência externa e drift.

### Próxima wave recomendada
- **Checkout/Payment Execution Wave 5 — Payment Stale Attempt Alert Review**
- foco:
  - revisar se a pendência antiga deve virar alerta operacional automático
  - decidir threshold inicial usando o que já existe em `PaymentAttempt` e métricas
  - evitar job novo se dashboard/alert rule por métrica já for suficiente

## Wave FN — Payment Stale Attempt Alert Review
- a revisão confirmou que já existe alerta para backlog total:
  - `HubxPaymentsPendingAttemptsHigh`
  - baseado em `sum(hubx_payments_attempt_total{status="pending"}) > 100`
- esse alerta é útil para volume, mas não responde à pergunta operacional mais urgente:
  - “alguma loja tem tentativa pendente antiga demais?”

### Leitura atual
- a área do cliente já classifica tentativa pendente antiga:
  - warning após 30 minutos sem atualização recente
  - critical após 6 horas sem atualização recente
- o comando operacional já permite triagem:
  - `list_payment_attempts --stale-hours=6`
- a métrica atual `hubx_payments_attempt_total{tenant_id,status}` só mede quantidade.
- Prometheus ainda não consegue alertar idade real da tentativa pendente mais antiga por tenant.

### Decisão
- adicionar uma métrica derivada por tenant na próxima execução:
  - `hubx_payments_pending_attempt_oldest_age_seconds{tenant_id}`
- manter o threshold inicial em 6 horas:
  - `> 21600`
- manter severidade `warning` inicialmente.
- não criar Celery beat, job agendado ou novo modelo para esse recorte.
- manter triagem manual via `list_payment_attempts --tenant-id=<id> --status=pending --stale-hours=6`.

### Motivo
- idade de pendência é mais acionável que backlog agregado em MVP.
- métrica por tenant preserva isolamento operacional e reduz ruído.
- calcular no scrape é suficiente para o volume esperado nesta fase.
- job assíncrono só faria sentido quando houver SLA formal de conciliação/expiração.

### Próxima wave recomendada
- **Checkout/Payment Execution Wave 6 — Payment Stale Attempt Metric Execution**
- foco:
  - exportar `hubx_payments_pending_attempt_oldest_age_seconds{tenant_id}`
  - adicionar alert rule `HubxPaymentsStalePendingAttempt`
  - atualizar runbook e teste do endpoint de métricas

## Wave FO — Payment Stale Attempt Metric Execution
- a métrica de pendência antiga foi adicionada ao exporter Prometheus de payments.
- ela complementa `hubx_payments_attempt_total`, que mede volume, com um sinal de idade por tenant.

### Escopo executado
- métrica:
  - `hubx_payments_pending_attempt_oldest_age_seconds{tenant_id}`
- cálculo:
  - considera apenas `PaymentAttempt.status=pending`
  - agrupa por `tenant_id`
  - usa a menor `updated_at` pendente como referência
  - exporta idade em segundos no momento do scrape
- alerta:
  - `HubxPaymentsStalePendingAttempt`
  - threshold inicial `> 21600`
  - `for: 10m`
  - severidade `warning`
- runbook:
  - diagnóstico de tentativa pendente antiga
  - comando recomendado com `--tenant-id`, `--status=pending` e `--stale-hours=6`
- teste:
  - endpoint de métricas agora verifica a presença da nova série por tenant

### Leitura operacional
- uma tentativa antiga isolada agora vira sinal independente de backlog agregado.
- o alerta continua tenant-scoped e não cria novo estado financeiro.
- o diagnóstico segue manual e seguro nesta fase; não há job de expiração automática.

### Próxima wave recomendada
- **Checkout/Payment Execution Wave 7 — Payment Stale Attempt Dashboard Review**
- foco:
  - decidir se o dashboard existente precisa destacar idade máxima por tenant
  - evitar painel novo se a alert rule e o runbook já forem suficientes para operação inicial

## Wave FP — Payment Stale Attempt Dashboard Review
- a revisão confirmou que o dashboard atual de payments já cobre:
  - sinais críticos por código
  - timestamp do último sinal
  - volume de `PaymentAttempt` por status
- depois da métrica `hubx_payments_pending_attempt_oldest_age_seconds{tenant_id}`, ficou uma lacuna visual:
  - o alerta detecta tentativa antiga por tenant
  - o runbook explica a triagem
  - mas o dashboard ainda não mostra rapidamente qual tenant tem maior idade pendente

### Decisão
- adicionar um painel dedicado no dashboard atual.
- tipo recomendado:
  - `table`
- query recomendada:
  - `hubx_payments_pending_attempt_oldest_age_seconds`
- colunas esperadas:
  - `tenant_id`
  - idade em segundos
- ordenação:
  - maior idade primeiro
- unidade:
  - `s`
- manter o painel no mesmo dashboard `Hubx Payments Alert Signals`.

### Motivo
- o alerta sozinho indica que há problema, mas o painel acelera triagem visual.
- tabela por tenant é mais útil que timeseries agregada para esse caso.
- não há necessidade de criar dashboard separado nesta fase.
- a operação continua simples: dashboard aponta tenant, runbook orienta comando de triagem.

### Próxima wave recomendada
- **Checkout/Payment Execution Wave 8 — Payment Stale Attempt Dashboard Execution**
- foco:
  - adicionar painel Grafana para `hubx_payments_pending_attempt_oldest_age_seconds`
  - atualizar README de observabilidade com a nova métrica
  - validar JSON do dashboard

## Wave FQ — Payment Stale Attempt Dashboard Execution
- o dashboard Grafana de payments recebeu um painel específico para idade de tentativa pendente.

### Escopo executado
- dashboard atualizado:
  - `infra/observability/grafana/payments-alert-signals-dashboard.json`
- painel:
  - `Tentativa pendente mais antiga por tenant`
- query:
  - `hubx_payments_pending_attempt_oldest_age_seconds`
- tipo:
  - tabela instantânea
- unidade:
  - segundos
- ordenação:
  - maior idade primeiro
- thresholds visuais:
  - verde abaixo de 30 minutos
  - laranja acima de 30 minutos
  - vermelho acima de 6 horas

### Leitura operacional
- o alerta `HubxPaymentsStalePendingAttempt` continua sendo o gatilho.
- o painel agora acelera a identificação do tenant afetado.
- o runbook continua apontando a triagem por `list_payment_attempts`.
- não foi criado dashboard separado para evitar fragmentação nesta fase.

### Próxima wave recomendada
- **Checkout/Payment Execution Wave 9 — Payment Execution Closure Review**
- foco:
  - revisar se a trilha de execução payments já está suficientemente fechada para esta fase
  - separar próximos temas maiores: refund/estorno, conciliação financeira, provider real production rollout e SLA formal

## Wave FR — Payment Execution Closure Review
- decisão:
  - **Go técnico para encerrar `Checkout/Payment Execution` nesta fase**.
- a trilha deixou de ser uma hipótese sobre “pagamento real inexistente” e virou uma revisão/hardening do fluxo já existente.

### O que está pronto
- `PaymentAttempt` tenant-scoped para acompanhar tentativas.
- bootstrap de contrato com provider e criação/reuso de intent externa.
- hosted redirect e hosted return com UX honesta de verificação pendente.
- webhook assinado como fonte de verdade para `payment.paid` e `payment.failed`.
- confirmação externa delegada para `orders`.
- validação final de inventário antes de marcar pedido como pago.
- baixa operacional de estoque pós-pagamento confirmado.
- proteção regressiva para `payment.paid` com conflito de estoque.
- reconciliação de tentativa apenas quando o pedido confirma/falha com segurança.
- timeline operacional, stale state e drift no detalhe do pedido.
- triagem CLI com `list_payment_attempts`.
- métricas, alertas e dashboard para:
  - sinais críticos
  - tentativas por status
  - tentativa pendente antiga por tenant

### Riscos aceitos
- não há reserva/alocação pré-pagamento.
- retorno hospedado não consulta provider diretamente.
- tentativa pendente antiga ainda exige triagem manual.
- não há refund/estorno.
- não há conciliação financeira/backoffice completa.
- não há SLA formal automatizado de expiração/reconciliação.
- production rollout real de provider ainda depende de ativação operacional controlada.

### Go/No-Go
- **Go para encerrar esta abordagem agora**.
- **No-Go para continuar em micro-waves de payments execution** sem escolher um tema maior.

### Próximos temas maiores
- `Payment Refund/Reversal Foundation`
  - estorno, reversão operacional e impacto em pedido/estoque.
- `Payments Financial Reconciliation`
  - conciliação backoffice, divergências financeiras e relatório operacional.
- `Provider Production Rollout`
  - ativação real controlada por tenant, credenciais, webhooks públicos e rollback.
- `Payment SLA Automation`
  - expiração/reconciliação automática de tentativas antigas.

### Próxima abordagem recomendada
- **Provider Production Rollout Review**
- motivo:
  - a base transacional e operacional já existe; o próximo bloqueio real para produção é ativar provider real com critérios de rollout, rollback e validação fim a fim.

## Wave FS — Provider Production Rollout Contract Review
- a revisão mostrou que já existem blocos importantes:
  - `decide_provider_rollout(...)`
  - rollout `sandbox`, `controlled`, `live` e `off`
  - allowlist por tenant no modo `controlled`
  - `fallback_mode` `lite` ou `block`
  - alert signal `provider_rollout.blocked`
  - readiness command
- lacuna encontrada:
  - `live` global podia liberar provider real para todos sem uma confirmação adicional explícita.
- decisão:
  - `live` global precisa de flag dedicada.

## Wave FT — Provider Production Rollout Safety Execution
- foi adicionado hardening para impedir ativação `live` global acidental.

### Escopo executado
- `PAYMENTS_REAL_PROVIDER_LIVE_GLOBAL_ENABLED`
  - quando `false` ou ausente, `PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=live` não libera provider real.
  - reason code: `live-global-not-enabled`.
  - quando `true`, `live` global fica explicitamente liberado.
  - reason code: `live-global-enabled`.
- readiness command:
  - ganhou `--target=sandbox|production`.
  - produção exige rollout `controlled` ou `live`.
  - produção exige `PAYMENTS_REAL_PROVIDER_FALLBACK_MODE=block`.
  - produção bloqueia `live` sem `PAYMENTS_REAL_PROVIDER_LIVE_GLOBAL_ENABLED=true`.
- testes:
  - bloqueio de `live` global sem flag.
  - liberação de `live` global com flag.
  - readiness production bloqueado/liberado.

## Wave FU — Provider Production Rollout Runbook Review
- o runbook operacional agora diferencia sandbox, production controlled rollout e live global.
- decisão operacional:
  - iniciar produção por `controlled`, não por `live`.
  - manter `fallback_mode=block` em produção.
  - usar `live` apenas após piloto validado e com flag explícita.
  - rollback rápido deve usar `PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=off` ou remover tenant da allowlist.

### Próxima wave
- **Provider Production Rollout Closure Review**
- foco:
  - fechar go/no-go da abordagem e separar rollout operacional real de futuras trilhas financeiras.

## Wave FV — Provider Production Rollout Closure Review
- decisão:
  - **Go técnico para piloto controlado de provider real**.
- decisão complementar:
  - **No-Go para live global imediato**.

### Critérios mínimos atendidos
- rollout controlado por tenant existe.
- provider real Pagar.me é ativado apenas quando o tenant está allowlisted.
- modo `live` global exige flag explícita adicional.
- readiness production bloqueia:
  - provider default incorreto
  - rollout mode inadequado
  - controlled sem tenants
  - fallback diferente de `block`
  - live sem flag global explícita
  - segredo/API/header/webhook ausentes
- provider failures geram alert signal.
- rollback operacional é simples:
  - remover tenant da allowlist
  - ou mudar rollout para `off`

### Riscos aceitos
- não houve chamada real ao provider neste ambiente.
- credenciais e webhook público continuam responsabilidade de ambiente/deploy.
- conciliação financeira, refund/estorno e SLA automático continuam fora desta abordagem.
- live global só deve ser considerado após piloto controlado com monitoramento estável.

### Próxima abordagem recomendada
- **Payments Financial Reconciliation Review**
- motivo:
  - com rollout controlado tecnicamente protegido, o próximo grande risco de produção deixa de ser abrir o provider e passa a ser reconciliar divergências financeiras de forma operacionalmente confiável.

## Wave FW — Payments Financial Reconciliation Surface Review
- a revisão mostrou que a base de conciliação já tinha sinais dispersos:
  - `PaymentAttempt.status`
  - `amount`
  - `external_reference`
  - `paid_at` / `failed_at`
  - `Order.status`
  - `Order.payment_status`
  - `Order.payment_reference`
  - drift no detalhe do pedido
- lacuna:
  - não havia uma auditoria operacional explícita para listar divergências financeiras entre `PaymentAttempt` e `Order`.

### Decisão
- começar com auditoria read-only, não ledger persistido.
- manter ownership:
  - `payments` audita tentativas e divergências financeiras.
  - `orders` continua dono da transição do pedido.
- não criar ajuste automático nesta fase.

## Wave FX — Payments Financial Reconciliation Audit Execution
- foi criado o auditor operacional de divergências financeiras.

### Escopo executado
- service:
  - `payments.application.financial_reconciliation_queries`
- command:
  - `list_payment_reconciliation_issues`
- filtros:
  - `--tenant-id`
  - `--limit`
- issues detectadas:
  - `attempt_paid_order_unconfirmed`
  - `order_confirmed_attempt_not_paid`
  - `attempt_amount_mismatch`
  - `paid_attempt_missing_external_reference`
  - `payment_reference_mismatch`

### Leitura operacional
- a auditoria não altera dados.
- a saída é tenant-scoped e serve para suporte/conciliação.
- divergências críticas continuam exigindo conferência de provider, webhook e histórico do pedido antes de qualquer correção manual.

## Wave FY — Payments Financial Reconciliation Runbook Review
- o runbook operacional foi atualizado com o comando de auditoria.
- a orientação explícita é:
  - investigar divergências antes de qualquer ajuste manual.
  - não transformar auditoria em correção automática nesta fase.
  - preservar `PaymentAttempt` como trilha financeira sensível.

### Próxima wave
- **Payments Financial Reconciliation Closure Review**
- foco:
  - decidir se o recorte mínimo de conciliação financeira está pronto para esta fase
  - separar ledger/backoffice financeiro completo como trilha maior

## Wave FZ — Payments Financial Reconciliation Closure Review
- decisão:
  - **Go técnico para conciliação financeira mínima read-only**.
- decisão complementar:
  - **No-Go para ledger/backoffice financeiro completo nesta abordagem**.

### O que ficou pronto
- auditoria operacional tenant-scoped.
- comando `list_payment_reconciliation_issues`.
- detecção de:
  - tentativa paga sem pedido confirmado
  - pedido confirmado sem tentativa paga
  - valor divergente entre tentativa e pedido
  - tentativa paga sem referência externa
  - referência externa divergente entre tentativa e pedido
- runbook com orientação de triagem.
- testes cobrindo divergência crítica, divergência de valor, filtro por tenant e estado limpo.

### Riscos aceitos
- não há ledger financeiro persistido.
- não há tela admin financeira.
- não há correção automática.
- não há estorno/refund.
- não há conciliação por extrato/settlement do provider.

### Próxima abordagem recomendada
- **Payments Admin Finance Surface Review**
- motivo:
  - agora existe auditoria CLI; o próximo ganho prático é decidir se merchants/admin precisam de uma tela interna mínima de divergências antes de criar ledger financeiro completo.

## Wave GA — Payments Admin Finance Surface Review
- a revisão confirmou que já havia:
  - auditoria CLI read-only
  - service tenant-scoped de divergências
  - dashboard merchant ops com links para filas operacionais
- lacuna:
  - não havia surface visual para suporte/admin ver divergências financeiras sem rodar comando.

### Decisão
- criar uma tela admin mínima e read-only.
- não criar correção manual.
- não criar ledger persistido.
- manter a surface dentro de `ops/payments/finance/`.

## Wave GB — Payments Admin Finance Surface Execution
- foi criada a página administrativa mínima para divergências financeiras.

### Escopo executado
- rota:
  - `/ops/payments/finance/`
- namespace:
  - `payments_ops:admin-finance`
- view:
  - `AdminPaymentFinanceView`
- template reutilizado:
  - `admin_orders_list_page.html`
- conteúdo:
  - severidade
  - pedido
  - tentativa
  - divergência
- dashboard merchant ops:
  - adiciona atalho `Financeiro`

### Garantias
- surface é read-only.
- listagem é tenant-scoped.
- sem tenant resolvido, a tela não lista divergências globais.
- não há mutação financeira.

## Wave GC — Payments Admin Finance Surface Closure Review
- decisão:
  - **Go técnico para surface admin financeira mínima**.
- decisão complementar:
  - **No-Go para backoffice financeiro completo nesta abordagem**.

### Próximos temas maiores
- ledger financeiro persistido.
- workflow de resolução manual com auditoria.
- refund/estorno.
- conciliação por settlement/extrato de provider.

### Próxima abordagem recomendada
- **Payment Refund/Reversal Foundation Review**
- motivo:
  - com divergências visíveis para admin, o próximo tema financeiro realmente transacional é definir estorno/reversão sem quebrar pedidos, estoque e ledger futuro.

## Wave GD — Payment Refund/Reversal Foundation Review
- a revisão encontrou que o sistema já possui reversões operacionais parciais:
  - cancelamento de pedido em `orders`
  - recuperação de estoque reservado quando pedido pago é cancelado antes do envio
  - reversão de redemption de cupom no cancelamento
- lacuna:
  - não existe refund financeiro real no provider
  - não existe ledger de refund
  - não existe política de refund parcial/total

### Decisão
- não implementar estorno transacional nesta abordagem.
- criar apenas uma auditoria read-only de elegibilidade para refund/reversal.
- manter refund real como trilha maior separada.

## Wave GE — Payment Refund/Reversal Readiness Execution
- foi criado um auditor operacional read-only de candidatos a refund/reversal.

### Escopo executado
- service:
  - `payments.application.refund_reversal_queries`
- command:
  - `list_payment_refund_candidates`
- filtros:
  - `--tenant-id`
  - `--ready-only`
  - `--limit`
- bloqueios iniciais:
  - `order-not-paid`
  - `order-already-canceled`
  - `order-already-shipped`
  - `inventory-finalized`
  - `paid-attempt-missing`
  - `external-reference-missing`

### Leitura operacional
- um candidato `ready` significa apenas que há base mínima para iniciar análise de refund.
- o comando não chama provider.
- o comando não altera pedido, tentativa, estoque ou cupom.
- pedido enviado/finalizado fica bloqueado para evitar reversão financeira ingênua.

## Wave GF — Payment Refund/Reversal Closure Review
- decisão:
  - **Go técnico para readiness read-only de refund/reversal**.
- decisão complementar:
  - **No-Go para estorno financeiro real nesta abordagem**.

### Próximos temas maiores
- modelo/ledger de refund.
- chamada real ao provider para estorno.
- política de refund parcial vs total.
- integração com cancelamento, estoque, cupom e notificações.
- surface admin de aprovação/execução com auditoria forte.

### Próxima abordagem recomendada
- **Refund Ledger Contract Review**
- motivo:
  - antes de chamar provider, o sistema precisa de um ledger persistido e idempotente para registrar intenção, execução, falha e reversão de refund.

## Wave GG — Refund Ledger Contract Review
- a revisão confirmou que o readiness read-only já identifica candidatos, mas ainda não havia trilha persistida para intenção de refund.
- contrato mínimo escolhido:
  - entidade tenant-scoped `PaymentRefund`
  - vínculo com `Order`
  - vínculo opcional com `PaymentAttempt` pago
  - chave idempotente por tenant
  - valor, moeda, provider, referência externa, motivo, blockers e metadata
  - estados preparados para `requested`, `blocked`, `processing`, `succeeded`, `failed` e `reversed`

### Decisão
- registrar intenção/bloqueio de refund antes de qualquer chamada real ao provider.
- manter o ledger sem mutar pedido, tentativa, estoque, cupom ou notificações nesta wave.
- usar idempotência por `(tenant, idempotency_key)` como trava mínima contra duplicidade operacional.

## Wave GH — Refund Ledger Contract Execution
- foi criado o ledger persistido mínimo de refund.

### Escopo executado
- model:
  - `PaymentRefund`
- migration:
  - `payments.0004_paymentrefund`
- service:
  - `payments.application.refund_ledger_commands`
- command:
  - `request_payment_refund_intent`
- testes:
  - criação de intenção `requested`
  - idempotência por tenant
  - bloqueio de pedido enviado
  - proteção contra tenant ausente, chave ausente e cross-tenant
  - saída operacional do comando

### Garantias
- não há chamada de provider.
- não há alteração de `Order`.
- não há alteração de `PaymentAttempt`.
- não há alteração de estoque ou cupom.
- blockers geram ledger `blocked` quando o pedido existe, preservando evidência operacional.

## Wave GI — Refund Ledger Closure Review
- decisão:
  - **Go técnico para ledger mínimo de refund**.
- decisão complementar:
  - **No-Go para refund financeiro real nesta abordagem**.

### Próxima abordagem recomendada
- **Refund Provider Execution Review**
- motivo:
  - agora existe trilha idempotente; a próxima decisão é se já vale integrar execução real ao provider ou antes criar surface admin de aprovação.

## Wave GJ — Refund Provider Execution Review
- a revisão comparou o ledger atual com a integração real existente de provider.
- achados:
  - `PagarmeProviderAdapter` ainda cobre apenas criação de intenção/link de pagamento.
  - não existe contrato de refund no adapter.
  - não existe surface admin explícita para aprovar execução financeira.
  - não existe política de refund parcial, total, múltiplo ou pós-envio.
  - `payment.refunded` ainda é evento documentado, mas não deve ser emitido antes de execução real confirmada.

### Decisão
- **No-Go para execução direta de refund no provider agora**.
- **Go para preparar uma surface admin de aprovação/triagem antes da chamada externa**.

### Critérios mínimos antes de provider real
- refund precisa nascer no ledger como `requested`.
- operador precisa ver blockers, valor, pedido, tentativa e referência externa antes de aprovar.
- aprovação deve ser tenant-scoped e idempotente.
- execução real deve transicionar `requested → processing → succeeded|failed`.
- somente `succeeded` pode emitir/representar `payment.refunded`.
- efeitos em `orders`, estoque, cupom e notifications devem ser explícitos e posteriores à confirmação do provider.

## Wave GK — Refund Provider Execution Closure Review
- decisão:
  - **Go técnico para surface admin de refund antes do provider**.
- decisão complementar:
  - **No-Go para CLI/API chamar provider diretamente nesta fase**.

### Próxima abordagem recomendada
- **Refund Admin Approval Surface Review**
- motivo:
  - a próxima peça segura é dar visibilidade e aprovação explícita ao ledger `PaymentRefund`, sem ainda movimentar dinheiro.

## Wave GL — Refund Admin Approval Surface Review
- a revisão avaliou a surface admin financeira existente e o ledger `PaymentRefund`.
- ponto de partida:
  - `/ops/payments/finance/` já mostra divergências financeiras read-only.
  - `PaymentRefund` já guarda intenção/bloqueio idempotente.
  - ainda não há tela dedicada para triagem/aprovação de refund.

### Surface mínima recomendada
- rota:
  - `/ops/payments/refunds/`
- namespace:
  - `payments_ops:admin-refunds`
- escopo inicial:
  - listagem tenant-scoped de `PaymentRefund`
  - filtros simples por `status`
  - colunas:
    - status
    - pedido
    - valor
    - tentativa/referência externa
    - blockers
    - chave idempotente
  - ações:
    - detalhe read-only do refund
    - sem botão de executar provider nesta primeira surface

### Regras de segurança
- sem tenant resolvido, a lista deve ficar vazia.
- `blocked` deve ser exibido como estado operacional explícito, não como erro silencioso.
- `requested` significa “pode entrar em aprovação”, não “estorno autorizado automaticamente”.
- a tela não deve alterar `Order`, `PaymentAttempt`, estoque, cupom ou notificações.
- aprovação real deve ser uma wave separada, com permissão/CSRF/auditoria e transição explícita no ledger.

### Decisão
- **Go para implementar uma surface admin read-only de refunds antes de aprovação mutável**.
- **No-Go para botão de approve/execute provider nesta mesma etapa**.

## Wave GM — Refund Admin Approval Surface Closure Review
- decisão:
  - a primeira surface deve ser **read-only**, apesar do nome “approval”.
- motivo:
  - o operador precisa enxergar o ledger antes de aprovar movimentação financeira.
  - misturar visibilidade, aprovação e provider call no mesmo passo aumentaria risco operacional.

### Próxima abordagem recomendada
- **Refund Admin Read-Only Surface Execution**
- motivo:
  - criar `/ops/payments/refunds/` com listagem tenant-scoped do ledger e preparar a base visual para aprovação futura.

## Wave GN — Refund Admin Read-Only Surface Execution
- foi criada a primeira surface admin para triagem de refunds.

### Escopo executado
- rota:
  - `/ops/payments/refunds/`
- namespace:
  - `payments_ops:admin-refunds`
- query service:
  - `payments.application.refund_ledger_queries`
- view:
  - `AdminPaymentRefundsView`
- dashboard merchant ops:
  - adiciona atalho `Refunds`
- filtros:
  - status do ledger
- colunas:
  - status
  - pedido
  - valor
  - tentativa/referência externa
  - blockers
  - idempotency key

### Garantias
- a listagem é tenant-scoped.
- sem tenant resolvido, a tela não lista refunds globais.
- a tela é read-only.
- não há botão de aprovar, executar provider, alterar pedido, alterar tentativa, estoque, cupom ou notificações.

## Wave GO — Refund Admin Read-Only Surface Closure Review
- decisão:
  - **Go técnico para surface read-only de refunds**.
- decisão complementar:
  - **No-Go para aprovação/execução de refund nesta abordagem**.

### Próxima abordagem recomendada
- **Refund Approval Command Contract Review**
- motivo:
  - agora existe ledger e visibilidade admin; o próximo passo seguro é desenhar o command de aprovação que transiciona `requested` sem ainda chamar provider real.

## Wave GP — Refund Approval Command Contract Review
- a revisão confirmou que já existem:
  - ledger `PaymentRefund`
  - intenção/bloqueio idempotente
  - surface admin read-only
  - boundary documentada para não chamar provider diretamente
- lacuna:
  - não existe command explícito para aprovar um refund e preparar execução futura.

### Contrato mínimo recomendado
- service:
  - `payments.application.refund_approval_commands`
- método:
  - `approve_refund(...)`
- entrada:
  - `tenant_id`
  - `refund_key`
  - `actor_label`
  - `approval_note`
- pré-condições:
  - tenant resolvido
  - refund pertence ao tenant
  - status atual é `requested`
  - sem blockers
  - possui `payment_attempt`
  - possui `external_reference`
  - amount maior que zero
- transição:
  - `requested → processing`
- metadata:
  - `approved_by`
  - `approved_at`
  - `approval_note`
  - `approval_contract_version=refund-approval-v1`
  - `provider_call=not-executed`
- retornos:
  - `refund-approval-ready`
  - `refund-approval-blocked`
  - `refund-approval-unavailable`

### Fora do escopo
- não chamar provider.
- não marcar `succeeded`.
- não emitir `payment.refunded`.
- não alterar `Order`, `PaymentAttempt`, estoque, cupom ou notifications.
- não aprovar refunds `blocked`, `failed`, `succeeded`, `reversed` ou já `processing`.

## Wave GQ — Refund Approval Command Contract Closure Review
- decisão:
  - **Go técnico para command de aprovação interna do ledger**.
- decisão complementar:
  - **No-Go para provider execution dentro do command de aprovação**.

### Próxima abordagem recomendada
- **Refund Approval Command Execution**
- motivo:
  - implementar o command que faz apenas a transição auditável `requested → processing`, preparando uma wave posterior de provider adapter.

## Wave GR — Refund Approval Command Execution
- foi implementado o command service de aprovação interna de refund.

### Escopo executado
- service:
  - `payments.application.refund_approval_commands`
- método:
  - `approve_refund(...)`
- transição:
  - `requested → processing`
- metadados:
  - `approved_by`
  - `approved_at`
  - `approval_note`
  - `approval_contract_version`
  - `provider_call=not-executed`
- bloqueios:
  - tenant/refund ausente
  - refund fora do tenant
  - status diferente de `requested`
  - blockers existentes
  - ator ausente
  - tentativa paga ausente
  - referência externa ausente
  - valor inválido

### Garantias
- não há chamada ao provider.
- não há emissão de `payment.refunded`.
- não há alteração de pedido, tentativa, estoque, cupom ou notificações.
- reprovações preservam o status atual e registram `approval_blockers` na metadata do ledger.

## Wave GS — Refund Approval Command Closure Review
- decisão:
  - **Go técnico para aprovação interna do ledger**.
- decisão complementar:
  - **No-Go para execução financeira real ainda**.

### Próxima abordagem recomendada
- **Refund Approval Admin Action Review**
- motivo:
  - agora o command existe; o próximo passo seguro é decidir como a surface admin poderá acionar essa transição sem chamar provider.

## Wave GT — Refund Approval Admin Action Review
- a revisão avaliou a surface `/ops/payments/refunds/` e o command `approve_refund(...)`.
- decisão de produto/técnica:
  - expor uma action admin mínima para aprovação interna do ledger.
  - manter essa action como POST tenant-scoped.
  - continuar sem chamada ao provider.

### Contrato recomendado
- rota:
  - `/ops/payments/refunds/<refund_key>/approve/`
- namespace:
  - `payments_ops:admin-refund-approve`
- método:
  - `POST`
- entrada:
  - `refund_key` pela URL
  - `approval_note` opcional no body
  - `actor_label` derivado do usuário/request quando possível, com fallback operacional explícito
- comportamento:
  - resolve `tenant_id` da request
  - chama `payment_refund_approval_commands.approve_refund(...)`
  - redireciona de volta para `/ops/payments/refunds/`
  - adiciona feedback simples de sucesso/bloqueio/indisponibilidade quando a base de messages estiver disponível

### UI mínima
- mostrar ação apenas para refunds `requested`.
- texto sugerido:
  - `Aprovar internamente`
- nota/copy:
  - “Esta ação prepara execução futura e não chama o provider.”
- manter estados `blocked`, `processing`, `succeeded`, `failed` e `reversed` sem ação de aprovação.

### Fora do escopo
- não chamar provider.
- não criar botão de “estornar”.
- não alterar `Order`, `PaymentAttempt`, estoque, cupom ou notifications.
- não emitir `payment.refunded`.
- não criar fluxo completo de permissões avançadas; a action deve respeitar o escopo ops atual e permanecer tenant-scoped.

## Wave GU — Refund Approval Admin Action Closure Review
- decisão:
  - **Go técnico para action admin de aprovação interna**.
- decisão complementar:
  - **No-Go para provider execution e efeitos externos nessa action**.

### Próxima abordagem recomendada
- **Refund Approval Admin Action Execution**
- motivo:
  - conectar a surface read-only ao command já testado, adicionando uma action POST segura para `requested → processing`.

## Wave GV — Refund Approval Admin Action Execution
- foi conectada a surface admin de refunds ao command de aprovação interna.

### Escopo executado
- rota:
  - `POST /ops/payments/refunds/<refund_key>/approve/`
- namespace:
  - `payments_ops:admin-refund-approve`
- view:
  - `AdminPaymentRefundApproveView`
- UI:
  - coluna `Ação` na lista de refunds
  - botão `Aprovar internamente` apenas para status `requested`
  - copy explícita `Não executa estorno`

### Comportamento
- resolve tenant pela request.
- deriva actor label do usuário quando possível, com fallback `Ops interno`.
- delega para `payment_refund_approval_commands.approve_refund(...)`.
- redireciona para `/ops/payments/refunds/`.

### Garantias
- a view não decide blockers.
- a view não chama provider.
- a view não altera pedido, tentativa, estoque, cupom ou notifications.
- cross-tenant não altera o refund.

## Wave GW — Refund Approval Admin Action Closure Review
- decisão:
  - **Go técnico para action admin de aprovação interna**.
- decisão complementar:
  - **No-Go para execução real de refund nesta abordagem**.

### Próxima abordagem recomendada
- **Refund Provider Adapter Contract Review**
- motivo:
  - agora há ledger, surface, command e action admin; o próximo passo natural é desenhar o contrato de adapter real de refund sem ainda acoplar efeitos em outros módulos.

## Wave GX — Refund Provider Adapter Contract Review
- a revisão comparou o adapter atual de pagamentos com o novo fluxo de refund.
- estado atual:
  - `PagarmeProviderAdapter` cria link/intenção de pagamento.
  - `PaymentRefund` já pode chegar a `processing` por aprovação interna.
  - ainda não existe contrato externo de refund.

### Contrato mínimo recomendado
- infrastructure:
  - `RefundProviderContract`
  - `RefundProviderResponse`
- adapter:
  - `create_refund(contract=...)`
- campos do contrato:
  - `tenant_id`
  - `refund_key`
  - `idempotency_key`
  - `provider_code`
  - `external_reference`
  - `amount`
  - `currency_code`
  - `reason_code`
  - `metadata`
- campos da resposta:
  - `provider_code`
  - `provider_refund_reference`
  - `status`
  - `payload_snapshot`

### Semântica de status
- `accepted`:
  - provider aceitou a solicitação, mas confirmação final ainda pode depender de webhook/consulta posterior.
- `succeeded`:
  - provider confirmou refund concluído.
- `failed`:
  - provider recusou ou falhou a execução.

### Regras
- adapter não altera `PaymentRefund` diretamente.
- adapter não altera pedido, tentativa, estoque, cupom ou notifications.
- command futuro de execução será responsável por:
  - carregar `PaymentRefund` `processing`
  - construir `RefundProviderContract`
  - chamar adapter
  - registrar resposta no ledger
  - decidir transição `processing → succeeded|failed`
- somente `succeeded` pode preparar emissão de `payment.refunded`.

### Pagar.me
- o endpoint exato de refund deve ser confirmado antes da execução.
- a primeira implementação real deve exigir:
  - secret key configurada
  - `external_reference`
  - amount em centavos
  - chave idempotente
- até esse contrato ser implementado, não há chamada externa de refund.

## Wave GY — Refund Provider Adapter Contract Closure Review
- decisão:
  - **Go técnico para contrato de adapter de refund**.
- decisão complementar:
  - **No-Go para chamada real ao provider nesta abordagem**.

### Próxima abordagem recomendada
- **Refund Provider Adapter Skeleton Execution**
- motivo:
  - criar dataclasses e adapter lite/real skeleton com testes de contrato, ainda sem disparar refund real em produção.

## Wave GZ — Refund Provider Adapter Skeleton Execution
- foi criado o esqueleto de adapter de refund.

### Escopo executado
- dataclasses:
  - `RefundProviderContract`
  - `RefundProviderResponse`
- adapter lite:
  - `ProviderAdapterLite.create_refund(...)`
  - retorna `status=accepted`
  - marca `provider_call=lite`
- adapter Pagar.me:
  - `PagarmeProviderAdapter.create_refund(...)`
  - falha explicitamente com `pagarme-refund-adapter-not-implemented`

### Garantias
- nenhuma chamada real ao provider é feita.
- nenhum command de execução foi conectado ainda.
- nenhum `PaymentRefund` é alterado por esse skeleton.
- nenhum evento `payment.refunded` é emitido.

## Wave HA — Refund Provider Adapter Skeleton Closure Review
- decisão:
  - **Go técnico para skeleton de adapter de refund**.
- decisão complementar:
  - **No-Go para execução real até existir command de execução e endpoint confirmado**.

### Próxima abordagem recomendada
- **Refund Execution Command Contract Review**
- motivo:
  - o adapter skeleton existe; o próximo passo seguro é desenhar o command que consumirá `PaymentRefund.processing` e registrará resposta externa sem efeitos em outros módulos.

## Wave HB — Refund Execution Command Contract Review
- a revisão confirmou que já existem:
  - ledger `PaymentRefund`
  - aprovação interna `requested → processing`
  - action admin para aprovação interna
  - skeleton de adapter de refund
- lacuna:
  - ainda não há command que consuma refunds `processing` e registre a resposta do adapter.

### Contrato mínimo recomendado
- service:
  - `payments.application.refund_execution_commands`
- método:
  - `execute_refund(...)`
- entrada:
  - `tenant_id`
  - `refund_key`
- pré-condições:
  - tenant resolvido
  - refund pertence ao tenant
  - status atual é `processing`
  - `provider_refund_reference` ainda ausente
  - possui `payment_attempt`
  - possui `external_reference`
  - amount maior que zero
  - sem blockers
- contrato externo:
  - construir `RefundProviderContract` a partir de `PaymentRefund`
  - chamar `get_provider_adapter(...).create_refund(contract=...)`
- transições:
  - resposta `accepted`:
    - manter status `processing`
    - salvar `provider_refund_reference`
    - salvar `provider_refund.status=accepted` na metadata
  - resposta `succeeded`:
    - `processing → succeeded`
    - preencher `completed_at`
    - salvar referência e payload
  - resposta `failed` ou erro do adapter:
    - `processing → failed`
    - preencher `failed_at`
    - salvar reason/payload

### Fora do escopo
- não emitir `payment.refunded` nesta primeira execução.
- não alterar `Order`, `PaymentAttempt`, estoque, cupom ou notifications.
- não criar retry automático.
- não tentar Pagar.me real enquanto `PagarmeProviderAdapter.create_refund(...)` estiver explicitamente não implementado.

## Wave HC — Refund Execution Command Contract Closure Review
- decisão:
  - **Go técnico para command de execução do ledger contra adapter skeleton**.
- decisão complementar:
  - **No-Go para efeitos cross-module e evento `payment.refunded` nessa etapa**.

### Próxima abordagem recomendada
- **Refund Execution Command Skeleton Execution**
- motivo:
  - implementar `execute_refund(...)` consumindo `processing`, usando adapter lite/skeleton e registrando resposta no ledger sem efeitos externos.

## Wave HD — Refund Execution Command Skeleton Execution
- foi implementado o command skeleton de execução de refund.

### Escopo executado
- service:
  - `payments.application.refund_execution_commands`
- método:
  - `execute_refund(...)`
- entrada:
  - `tenant_id`
  - `refund_key`
- consumo:
  - apenas `PaymentRefund.status=processing`
- integração:
  - constrói `RefundProviderContract`
  - chama `get_provider_adapter(...).create_refund(...)`
  - registra resposta em `metadata.provider_refund`

### Semântica implementada
- `accepted`:
  - mantém `processing`
  - grava `provider_refund_reference`
- `succeeded`:
  - transiciona para `succeeded`
  - grava `completed_at`
- `failed` ou erro do adapter:
  - transiciona para `failed`
  - grava `failed_at`
- blockers:
  - preservam status atual
  - gravam `execution_blockers`

### Garantias
- não emite `payment.refunded`.
- não altera pedido, tentativa, estoque, cupom ou notifications.
- cross-tenant retorna indisponível sem alterar o ledger.

## Wave HE — Refund Execution Command Skeleton Closure Review
- decisão:
  - **Go técnico para execution command skeleton**.
- decisão complementar:
  - **No-Go para efeitos cross-module e provider real Pagar.me**.

### Próxima abordagem recomendada
- **Refund Provider Real Endpoint Review**
- motivo:
  - agora existe pipeline interno até o adapter; antes de chamar Pagar.me real, precisamos confirmar endpoint, payload, idempotência e estratégia de confirmação.

## Wave HF — Refund Provider Real Endpoint Review
- a revisão consultou a documentação oficial atual da API Reference V5 do Pagar.me.
- endpoint oficial encontrado:
  - `DELETE https://api.pagar.me/core/v5/charges/{charge_id}`
- semântica documentada:
  - cancelar cobrança.
  - `charge_id` é obrigatório.
  - `amount` é opcional e, se ausente, considera o valor total da cobrança.
  - `bank_account` é usado para estorno de boleto e pode ser obrigatório nesse caso.
- autenticação:
  - Basic Auth com chave secreta, coerente com o adapter atual de criação de payment link.

### Mapeamento para o Hubx
- `PaymentRefund.external_reference` deve ser tratado como `charge_id`.
- `PaymentRefund.amount` deve ser enviado em centavos quando houver refund parcial.
- `PaymentRefund.idempotency_key` deve continuar sendo chave interna do ledger.
- `PaymentRefund.provider_refund_reference` deve ser preenchido a partir da resposta quando o provider devolver identificador suficiente; caso contrário, usar fallback rastreável derivado de `charge_id/refund_key` apenas como referência operacional.

### Riscos
- o endpoint se chama “cancelar cobrança”, mas pode representar estorno dependendo do método/status da cobrança.
- boleto pode exigir `bank_account`, que o ledger atual ainda não captura.
- a resposta `200` precisa ser inspecionada em sandbox antes de decidir se representa `accepted` ou `succeeded`.
- não há confirmação no código atual de que `external_reference` sempre contém `charge_id` válido para todos os métodos.

### Decisão
- **Go para preparar o adapter Pagar.me real em modo conservador**.
- **No-Go para ativar execução real em produção sem sandbox contract test/manual validation**.

### Próxima implementação segura
- implementar `PagarmeProviderAdapter.create_refund(...)` usando:
  - `DELETE /charges/{charge_id}`
  - payload com `amount` em centavos
  - sem suporte inicial a boleto com `bank_account`
  - erro explícito se `external_reference` ausente
  - status inicial `accepted` para respostas 2xx até validarmos a semântica real no sandbox

## Wave HG — Refund Provider Real Endpoint Closure Review
- decisão:
  - **Go técnico para adapter real conservador em sandbox**.
- decisão complementar:
  - **No-Go para rollout de produção ou efeitos cross-module**.

### Próxima abordagem recomendada
- **Refund Pagar.me Adapter Sandbox Execution**
- motivo:
  - implementar o endpoint real no adapter com testes mockados, mantendo o execution command já existente e sem habilitar produção.

## Wave HH — Refund Pagar.me Adapter Sandbox Execution
- foi implementado o endpoint real conservador de refund no adapter Pagar.me.

### Escopo executado
- adapter:
  - `PagarmeProviderAdapter.create_refund(...)`
- endpoint:
  - `DELETE /charges/{charge_id}`
- autenticação:
  - Basic Auth com `PAGARME_SECRET_KEY`
- payload:
  - `amount` em centavos quando maior que zero
- headers:
  - `Idempotency-Key` com `PaymentRefund.idempotency_key`

### Semântica
- resposta 2xx é registrada como `accepted`.
- `provider_refund_reference` usa `id`, `code` ou `charge_id` da resposta.
- se o provider não devolver referência, usa fallback rastreável com `charge_id/refund_key`.

### Bloqueios explícitos
- sem secret key:
  - `pagarme-secret-key-missing`
- sem charge id:
  - `pagarme-refund-charge-id-missing`
- falha de rede:
  - `pagarme-network-unavailable`
- JSON inválido:
  - `pagarme-invalid-json-response`

### Garantias
- testes são mockados; não há chamada real durante a suíte.
- boleto com `bank_account` continua fora do escopo.
- production rollout continua bloqueado por decisão operacional.
- nenhum efeito cross-module foi adicionado.

## Wave HI — Refund Pagar.me Adapter Sandbox Closure Review
- decisão:
  - **Go técnico para adapter Pagar.me sandbox/mockado**.
- decisão complementar:
  - **No-Go para ativação real sem validação sandbox manual/contract test com credenciais reais**.

### Próxima abordagem recomendada
- **Refund Sandbox Validation Command Review**
- motivo:
  - antes de rollout real, criar um comando de validação controlada que execute um refund sandbox específico e registre resultado sem propagar efeitos.

## Wave HJ — Refund Sandbox Validation Command Review
- a revisão avaliou os comandos sandbox existentes de payments:
  - `payment_sandbox_readiness`
  - `payment_sandbox_validate_webhook`
- lacuna:
  - não existe comando controlado para validar uma execução real de refund sandbox a partir de um `PaymentRefund.processing`.

### Contrato recomendado
- command:
  - `payment_sandbox_validate_refund`
- argumentos obrigatórios:
  - `--tenant-id`
  - `--refund-key`
- argumentos opcionais:
  - `--dry-run`
  - `--require-processing`
- comportamento:
  - carrega `PaymentRefund` tenant-scoped.
  - valida que o status é `processing`.
  - imprime dados críticos antes de executar:
    - tenant
    - order number
    - refund key
    - amount
    - external reference
    - idempotency key
  - com `--dry-run`, não chama provider/adapter.
  - sem `--dry-run`, chama `payment_refund_execution_commands.execute_refund(...)`.
  - imprime resultado e status final do ledger.

### Segurança
- sem tenant não executa.
- cross-tenant não encontra registro.
- status diferente de `processing` bloqueia.
- comando não altera `Order`, `PaymentAttempt`, estoque, cupom ou notifications.
- comando não emite `payment.refunded`.
- comando deve ser tratado como ferramenta de sandbox/ops controlada, não como feature de produção.

### Decisão
- **Go para implementar comando de validação sandbox de refund**.
- **No-Go para expor esse comando como ação admin ou fluxo customer-facing**.

## Wave HK — Refund Sandbox Validation Command Closure Review
- decisão:
  - **Go técnico para command sandbox de validação**.
- decisão complementar:
  - **No-Go para rollout real de refund automático**.

### Próxima abordagem recomendada
- **Refund Sandbox Validation Command Execution**
- motivo:
  - implementar `payment_sandbox_validate_refund` com `--dry-run`, validação tenant-scoped e integração controlada com `execute_refund(...)`.

## Wave HL — Refund Sandbox Validation Command Execution
- foi implementado o comando operacional de validação sandbox de refund.

### Escopo executado
- command:
  - `payment_sandbox_validate_refund`
- argumentos:
  - `--tenant-id`
  - `--refund-key`
  - `--dry-run`
  - `--require-processing`
- comportamento:
  - carrega `PaymentRefund` por tenant e `refund_key`
  - imprime candidato e dados críticos
  - bloqueia status diferente de `processing`
  - em `--dry-run`, não chama adapter/provider
  - sem `--dry-run`, delega para `execute_refund(...)`

### Garantias
- tenant-scoped.
- sem bulk execution.
- sem evento `payment.refunded`.
- sem efeito em pedido, tentativa, estoque, cupum ou notifications.
- útil para sandbox/ops controlado, não como feature de produção.

## Wave HM — Refund Sandbox Validation Command Closure Review
- decisão:
  - **Go técnico para validação sandbox controlada**.
- decisão complementar:
  - **No-Go para rollout automático de refund real**.

### Próxima abordagem recomendada
- **Refund Provider Sandbox Runbook Review**
- motivo:
  - agora há comando; o próximo passo é consolidar a sequência operacional segura para validar um refund sandbox real ponta a ponta.

## Wave HN — Refund Provider Sandbox Runbook Review
- a revisão consolidou o runbook operacional de refund sandbox como sequência controlada, não como rollout automático.
- o fluxo recomendado agora exige:
  - tenant controlado de teste
  - credenciais sandbox
  - charge sandbox paga com `external_reference`
  - intenção idempotente registrada no ledger
  - aprovação interna antes de execução
  - `payment_sandbox_validate_refund --dry-run`
  - execução explícita sem `--dry-run` apenas depois de readiness positivo
- foram documentados critérios de No-Go:
  - tenant ausente ou incorreto
  - credenciais de produção
  - refund fora de `processing`
  - ausência de `external_reference`
  - idempotência não rastreável
  - refund de boleto com dados bancários ainda não modelados
  - resposta do provider sem referência auditável
- foram documentados critérios de Go pós-sandbox:
  - ledger auditável antes/depois da chamada
  - `metadata.provider_refund` preservado
  - nenhuma propagação para order, estoque, cupom ou notification
  - `payment.refunded` ainda bloqueado até confirmação externa concluída
- ajuste importante:
  - o runbook deixou de tratar Pagar.me como “não implementado”
  - a redação agora diferencia adapter lite `accepted` de adapter Pagar.me sandbox-first conservador.

## Wave HO — Refund Provider Sandbox Runbook Closure Review
- decisão:
  - **Go técnico para runbook sandbox de refund**.
- decisão complementar:
  - **No-Go para produção real sem execução sandbox observada e conciliação financeira revisada**.

### Próxima abordagem recomendada
- **Refund Provider Production Gate Review**
- motivo:
  - com adapter, command e runbook documentados, o próximo passo seguro é transformar evidências sandbox em critérios objetivos para habilitar ou negar produção.

## Wave HP — Refund Provider Production Gate Review
- a revisão confirmou que refund provider ainda não deve ser tratado como produção liberada por padrão.
- estado atual:
  - ledger tenant-scoped existe
  - aprovação interna `requested → processing` existe
  - adapter Pagar.me sandbox-first existe
  - command controlado `payment_sandbox_validate_refund` existe
  - runbook sandbox ponta a ponta existe
- lacuna antes de produção:
  - ainda não há evidência registrada de execução sandbox real observada
  - ainda não há confirmação operacional da semântica final do provider para `accepted` vs `succeeded`
  - boleto com `bank_account` continua fora do modelo
  - `payment.refunded` continua evento reservado para refund concluído confirmado

### Gate recomendado
- produção só pode avançar com evidência mínima:
  - `tenant-id` sandbox usado no dry-run e execução
  - `refund-key`
  - `idempotency_key`
  - `external_reference`
  - saída do dry-run com `result=ready`
  - saída da execução com status final do ledger
  - payload preservado em `metadata.provider_refund`
  - conciliação financeira revisada depois da execução
- produção inicial, se habilitada futuramente, deve ser limitada a:
  - execução manual por refund já aprovado internamente
  - charge com referência externa conhecida
  - método sem dados bancários adicionais
  - observação pós-execução antes de eventos ou efeitos cross-module

### No-Go explícito
- execução em lote.
- chamada direta pelo botão admin sem confirmação operacional separada.
- refund sem `external_reference`.
- boleto ou método que exija `bank_account`.
- emissão automática de `payment.refunded`.
- ajuste automático de pedido, estoque, cupom, notification ou tentativa financeira.
- ausência de conciliação financeira depois da execução.

## Wave HQ — Refund Provider Production Gate Closure Review
- decisão:
  - **No-Go para liberar refund provider em produção agora**.
- decisão complementar:
  - **Go técnico para gate documental de produção controlada**.
- motivo:
  - o sistema tem estrutura suficiente para validar sandbox e preparar produção manual limitada, mas ainda não tem evidência operacional real suficiente para movimentar dinheiro em produção.

### Próxima abordagem recomendada
- **Refund Sandbox Evidence Capture Review**
- motivo:
  - antes de qualquer execução real em produção, o próximo ganho é padronizar como registrar evidências sandbox e anexá-las ao ledger/ops sem depender de memória operacional solta.

## Wave HR — Refund Sandbox Evidence Capture Review
- a revisão confirmou que `PaymentRefund.metadata` já é suficiente para receber evidência operacional sem migration imediata.
- decisão:
  - evidência sandbox deve viver em envelope próprio `metadata.sandbox_evidence`
  - `metadata.provider_refund` continua sendo a resposta técnica do adapter/provider
  - captura de evidência não deve alterar status do ledger
  - captura não deve emitir evento nem propagar efeitos cross-module

### Envelope recomendado
- `sandbox_evidence.captured_at`
- `sandbox_evidence.captured_by`
- `sandbox_evidence.environment`
- `sandbox_evidence.tenant_id`
- `sandbox_evidence.refund_key`
- `sandbox_evidence.dry_run_output`
- `sandbox_evidence.execution_output`
- `sandbox_evidence.provider_dashboard_reference`
- `sandbox_evidence.reconciliation_reference`
- `sandbox_evidence.decision`
- `sandbox_evidence.notes`

### Guardrails
- não armazenar secret keys, tokens, Authorization headers, dados de cartão ou dados bancários sensíveis.
- não sobrescrever `provider_refund`.
- não aceitar evidência sem tenant/refund explícitos.
- `decision=go-production-limited` exige sandbox executado, provider revisado e conciliação conferida.
- ausência de `sandbox_evidence` mantém o gate de produção fechado.

## Wave HS — Refund Sandbox Evidence Capture Closure Review
- decisão:
  - **Go técnico para contrato documental de evidência sandbox em `PaymentRefund.metadata.sandbox_evidence`**.
- decisão complementar:
  - **No-Go para criar modelo novo ou automação de produção nesta etapa**.
- motivo:
  - o sistema precisa primeiro padronizar a evidência operacional antes de criar command/action de captura ou liberar produção.

### Próxima abordagem recomendada
- **Refund Sandbox Evidence Capture Command Review**
- motivo:
  - com o envelope definido, o próximo passo natural é decidir se vale criar um command explícito para anexar evidência ao ledger de forma tenant-scoped e auditável.

## Wave HT — Refund Sandbox Evidence Capture Command Review
- a revisão concluiu que a captura deve ser um command separado de `payment_sandbox_validate_refund`.
- motivo:
  - validação sandbox pode chamar provider
  - captura de evidência deve apenas anexar observação operacional
  - misturar os dois fluxos aumentaria risco de execução acidental

### Command recomendado
- nome sugerido:
  - `capture_payment_refund_sandbox_evidence`
- argumentos obrigatórios:
  - `--tenant-id`
  - `--refund-key`
  - `--captured-by`
  - `--decision`
- argumentos opcionais:
  - `--environment`
  - `--dry-run-output`
  - `--execution-output`
  - `--provider-dashboard-reference`
  - `--reconciliation-reference`
  - `--notes`

### Regras
- carregar `PaymentRefund` por `tenant_id + refund_key`.
- escrever somente em `metadata.sandbox_evidence`.
- preservar `metadata.provider_refund`.
- não alterar status, referência do provider ou timestamps finais.
- bloquear secrets, tokens, Authorization headers, dados de cartão e dados bancários sensíveis.
- aceitar decisões explícitas:
  - `no-go`
  - `sandbox-observed`
  - `go-production-limited`
- exigir `provider_refund`, referência de dashboard e referência de conciliação para `go-production-limited`.

### Fora do escopo
- chamar provider.
- executar refund.
- aprovar refund.
- emitir `payment.refunded`.
- alterar pedido, estoque, cupom, notification ou tentativa financeira.

## Wave HU — Refund Sandbox Evidence Capture Command Closure Review
- decisão:
  - **Go técnico para implementar command separado de captura de evidência sandbox**.
- decisão complementar:
  - **No-Go para acoplar captura ao command de execução ou validação do provider**.
- motivo:
  - a captura precisa ser auditável, tenant-scoped e incapaz de movimentar dinheiro.

### Próxima abordagem recomendada
- **Refund Sandbox Evidence Capture Command Execution**
- motivo:
  - implementar o command com escrita limitada em `metadata.sandbox_evidence`, validação de campos sensíveis e testes de contrato.

## Wave HV — Refund Sandbox Evidence Capture Command Execution
- foi implementado o command operacional de captura de evidência sandbox.

### Escopo executado
- application service:
  - `payments.application.refund_sandbox_evidence_commands`
- command:
  - `capture_payment_refund_sandbox_evidence`
- escrita:
  - somente `PaymentRefund.metadata.sandbox_evidence`
- preservação:
  - mantém `metadata.provider_refund`
  - mantém `status`
  - mantém `provider_refund_reference`
  - mantém timestamps finais do ledger

### Contrato
- argumentos obrigatórios:
  - `--tenant-id`
  - `--refund-key`
  - `--captured-by`
  - `--decision`
- decisões permitidas:
  - `no-go`
  - `sandbox-observed`
  - `go-production-limited`
- argumentos opcionais:
  - `--environment`
  - `--dry-run-output`
  - `--execution-output`
  - `--provider-dashboard-reference`
  - `--reconciliation-reference`
  - `--notes`

### Guardrails implementados
- cross-tenant retorna indisponível.
- conteúdo com sinais de secret/token/header Authorization/cartão/dados bancários é bloqueado.
- `go-production-limited` exige `metadata.provider_refund`, referência do provider e referência de conciliação.
- command não chama provider.
- command não aprova nem executa refund.
- command não emite `payment.refunded`.
- command não altera pedido, estoque, cupom, notification ou tentativa financeira.

### Testes
- captura escreve metadata e preserva status/provider.
- captura é tenant-scoped.
- conteúdo sensível é bloqueado.
- gate limitado exige referências mínimas.

## Wave HW — Refund Sandbox Evidence Capture Command Closure Review
- decisão:
  - **Go técnico para captura auditável de evidência sandbox no ledger**.
- decisão complementar:
  - **No-Go para liberar produção de refund apenas por existir evidência capturada**.
- motivo:
  - a evidência agora pode ser registrada com segurança, mas produção ainda depende de revisão operacional e decisão explícita do gate.

### Próxima abordagem recomendada
- **Refund Provider Production Enablement Review**
- motivo:
  - com adapter, execução sandbox, runbook, gate e captura de evidência, a próxima revisão deve decidir se existe alguma mudança mínima aceitável para habilitar produção manual limitada — ou se a trilha deve encerrar em No-Go até evidência real externa.

## Wave HX — Refund Provider Production Enablement Review
- a revisão confirmou que a trilha técnica já possui:
  - ledger de refund tenant-scoped
  - aprovação interna
  - adapter Pagar.me sandbox-first
  - execution command
  - validation command sandbox
  - runbook
  - gate de produção
  - captura auditável de evidência sandbox
- a revisão também confirmou que ainda falta o insumo mais importante:
  - evidência real de sandbox externo executado e conciliado.

### Decisão de enablement
- **No-Go para produção ampla**.
- **No-Go para automação de refund**.
- **No-Go para self-service de lojista ou cliente**.
- **Go apenas para preparar uma futura produção manual limitada**, condicionada a evidência sandbox real.

### Produção manual limitada futura
- escopo máximo aceitável:
  - um tenant controlado por vez
  - um refund por execução
  - execução manual por `refund_key`
  - refunds já aprovados internamente e em `processing`
  - método de pagamento sem dados bancários adicionais
  - observação pós-execução antes de qualquer nova rodada
- pré-requisitos:
  - `metadata.sandbox_evidence.decision=go-production-limited`
  - `metadata.provider_refund` revisado
  - referência de dashboard do provider
  - referência de conciliação financeira
  - operador financeiro identificado

### O que não implementar agora
- feature flag ampla para produção.
- botão admin que execute refund real diretamente.
- retry automático.
- execução em lote.
- emissão automática de `payment.refunded`.
- efeitos automáticos em pedidos, estoque, cupom ou notifications.

## Wave HY — Refund Provider Production Enablement Closure Review
- decisão:
  - **No-Go final para habilitar produção real nesta abordagem sem evidência sandbox externa**.
- decisão complementar:
  - **Go técnico para encerrar a trilha de preparação de refund provider com produção manual limitada apenas como caminho futuro condicionado**.
- motivo:
  - o sistema agora está preparado para registrar e avaliar evidência, mas não deve movimentar dinheiro real enquanto essa evidência não existir fora dos testes mockados.

## Refund Provider Admin Execution
- `/ops/payments/refunds/` agora opera o ledger `PaymentRefund` em duas etapas explícitas:
  - `requested -> processing` por aprovação interna;
  - `processing -> provider` por `POST /ops/payments/refunds/<refund_key>/execute/`.
- writes exigem role tenant-scoped resolvida e permissão `payments.manage`; leitura continua protegida por `payments.view` no prefix gate.
- a execução chama `payments.application.refund_execution_commands.execute_refund(...)`, que monta `RefundProviderContract`, resolve o adapter por `payments.infrastructure.provider_adapters.get_provider_adapter(...)` e registra a resposta em `metadata.provider_refund`.
- `PagarmeProviderAdapter.create_refund(...)` usa o endpoint conservador de cancelamento/refund de charge já validado na trilha sandbox-first.
- `AsaasProviderAdapter.create_refund(...)` usa `POST /payments/{id}/refund`, enviando `value` quando há valor positivo e `description` com o motivo operacional.
- status do provider é normalizado de forma defensiva:
  - `succeeded` apenas para respostas explicitamente concluídas;
  - `failed` para respostas explicitamente recusadas;
  - `accepted` para respostas assíncronas, vazias ou ainda pendentes.
- a tabela admin mostra `provider_code` e `provider_refund_reference`, mantendo rastreabilidade operacional sem expor payload sensível.

### Escopo deliberado
- não emite `payment.refunded` automaticamente.
- não altera `Order`, `PaymentAttempt`, estoque, cupom, shipment ou notifications depois do refund.
- não tenta refund de boleto Asaas pelo endpoint async separado de bank slip neste corte.
- não libera automação em massa; toda execução é POST manual, tenant-scoped, idempotente pelo ledger e auditada.

### Próxima abordagem recomendada
- **Payments Refund/Reversal Track Closure Review**
- motivo:
  - a trilha já cobriu ledger, admin, aprovação, adapter, execução, sandbox, evidência e gate; o próximo passo natural é declarar o status final e listar bloqueios residuais para produção real.

## Wave HZ — Payments Refund/Reversal Track Closure Review
- a trilha de refund/reversal foi revisada de ponta a ponta.
- escopo construído:
  - auditoria de candidatos a refund/reversal
  - ledger tenant-scoped `PaymentRefund`
  - intenção idempotente de refund
  - surface admin read-only
  - aprovação interna `requested → processing`
  - adapter contract para refund
  - execution command contra adapter
  - endpoint Pagar.me sandbox-first conservador
  - command de validação sandbox por `refund_key`
  - runbook sandbox
  - gate de produção
  - captura auditável de evidência sandbox

### Readiness final
- **Go técnico para fundação interna de refund/reversal**.
- **Go técnico para suporte, auditoria, triagem e preparação sandbox**.
- **No-Go para produto financeiro de produção**.
- **No-Go para automação, self-service e execução em lote**.

### Bloqueios residuais
- falta evidência sandbox externa real.
- `accepted` ainda não deve ser tratado como refund concluído.
- boleto/dados bancários adicionais seguem fora do modelo.
- `payment.refunded` segue reservado para confirmação externa concluída.
- não há propagação segura definida para pedido, estoque, cupom ou notifications.
- não há retry/compensação automática.

### Critério para reabrir a trilha
- reabrir somente se houver:
  - evidência sandbox real capturada
  - demanda operacional de produção manual limitada
  - necessidade concreta de boleto/dados bancários
  - decisão explícita de emitir `payment.refunded` após confirmação externa

## Wave IA — Payments Refund/Reversal Track Final Decision
- decisão:
  - **trilha encerrada como fundação técnica**.
- decisão complementar:
  - **produção real permanece bloqueada**.
- motivo:
  - o sistema agora possui base auditável e controlada, mas ainda não tem evidência externa suficiente para movimentar dinheiro real em produção.

### Próxima abordagem recomendada
- **Payments Financial Operations Closure Review**
- motivo:
  - com refund/reversal fechado como fundação, o próximo passo natural é consolidar o status de operações financeiras de payments como um todo e decidir se saímos de payments para outro módulo de maior ROI.

## Wave IB — Payments Financial Operations Closure Review
- a revisão consolidou o estado financeiro de payments após as trilhas de:
  - provider rollout controlado
  - checkout/payment execution
  - stale payment attempts
  - financial reconciliation
  - admin finance surface
  - refund/reversal foundation

### Readiness consolidado
- **Go técnico para operação controlada de payments**:
  - `PaymentAttempt` tenant-scoped
  - hosted redirect seguro
  - hosted return como hint, não confirmação financeira
  - webhook como fonte de verdade
  - readiness sandbox/produção controlada
  - auditoria read-only de divergências
  - `/ops/payments/finance/`
  - métricas e alertas operacionais
  - fundação interna de refund/reversal
- **No-Go para backoffice financeiro completo**:
  - settlement/extrato de provider
  - ledger financeiro geral
  - correção automática de divergências
  - expiração automática de tentativas pendentes
  - pruning/retention financeiro formal
  - refund production-ready

### Decisão de continuidade
- payments não deve receber novas micro-waves financeiras agora sem:
  - evidência sandbox externa real
  - demanda operacional concreta
  - necessidade de settlement/ledger financeiro
  - requisito de produção para refund/manual provider operations
- a abordagem financeira fica encerrada como suficiente para suporte, triagem e rollout controlado.

## Wave IC — Payments Financial Operations Final Decision
- decisão:
  - **encerrar payments financial operations como abordagem ativa neste ciclo**.
- decisão complementar:
  - **não tratar payments como bloqueador principal do próximo roadmap funcional**.
- motivo:
  - o módulo já tem controles suficientes para o estágio atual, e insistir em novas micro-waves tende a produzir baixo ROI sem validação externa real.

### Próxima abordagem recomendada
- **System Next ROI Track Selection Review**
- motivo:
  - payments atingiu suficiência operacional controlada; o próximo passo natural é escolher outro eixo de produto/sistema com maior impacto funcional.

## Battery C — Payments Production Readiness Closure

- o módulo `payments` agora possui gates executáveis para as 7 ondas da Battery C.
- query service:
  - `payments.application.production_readiness_queries`
- comando:
  - `python manage.py payments_production_readiness --review closure --provider-gate-ready --provider-activation-evidence-ready --webhook-smoke-ready --refund-gate-ready --refund-smoke-evidence-ready-or-no-go-recorded --financial-reconciliation-ready --rollback-runbook-ready --monitoring-window-defined --incident-owner-defined --no-unbounded-rollout --no-sensitive-material-recorded --decision-recorded`

### Ondas fechadas

1. Payment Provider Production Gate Refresh Review.
2. Payment Provider Production Activation Evidence.
3. Payment Webhook Production Smoke Review.
4. Payment Refund Production Gate Review.
5. Payment Refund Production Smoke Evidence.
6. Payment Financial Reconciliation Production Review.
7. Payments Production Closure Review.

### Decisão

- **Go para readiness de produção controlada de payments**.
- **No-Go para rollout amplo, self-service de refund, execução em lote ou correção financeira automática**.
- produção deve permanecer tenant-by-tenant, com rollback/runbook, monitoramento, dono de incidente e evidência sanitizada.

### Próxima bateria recomendada

**Battery D — Shipping Quote Productionization**

Objetivo:

- evoluir shipping de tracking/promise para cotação real e método de entrega produtivo.
