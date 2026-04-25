# Notifications

## Responsabilidade
Gerenciar e-mails e notificações.

## Entidades principais
- EmailLog

## Casos de uso
- enviar e-mail de pedido
- enviar e-mail de envio

## Regras de negócio
- envios devem ser assíncronos

## Wave BE — Notifications Product Experience Review
- a revisão do eixo de notificações mostra que o módulo ainda é contrato futuro
- hoje ele documenta responsabilidade por e-mails/notificações, mas não possui `EmailLog`, services de envio ou workers implementados
- ao mesmo tempo, o produto já tem eventos e estados suficientes para justificar uma camada de comunicação futura

### Módulo responsável
- **`notifications`**
  - deve ser o dono futuro de:
    - templates de mensagem
    - logs de envio
    - preferências/canais
    - dispatch assíncrono
    - idempotência de notificação
- **módulos de origem**
  - `orders`, `payments`, `shipping`, `tenants` e `subscriptions` devem emitir ou expor eventos
  - não devem embutir lógica de envio de e-mail

### Sinais já existentes no produto
- **pedido**
  - pedido criado
  - pedido confirmado
  - pedido cancelado
- **pagamento**
  - pagamento pendente
  - pagamento confirmado
  - pagamento falhou
  - retorno do ambiente seguro
- **entrega**
  - preparo iniciado
  - envio iniciado
  - entrega concluída
- **plataforma**
  - tenant criado
  - assinatura ativada/cancelada

### O que está forte
- `docs/events-map.md` já lista consumidores de notifications para eventos críticos
- a área do cliente já comunica estados importantes na UI
- os módulos de pedidos/pagamentos/entrega já têm estados e histórico suficientes para alimentar mensagens futuras
- a regra “envios devem ser assíncronos” está correta para escala

### Gaps de produto
- **sem contrato de mensagem**
  - ainda não está definido quais notificações são transacionais, operacionais ou marketing
- **sem público-alvo explícito**
  - customer e owner precisam de mensagens diferentes
  - `OwnerUser` e `Customer` não devem ser confundidos
- **sem canal**
  - e-mail é citado, mas ainda não há contrato para in-app/admin/customer area
- **sem idempotência**
  - ainda não existe chave lógica por evento/destinatário/canal
- **sem tenant context**
  - toda notificação futura deve carregar `tenant_id`
  - também deve respeitar identidade customer/owner

### Decisão prática
- não implementar envio real nesta wave
- o próximo recorte deve definir um catálogo mínimo de notificações transacionais
- priorizar mensagens que reforçam confiança do cliente:
  - pedido recebido
  - pagamento confirmado
  - pagamento falhou
  - pedido enviado
  - pedido entregue
- separar explicitamente:
  - customer-facing
  - owner/admin-facing
  - sistema/auditoria

### Próxima wave
- **Wave BF — Notification Intent Catalog Plan**
- foco:
  - definir o catálogo mínimo de intents de notificação
  - mapear evento, público, canal, idempotency key e copy objetivo antes de implementar qualquer worker

## Wave BF — Notification Intent Catalog Plan
- o catálogo mínimo de notificações deve começar por intents transacionais
- o objetivo é criar contrato de produto antes de qualquer envio real
- cada intent deve ser pequeno, idempotente e tenant-scoped

### Contrato mínimo por intent
- `intent_key`
- `source_event`
- `audience`
  - `customer`
  - `owner`
  - `system`
- `channel`
  - inicialmente `email`
  - futuro: `in_app`, `admin`
- `idempotency_key_template`
- `title`
- `description`
- `cta_label`
- `cta_target`

### Intents customer-facing iniciais
- **`customer.order.received`**
  - evento: `order.created`
  - canal: `email`
  - objetivo: confirmar que o pedido nasceu e pode ser acompanhado
  - CTA: abrir detalhe do pedido
- **`customer.payment.confirmed`**
  - evento: `payment.paid`
  - canal: `email`
  - objetivo: avisar que pagamento foi confirmado e preparo pode avançar
  - CTA: acompanhar pedido
- **`customer.payment.failed`**
  - evento: `payment.failed`
  - canal: `email`
  - objetivo: avisar que a tentativa falhou sem sugerir perda do pedido
  - CTA: retomar pagamento
- **`customer.shipment.sent`**
  - evento: `shipment.sent`
  - canal: `email`
  - objetivo: avisar que entrega saiu para transporte
  - CTA: acompanhar entrega
- **`customer.shipment.delivered`**
  - evento: `shipment.delivered`
  - canal: `email`
  - objetivo: confirmar entrega e preservar histórico
  - CTA: ver pedido / comprar novamente

### Intents owner-facing iniciais
- **`owner.order.created`**
  - evento: `order.created`
  - canal: `email`
  - objetivo: avisar nova venda recebida
  - CTA: abrir admin do pedido
- **`owner.payment.failed`**
  - evento: `payment.failed`
  - canal: `email`
  - objetivo: destacar pedido que pode precisar de suporte
  - CTA: abrir pedido
- **`owner.shipment.delivered`**
  - evento: `shipment.delivered`
  - canal: `email`
  - objetivo: fechar ciclo operacional e possível pós-venda
  - CTA: abrir pedido

### Regras de idempotência
- idempotency key mínima:
  - `{tenant_id}:{intent_key}:{entity_type}:{entity_id}:{channel}`
- para eventos externos de pagamento:
  - incluir referência externa quando disponível
- nunca usar apenas e-mail como chave
- nunca ignorar `tenant_id`

### Fora de escopo
- envio real
- Celery task
- `EmailLog`
- preferências de unsubscribe
- templates HTML
- provider SMTP
- in-app notifications

### Próxima wave
- **Wave BG — Notification Intent Catalog Execution**
- foco:
  - implementar catálogo puro em `notifications.application`
  - adicionar testes do contrato mínimo sem enviar e-mail

## Wave BG — Notification Intent Catalog Execution
- o catálogo puro de intents foi implementado em `notifications.application`
- a execução não envia e-mail, não cria logs e não depende de Celery
- o objetivo foi criar um contrato testável para futuras notificações

### Escopo executado
- **catálogo**
  - `notification_intent_catalog.py`
  - contém intents customer e owner
- **contrato**
  - `intent_key`
  - `source_event`
  - `audience`
  - `channel`
  - `idempotency_key_template`
  - `title`
  - `description`
  - `cta_label`
  - `cta_target`
- **helpers**
  - listar intents
  - filtrar por audience/source event
  - buscar por `intent_key`
  - gerar chave de idempotência
- **testes**
  - cobertura para catálogo, filtros, lookup e idempotência

### Intents iniciais
- customer:
  - `customer.order.received`
  - `customer.payment.confirmed`
  - `customer.payment.failed`
  - `customer.shipment.sent`
  - `customer.shipment.delivered`
- owner:
  - `owner.order.created`
  - `owner.payment.failed`
  - `owner.shipment.delivered`

### O que não mudou
- `EmailLog`
- migrations
- Celery
- provider SMTP
- templates HTML de e-mail
- preferências de notificação
- integração com eventos reais

### Próxima wave
- **Wave BH — Notification Dispatch Boundary Review**
- foco:
  - revisar qual deve ser a fronteira segura para transformar eventos em intents
  - decidir se o próximo passo é service de resolução/preview ou worker real

## Wave BH — Notification Dispatch Boundary Review
- a fronteira de dispatch deve transformar eventos em intents sem enviar mensagens diretamente
- o módulo `notifications` deve ser o dono da resolução entre evento, público, canal e idempotência
- módulos de origem não devem importar provider SMTP, templates de e-mail ou regras internas de notificações

### Contrato seguro de entrada
- `source_event`
- `tenant_id`
- `entity_type`
- `entity_id`
- `audience` opcional

### Contrato seguro de saída
- intent resolvida
- público-alvo
- canal
- chave de idempotência
- copy mínima
- CTA lógico

### Decisão prática
- não criar worker real nesta wave
- não criar `EmailLog` ainda
- o próximo passo deve ser um resolver/preview puro em `notifications.application`
- dispatch assíncrono real só deve entrar depois de:
  - destino/resolved recipient explícito
  - persistência de tentativa/envio
  - política de retry
  - preferência/canal por tenant

### Próxima wave
- **Wave BI — Notification Dispatch Preview Execution**
- foco:
  - implementar preview puro de dispatch
  - preservar `tenant_id` na chave de idempotência
  - validar filtros por evento e público sem enviar e-mail

## Wave BI — Notification Dispatch Preview Execution
- foi criado um resolver puro de preview para dispatch de notificações
- o resolver ainda não envia mensagens, não cria logs e não aciona Celery
- a função central recebe evento e contexto tenant-scoped, retornando previews de intents candidatas

### Escopo executado
- `notification_dispatch_resolver.py`
- `NotificationDispatchPreview`
- `resolve_notification_dispatch_previews`
- testes para:
  - resolução customer e owner por evento
  - filtro por audience
  - idempotência com `tenant_id`
  - contexto incompleto sem preview

### Fronteiras preservadas
- `orders`, `payments` e `shipping` continuam sem dependência de envio
- `notifications.application` concentra a resolução
- provider SMTP, templates HTML, `EmailLog` e worker continuam fora de escopo

### Próxima wave
- **Wave BJ — Notification Recipient Boundary Review**
- foco:
  - revisar como resolver destinatários sem misturar `Customer` e `OwnerUser`
  - decidir o contrato mínimo antes de qualquer envio real

## Wave BJ — Notification Recipient Boundary Review
- a resolução de destinatários não deve misturar identidade de compra com identidade administrativa
- `Customer` pertence a um tenant específico e representa o comprador
- `OwnerUser` representa administração da loja e não deve ser tratado como customer
- o módulo `notifications` pode receber destinatários resolvidos, mas não deve virar dono da regra de identidade

### Boundary segura
- módulos/eventos de origem devem fornecer ou permitir resolver:
  - `tenant_id`
  - audience esperado
  - tipo de identidade
  - id da identidade
  - canal/endereço de entrega
- `notifications.application` deve trabalhar com referência explícita de destinatário
- queries reais para customer/owner devem ficar em contracts bem definidos antes de envio real

### Decisão prática
- criar contrato puro de recipient target
- não consultar `customers.models.Customer` diretamente nesta etapa
- não consultar owner/admin diretamente nesta etapa
- não persistir destinatários ainda

### Próxima wave
- **Wave BK — Notification Recipient Target Execution**
- foco:
  - implementar value object puro para destinatários
  - separar explicitamente `customer` e `owner_user`
  - manter `tenant_id` obrigatório

## Wave BK — Notification Recipient Target Execution
- foi criado um contrato puro de recipient target
- a implementação não consulta banco, não envia e-mail e não resolve usuários automaticamente
- o objetivo é impedir que o futuro dispatch aceite destinatário ambíguo

### Escopo executado
- `notification_recipient_targets.py`
- `NotificationRecipientTarget`
- helpers explícitos:
  - `build_customer_recipient_target`
  - `build_owner_recipient_target`
- testes para:
  - customer target
  - owner target
  - ausência de e-mail como não entregável
  - contexto sem tenant/identidade como inválido

### Fronteiras preservadas
- `customers` segue dono do comprador
- `accounts` segue dono do owner/admin
- `notifications` recebe referência explícita e prepara entrega futura

### Próxima wave
- **Wave BL — Notification Dispatch Envelope Review**
- foco:
  - combinar preview de intent e recipient target em um envelope puro
  - ainda sem persistir `EmailLog` ou acionar worker

## Wave BL — Notification Dispatch Envelope Review
- o envelope deve ser a primeira unidade realmente “quase enviável”
- ele deve combinar:
  - intent resolvida
  - contexto tenant-scoped
  - destinatário explícito
  - copy mínima
  - chave de idempotência
- ainda não deve representar envio persistido

### Regras do envelope
- `tenant_id` do preview e do recipient precisa ser igual
- `audience` do preview e do recipient precisa ser igual
- recipient sem endereço de entrega não gera envelope
- a idempotência do evento deve ser preservada
- o delivery por destinatário deve ganhar chave própria para evitar colisão quando houver mais de um recipient no mesmo público

### Decisão prática
- criar envelope puro em `notifications.application`
- rejeitar mismatch de tenant/audience fechando sem envelope
- manter `EmailLog`, retries e workers fora de escopo

### Próxima wave
- **Wave BM — Notification Dispatch Envelope Execution**
- foco:
  - implementar contrato de envelope
  - validar tenant/audience/deliverability
  - gerar chave de delivery por recipient

## Wave BM — Notification Dispatch Envelope Execution
- foi implementado um envelope puro de dispatch
- a implementação combina preview de intent com recipient target explícito
- mismatches de tenant, audience ou e-mail ausente não geram envelope

### Escopo executado
- `notification_dispatch_envelopes.py`
- `NotificationDispatchEnvelope`
- `build_notification_dispatch_envelope`
- `recipient_delivery_key`
- testes para:
  - envelope válido
  - rejeição cross-tenant
  - rejeição por audience divergente
  - rejeição sem endereço de entrega

### O que ainda não mudou
- não há `EmailLog`
- não há Celery task
- não há provider SMTP
- não há renderização HTML de template
- não há integração automática com eventos reais

### Próxima wave
- **Wave BN — Notification Persistence Boundary Review**
- foco:
  - decidir quando `EmailLog` deve nascer
  - separar tentativa planejada, envio solicitado e entrega confirmada

## Wave BN — Notification Persistence Boundary Review
- a persistência de notificações deve nascer antes do worker real
- o objetivo inicial é registrar unidade planejável/idempotente, não confirmar entrega
- `EmailLog` deve carregar snapshot suficiente para auditoria e retry futuro sem depender do estado atual de módulos externos

### Estados mínimos
- `planned`
  - envelope virou unidade persistível
- `requested`
  - envio foi solicitado ao worker/provider
- `sent`
  - envio aceito/concluído pelo provider
- `failed`
  - tentativa falhou
- `skipped`
  - unidade ignorada por regra operacional futura

### Campos mínimos
- `tenant_id`
- `source_event`
- `intent_key`
- `audience`
- `channel`
- `entity_type`
- `entity_id`
- `idempotency_key`
- `recipient_delivery_key`
- snapshot do recipient
- snapshot da copy
- status e timestamps de envio

### Decisão prática
- criar `EmailLog` mínimo e tenant-scoped
- não criar worker ainda
- não criar integração SMTP ainda
- não renderizar template HTML ainda

### Próxima wave
- **Wave BO — EmailLog Minimal Persistence Execution**
- foco:
  - implementar modelo e migration inicial
  - validar idempotência por `recipient_delivery_key`
  - manter status inicial como `planned`

## Wave BO — EmailLog Minimal Persistence Execution
- `EmailLog` foi implementado como registro mínimo de unidade de e-mail planejável
- a tabela nasce tenant-scoped e com chave única por delivery de recipient
- o modelo preserva snapshot de evento, intent, recipient e copy

### Escopo executado
- `notifications.models.EmailLog`
- migration inicial de `notifications`
- testes de:
  - status default `planned`
  - canal default `email`
  - unicidade de `recipient_delivery_key`

### O que ainda não mudou
- nenhum worker Celery
- nenhum provider SMTP
- nenhuma criação automática de logs a partir de eventos
- nenhum template HTML

### Próxima wave
- **Wave BP — Notification Log Writer Boundary Review**
- foco:
  - revisar um writer idempotente de logs a partir do envelope
  - ainda sem dispatch assíncrono

## Wave BP — Notification Log Writer Boundary Review
- o writer de logs deve ser o primeiro ponto que toca banco a partir do envelope
- ele deve persistir unidade planejada e não deve solicitar envio
- a operação deve ser idempotente por `recipient_delivery_key`

### Regras do writer
- recebe apenas envelope já validado
- cria `EmailLog` com status `planned`
- se a delivery key já existir, retorna o registro existente
- não atualiza copy/status de log existente automaticamente
- não aciona worker, provider ou template

### Decisão prática
- implementar writer em `notifications.application`
- usar `get_or_create` por `recipient_delivery_key`
- devolver resultado com flag `created`

### Próxima wave
- **Wave BQ — Notification Log Writer Execution**
- foco:
  - persistir envelopes como `EmailLog`
  - validar idempotência sem duplicar envio planejado

## Wave BQ — Notification Log Writer Execution
- foi implementado writer idempotente para transformar envelope em `EmailLog`
- chamadas repetidas para a mesma delivery key retornam o log existente
- a execução ainda não dispara envio

### Escopo executado
- `notification_log_writer.py`
- `EmailLogWriteResult`
- `record_email_log_from_envelope`
- testes para:
  - criação de log planejado
  - reuso idempotente do log existente

### Próxima wave
- **Wave BR — Notification Worker Boundary Review**
- foco:
  - revisar o contrato futuro do worker sem plugar Celery/SMTP cedo demais

## Wave BR — Notification Worker Boundary Review
- antes de plugar Celery/SMTP, o sistema precisa de transições explícitas do `EmailLog`
- o worker futuro deve apenas consumir logs planejados/solicitáveis e marcar resultado
- mudanças de status precisam ser tenant-scoped para evitar mutação cross-tenant

### Transições iniciais
- `planned` → `requested`
- `planned/requested` → `sent`
- `planned/requested/failed/skipped` → `failed`
- `planned/requested` → `skipped`

### Decisão prática
- implementar comandos de status sem worker real
- cada comando deve exigir `tenant_id` e `log_id`
- não buscar logs globalmente
- não permitir que log `sent` volte para `failed`

### Próxima wave
- **Wave BS — Notification Log Status Commands Execution**
- foco:
  - implementar comandos de lifecycle
  - testar tenant-scope e transições seguras

## Wave BS — Notification Log Status Commands Execution
- foram implementados comandos de status para `EmailLog`
- os comandos são tenant-scoped e não acionam provider externo
- o objetivo é preparar o worker futuro sem introduzir infraestrutura prematura

### Escopo executado
- `notification_log_status_commands.py`
- `mark_email_log_requested`
- `mark_email_log_sent`
- `mark_email_log_failed`
- `mark_email_log_skipped`
- testes para:
  - request tenant-scoped
  - proteção cross-tenant
  - sent
  - failed
  - skipped

### Próxima wave
- **Wave BT — Notifications Product Track Wrap-Up Review**
- foco:
  - fechar o eixo atual de notifications
  - listar bloqueios reais antes de worker/provider/event integration

## Wave BT — Notifications Product Track Wrap-Up Review
- o eixo atual de notifications deixou de ser apenas documentação futura
- agora existe uma cadeia mínima e testável:
  - catálogo de intents
  - preview por evento
  - recipient target explícito
  - dispatch envelope
  - persistência em `EmailLog`
  - comandos de lifecycle do log

### Pronto nesta fase
- contrato de mensagens transacionais customer/owner
- idempotência tenant-scoped por intent/evento
- chave de delivery por recipient
- separação explícita entre `Customer` e owner/admin
- persistência mínima auditável
- status transitions sem envio real

### Ainda bloqueia envio real
- resolver destinatários reais a partir de eventos de domínio
- definir provider/adapters de e-mail
- criar templates de e-mail
- plugar Celery/queue
- definir retry/backoff
- definir preferências por tenant e opt-out quando aplicável
- integrar com eventos reais (`order.created`, `payment.paid`, `payment.failed`, `shipment.sent`, `shipment.delivered`)

### Decisão de encerramento
- a fase atual de produto/contrato de notifications está pronta
- o próximo salto já não é mais revisão de UX; é integração operacional controlada
- worker real só deve nascer depois de provider/template/recipient resolver ficarem explícitos

### Próxima trilha natural
- **Notification Event Integration Readiness**
- foco:
  - mapear eventos reais disponíveis
  - decidir ponto de publicação/consumo
  - conectar apenas um evento piloto com writer idempotente antes de liberar dispatch

## Wave BU — Notification Event Integration Readiness
- o mapa atual de eventos existe como contrato, mas ainda não há barramento interno genérico
- o ponto real mais seguro para piloto é o webhook de pagamento, porque ele já normaliza eventos externos e resolve `tenant_id`
- o primeiro evento escolhido é `payment.failed`

### Por que `payment.failed`
- não altera estoque
- não muda pedido para estado final
- já possui retry/continuidade na área do cliente
- tem intent customer-facing definida
- permite validar idempotência com replay de webhook

### Decisão prática
- implementar handler em `notifications.application`
- o handler deve resolver o pedido por `tenant_id + order_number`
- criar apenas log customer-facing quando houver `Customer` explícito
- não enviar e-mail ainda
- não criar bus genérico ainda

### Próxima wave
- **Wave BV — Payment Failed Notification Log Integration**
- foco:
  - conectar `payment.failed` ao writer idempotente
  - validar replay sem duplicar `EmailLog`

## Wave BV — Payment Failed Notification Log Integration
- o evento piloto `payment.failed` agora cria `EmailLog` planejado para o customer
- a integração acontece via boundary de `notifications.application`
- o webhook de pagamentos continua dono da normalização/segurança e apenas chama o handler depois da falha persistida

### Escopo executado
- `notification_event_handlers.py`
- handler `record_customer_order_event_email_logs`
- integração no webhook de payments para `payment.failed`
- testes de:
  - criação do log customer-facing
  - replay idempotente
  - skip quando não há `Customer` explícito
  - webhook criando `EmailLog`

### O que ainda não mudou
- nenhum e-mail real é enviado
- nenhum worker é acionado
- owner-facing ainda não foi conectado
- `payment.paid`, `order.created` e `shipment.*` continuam fora do piloto

### Próxima wave
- **Wave BW — Payment Failed Integration Wrap-Up Review**
- foco:
  - revisar se o piloto está seguro
  - listar próximos eventos candidatos sem plugar tudo de uma vez

## Wave BW — Payment Failed Integration Wrap-Up Review
- o piloto de integração está seguro para esta fase
- `payment.failed` agora gera uma unidade persistida e idempotente de notificação customer-facing
- a integração não envia mensagem real e não amplia superfície de provider/worker

### Critérios atendidos
- evento entra por webhook já protegido em `payments`
- `tenant_id` é resolvido antes do handler de notifications
- log só nasce depois de `payment-failed` persistido
- recipient exige `Customer` explícito
- replay do evento reutiliza `EmailLog`
- pedido sem customer explícito não gera envio planejado

### Próximos candidatos
- `payment.paid`
  - bom segundo candidato porque também vem do webhook
  - maior impacto operacional por confirmar pedido e estoque
- `shipment.sent`
  - depende de fluxo real de shipping/tracking mais maduro
- `order.created`
  - depende de decidir se confirmação inicial deve nascer no checkout ou em orders
- owner-facing events
  - dependem de resolver owners/admins com contrato explícito

### Decisão de encerramento
- não conectar novos eventos automaticamente nesta mesma leva
- o piloto cumpriu o objetivo: provar ponte evento → intent → recipient → envelope → `EmailLog`
- a próxima expansão deve adicionar `payment.paid` como segundo evento, mantendo a mesma disciplina incremental

## Wave BX — Payment Paid Notification Log Integration
- `payment.paid` foi conectado como segundo evento de notifications
- a integração reaproveita o mesmo handler tenant-scoped usado por `payment.failed`
- o log customer-facing só nasce quando a confirmação externa é aplicada pela primeira vez

### Escopo executado
- webhook de payments chama notifications após `payment-confirmed`
- `payment-already-confirmed` não cria nova unidade de comunicação
- replay segue idempotente por `recipient_delivery_key`
- teste do webhook cobre criação de `EmailLog` para pagamento confirmado

### O que ainda não mudou
- não há envio real
- não há worker
- não há owner-facing notification
- não há template HTML

### Próxima wave
- **Wave BY — Payment Event Notification Wrap-Up Review**
- foco:
  - revisar a dupla `payment.failed/payment.paid`
  - decidir se ainda vale conectar `order.created` nesta abordagem ou encerrar em pagamentos

## Wave BY — Payment Event Notification Wrap-Up Review
- a dupla `payment.failed` e `payment.paid` fecha um primeiro recorte coerente de eventos de pagamento
- ambos entram pelo webhook de `payments`, que já resolve tenant e valida segurança antes de chamar notifications
- a integração atual prova o caminho evento real → intent → recipient → envelope → `EmailLog`

### Por que não conectar `order.created` agora
- o ponto de materialização atual está em `checkout_completion_commands`
- ainda não há barramento interno genérico nem publicação formal pelo módulo `orders`
- chamar notifications diretamente de checkout para `order.created` aumentaria acoplamento antes de existir boundary de evento mais clara
- a confirmação inicial de pedido também compete com mensagens de checkout/retorno e pode duplicar comunicação de “pedido recebido”

### Decisão prática
- encerrar esta abordagem em eventos de pagamento
- manter `order.created` como próximo candidato somente após definir um publisher/dispatcher interno
- manter `shipment.*` bloqueado até o fluxo real de shipping/tracking amadurecer
- manter owner-facing bloqueado até resolver owners/admins explicitamente

### Próxima wave
- **Wave BZ — Notification Event Integration Closure**
- foco:
  - consolidar o que ficou pronto
  - listar bloqueios reais para continuar até envio operacional

## Wave BZ — Notification Event Integration Closure
- a abordagem de integração por evento está fechada nesta fase
- o sistema agora possui dois eventos reais de pagamento criando logs planejados:
  - `payment.failed`
  - `payment.paid`
- ambos são customer-facing, tenant-scoped e idempotentes

### Pronto
- catálogo de intents
- resolver de preview
- recipient target explícito
- envelope validado por tenant/audience
- `EmailLog` persistido
- writer idempotente
- lifecycle de log
- integração real de `payment.failed`
- integração real de `payment.paid`

### Bloqueios restantes
- event bus/publisher interno para `order.created`
- resolver explícito de owners/admins
- fluxo real de shipping para `shipment.sent` e `shipment.delivered`
- provider SMTP
- templates HTML/texto
- worker Celery
- retry/backoff operacional
- preferências por tenant e opt-out quando aplicável

### Decisão de encerramento
- esta abordagem está completa até o limite seguro sem infraestrutura de envio
- a próxima abordagem natural já é **Notification Delivery Infrastructure Readiness**
- o primeiro recorte futuro deve ser provider/template/worker em modo dry-run antes de qualquer envio real ao cliente

## Wave CA — Notification Delivery Infrastructure Readiness
- a próxima camada deve sair de `EmailLog` planejado para delivery controlado
- o modo inicial precisa ser dry-run por padrão
- envio real só deve ser possível com configuração explícita

### Decisão prática
- adicionar flag `NOTIFICATIONS_EMAIL_DRY_RUN`
- usar `DEFAULT_FROM_EMAIL` apenas quando dry-run estiver desligado
- criar adapter de delivery em `notifications.infrastructure`
- não criar worker ainda nesta wave

### Próxima wave
- **Wave CB — Email Delivery Adapter Dry-Run Execution**
- foco:
  - implementar adapter de e-mail
  - validar dry-run sem envio
  - validar envio real apenas com backend Django configurado

## Wave CB — Email Delivery Adapter Dry-Run Execution
- foi criado adapter de delivery de e-mail com dry-run seguro por padrão
- quando `NOTIFICATIONS_EMAIL_DRY_RUN=True`, nenhum e-mail é enviado
- quando dry-run é desligado, o adapter usa o backend de e-mail do Django e exige `DEFAULT_FROM_EMAIL`

### Escopo executado
- `notifications.infrastructure.email_delivery`
- `EmailDeliveryAdapter`
- `EmailDeliveryResult`
- settings:
  - `DEFAULT_FROM_EMAIL`
  - `NOTIFICATIONS_EMAIL_DRY_RUN`
  - `NOTIFICATIONS_EMAIL_BATCH_SIZE`
- testes para:
  - dry-run
  - envio via backend Django local-memory
  - falha segura sem remetente

### Próxima wave
- **Wave CC — Notification Delivery Command Boundary Review**
- foco:
  - criar comando tenant-scoped para processar um `EmailLog`
  - atualizar lifecycle sem precisar de Celery ainda

## Wave CC — Notification Delivery Command Boundary Review
- o comando de delivery deve ser a boundary entre `EmailLog` e adapter de infraestrutura
- ele deve continuar tenant-scoped e reutilizar o lifecycle existente
- o worker futuro deverá chamar esse comando, não falar direto com o adapter

### Regras do comando
- recebe `tenant_id` e `log_id`
- marca o log como `requested`
- chama adapter
- `sent` marca `sent`
- `dry-run` marca `skipped`
- falha marca `failed`
- cross-tenant retorna indisponível sem mutar log

### Próxima wave
- **Wave CD — Notification Delivery Command Execution**
- foco:
  - implementar comando de processamento de `EmailLog`
  - testar dry-run, sent, failed e proteção cross-tenant

## Wave CD — Notification Delivery Command Execution
- foi criado comando tenant-scoped para processar `EmailLog`
- o comando reutiliza as transições de status já existentes
- dry-run vira `skipped`, preservando que nenhum e-mail real saiu

### Escopo executado
- `notification_delivery_commands.py`
- `EmailDeliveryCommandService`
- `EmailDeliveryCommandResult`
- testes para:
  - dry-run
  - sent
  - failed
  - proteção cross-tenant

### Próxima wave
- **Wave CE — Notification Worker Boundary Review**
- foco:
  - preparar worker/management command em lote sem exigir Celery real nesta etapa

## Wave CE — Notification Worker Boundary Review
- a primeira execução em lote deve funcionar sem Celery obrigatório
- isso permite validar dry-run operacional em ambiente real antes de ligar workers
- o worker futuro deve ser fino e chamar o mesmo comando application por log

### Decisão prática
- criar management command tenant-scoped
- processar somente `EmailLog` com status `planned`
- respeitar limite de batch
- manter dry-run como comportamento default via adapter

### Próxima wave
- **Wave CF — Notification Email Batch Command Execution**
- foco:
  - implementar comando `process_email_logs`
  - validar batch tenant-scoped em dry-run

## Wave CF — Notification Email Batch Command Execution
- foi criado comando operacional para processar `EmailLog` planejado em lote
- o comando exige `tenant_id`
- o limite default vem de `NOTIFICATIONS_EMAIL_BATCH_SIZE`
- em dry-run, logs processados viram `skipped`

### Escopo executado
- `notifications.management.commands.process_email_logs`
- teste de batch tenant-scoped
- proteção por limite

### Próxima wave
- **Wave CG — Notification Delivery Infrastructure Closure**
- foco:
  - fechar readiness de delivery
  - listar exatamente o que falta para envio real em produção

## Wave CG — Notification Delivery Infrastructure Closure
- a abordagem de delivery infrastructure está fechada no limite seguro de dry-run
- o sistema agora consegue processar `EmailLog` planejado sem enviar e-mail real por padrão
- a mesma boundary pode ser usada por Celery no futuro

### Pronto
- settings explícitos:
  - `NOTIFICATIONS_EMAIL_DRY_RUN`
  - `NOTIFICATIONS_EMAIL_BATCH_SIZE`
  - `DEFAULT_FROM_EMAIL`
- adapter de e-mail usando backend Django
- comando application tenant-scoped para processar um log
- management command tenant-scoped para batch
- dry-run seguro marcando `EmailLog` como `skipped`
- testes de adapter, command e batch

### Ainda bloqueia envio real
- configurar provider SMTP/transacional real
- definir templates HTML/texto por intent
- decidir URLs reais de CTA por tenant/domínio
- adicionar observabilidade específica de delivery
- definir retry/backoff automático
- plugar Celery task em fila `emails`
- definir política de preferências/opt-out por tenant
- rodar rollout por tenant com `NOTIFICATIONS_EMAIL_DRY_RUN=0`

### Decisão de encerramento
- não habilitar envio real nesta abordagem
- a próxima abordagem natural é **Notification Template & CTA Readiness**
- antes de provider real, cada intent precisa de template e CTA resolvido por tenant

## Wave CH — Notification Template & CTA Readiness
- antes de envio real, cada CTA lógico precisa virar URL resolvida por tenant
- o primeiro recorte deve cobrir detalhe de pedido customer-facing e admin-facing
- URLs devem respeitar subdomínio ou custom domain do tenant

### Decisão prática
- implementar resolver de CTA em `notifications.application`
- resolver `customer_order_detail` e `admin_order_detail`
- exigir `tenant_id`, `entity_type=order` e `entity_id`
- não enviar link lógico como destino final de e-mail real

### Próxima wave
- **Wave CI — Notification CTA Resolver Execution**
- foco:
  - resolver URLs absolutas tenant-aware
  - integrar CTA resolvido no corpo texto do adapter

## Wave CI — Notification CTA Resolver Execution
- foi criado resolver de CTA para transformar targets lógicos em URLs absolutas
- o adapter de e-mail agora inclui URL resolvida quando disponível
- o resolver é tenant-scoped e não resolve pedido cross-tenant

### Escopo executado
- `notification_cta_resolver.py`
- `NotificationCta`
- resolução de:
  - `customer_order_detail`
  - `admin_order_detail`
- integração no plain-text do delivery adapter
- testes para:
  - subdomínio
  - custom domain
  - target desconhecido
  - proteção cross-tenant

### Próxima wave
- **Wave CJ — Notification Text Template Review**
- foco:
  - revisar se o corpo plain-text já é suficiente para dry-run/primeiro envio controlado
  - decidir se HTML template entra agora ou fica para uma próxima abordagem

## Wave CJ — Notification Text Template Review
- para o próximo rollout controlado, plain-text é suficiente como primeiro contrato
- HTML template ainda deve ficar fora para evitar ampliar superfície visual/provider antes de entrega real controlada
- o renderer deve ser application-level e o adapter deve apenas enviar resultado renderizado

### Decisão prática
- extrair renderer plain-text para `notifications.application`
- incluir subject, corpo e CTA resolvido
- manter HTML fora de escopo
- manter adapter fino

### Próxima wave
- **Wave CK — Notification Plain-Text Renderer Execution**
- foco:
  - implementar renderer de mensagem
  - fazer adapter consumir renderer
  - testar CTA resolvido no corpo

## Wave CK — Notification Plain-Text Renderer Execution
- foi criado renderer plain-text para `EmailLog`
- o adapter de delivery agora consome mensagem renderizada em vez de montar corpo internamente
- o renderer inclui CTA resolvido quando disponível

### Escopo executado
- `notification_message_renderer.py`
- `RenderedNotificationMessage`
- `render_email_log_message`
- teste de subject, corpo e CTA absoluto

### Próxima wave
- **Wave CL — Notification Template & CTA Closure**
- foco:
  - fechar abordagem de templates/CTA
  - listar próximos bloqueios para envio real

## Wave CL — Notification Template & CTA Closure
- a abordagem de Template & CTA Readiness está fechada para o primeiro envio controlado
- CTAs lógicos já viram URLs absolutas tenant-aware
- o corpo plain-text já é renderizado por application service

### Pronto
- resolver de CTA tenant-scoped
- suporte a subdomínio e custom domain
- proteção contra order cross-tenant
- renderer plain-text
- adapter de delivery consumindo mensagem renderizada

### Ainda bloqueia envio real amplo
- HTML template visual
- tracking/unsubscribe/preferências
- provider transacional real
- observabilidade de bounce/delivery
- rollout por tenant

### Decisão de encerramento
- não criar HTML nesta abordagem
- próximo ciclo natural: **Notification Rollout & Observability Readiness**
- foco: métricas/consultas de readiness antes de desligar dry-run

## Wave CM — Notification Rollout & Observability Readiness
- antes de desligar dry-run, operação precisa enxergar filas planejadas, falhas e skips por tenant
- o primeiro recorte deve ser query simples e management command
- métricas Prometheus podem entrar depois, reaproveitando a mesma consulta

### Decisão prática
- criar snapshot tenant-scoped de status de `EmailLog`
- expor comando `notification_readiness`
- não criar dashboard ainda

### Próxima wave
- **Wave CN — Notification Readiness Query Execution**
- foco:
  - implementar query de contadores por status
  - implementar comando de relatório

## Wave CN — Notification Readiness Query Execution
- foi criado snapshot de readiness por tenant
- o comando `notification_readiness` imprime contadores operacionais de `EmailLog`
- isso permite validar dry-run e backlog antes de envio real

### Escopo executado
- `notification_readiness_queries.py`
- `NotificationReadinessSnapshot`
- comando `notification_readiness`
- testes de:
  - contagem tenant-scoped
  - pending/failure flags
  - saída do comando

### Próxima wave
- **Wave CO — Notification Rollout Closure**
- foco:
  - fechar rollout readiness
  - definir critérios mínimos para desligar dry-run por tenant

## Wave CO — Notification Rollout Closure
- a abordagem de Rollout & Observability Readiness está fechada em nível operacional mínimo
- já existe relatório tenant-scoped para verificar backlog e falhas antes de qualquer envio real

### Critérios mínimos para desligar dry-run por tenant
- `notification_readiness --tenant-id <id>` sem falhas inesperadas
- backlog planejado conhecido e compatível com o lote
- `DEFAULT_FROM_EMAIL` configurado
- provider/backend de e-mail configurado
- CTA customer/admin validado em domínio final
- teste com tenant piloto e volume pequeno
- plano de rollback: religar `NOTIFICATIONS_EMAIL_DRY_RUN=1`

### Ainda não pronto para envio amplo
- sem HTML template
- sem opt-out/preferências
- sem dashboard Prometheus/Grafana específico
- sem Celery task real
- sem política automática de retry/backoff

### Decisão de encerramento
- a cadeia completa está pronta para piloto dry-run e relatório operacional
- envio real amplo continua bloqueado deliberadamente
- próxima abordagem natural fora de notifications: revisar **Event Bus / Publisher Boundary**, pois `order.created` e `shipment.*` dependem disso

## Wave CP — Event Bus / Publisher Boundary Review
- novos eventos como `order.created` e `shipment.*` não devem chamar notifications diretamente de qualquer módulo
- antes de plugar esses eventos, é preciso um contrato mínimo de publicação
- o primeiro publisher deve ser in-process e pequeno, apenas para estabilizar boundary

### Decisão prática
- criar `NotificationEvent`
- criar publisher com subscribe/publish
- não criar Celery ainda
- não conectar `order.created` automaticamente nesta wave

### Próxima wave
- **Wave CQ — Minimal Notification Event Publisher Execution**
- foco:
  - implementar publisher mínimo
  - testar dispatch in-process
  - documentar que não substitui fila real

## Wave CQ — Minimal Notification Event Publisher Execution
- foi criado publisher mínimo para eventos de notifications
- o publisher é in-process e serve como contrato de transição
- ele não é fila distribuída, não persiste eventos e não substitui Celery

### Escopo executado
- `notification_event_bus.py`
- `NotificationEvent`
- `NotificationEventPublisher`
- singleton `notification_event_publisher`
- testes de publish/subscribe e noop sem handlers

### Próxima wave
- **Wave CR — Event Publisher Closure**
- foco:
  - fechar o ciclo sem plugar eventos adicionais cedo demais
  - definir próximos candidatos seguros

## Wave CR — Event Publisher Closure
- o ciclo de Event Bus / Publisher Boundary está fechado como contrato mínimo
- ainda não é seguro ligar `order.created` automaticamente sem decidir o ponto oficial de publicação em `orders`
- também não é seguro ligar `shipment.*` antes do fluxo real de shipping/tracking

### Pronto
- contrato `NotificationEvent`
- publisher in-process testado
- documentação de limite: não é Celery, não é fila, não persiste eventos

### Próximos candidatos
- `order.created`
  - depende de publisher oficial no boundary de criação de pedido
- `shipment.sent`
  - depende de shipment real/tracking
- owner-facing
  - depende de resolver explícito de owners/admins

### Decisão de encerramento
- não conectar novos eventos neste ciclo
- próximo ciclo natural: **Owner Recipient Resolver Readiness**
- motivo: owner-facing já existe no catálogo, mas ainda falta resolver admin/owner com segurança

## Wave CS — Owner Recipient Resolver Readiness
- a revisão mostrou que ainda não existe `OwnerUser` persistido como entidade própria no código atual
- `AccountProfile` existe, mas também participa da experiência de conta e possui vínculo opcional com `Customer`
- usar `AccountProfile` como owner recipient agora violaria a regra de não misturar owner/admin com customer

### Decisão prática
- não implementar owner resolver nesta abordagem
- manter intents owner-facing no catálogo como contrato futuro
- bloquear envio owner-facing até existir modelo/contrato explícito de owner/admin por tenant

### Próxima wave
- **Wave CT — Owner Recipient Resolver Closure**
- foco:
  - registrar bloqueio real
  - definir pré-requisitos para habilitar owner-facing notifications

## Wave CT — Owner Recipient Resolver Closure
- owner-facing notifications permanecem bloqueadas por ausência de boundary de identidade administrativa
- isso é uma decisão de segurança multi-tenant, não falta de implementação simples

### Pré-requisitos
- criar ou formalizar `OwnerUser`
- definir vínculo owner ↔ tenant
- definir e-mail ativo/entregável do owner
- definir opt-in/preferência operacional por tenant
- testar isolamento cross-tenant

### Decisão de encerramento
- não criar fallback para owner usando `AccountProfile`
- próximo ciclo natural: **Notifications Final Production Readiness Review**
- foco:
  - consolidar tudo que está pronto
  - separar bloqueios reais de produção
  - decidir Go/No-Go para envio real

## Wave CU — Notifications Final Production Readiness Review
- a trilha de notifications possui pipeline técnico suficiente para dry-run e piloto controlado
- ainda não está pronta para envio real amplo em produção

### Pronto para dry-run
- intents customer/owner catalogadas
- `payment.failed` e `payment.paid` criando `EmailLog`
- `EmailLog` tenant-scoped e idempotente
- delivery adapter com dry-run default
- command application para processar log
- management command de batch tenant-scoped
- CTA resolver tenant-aware
- renderer plain-text
- readiness query/command
- publisher mínimo in-process como boundary futura

### No-Go para envio real amplo
- `OwnerUser`/owner resolver não implementado
- sem provider transacional configurado/validado
- sem Celery task real em fila `emails`
- sem retry/backoff automático
- sem preferências/opt-out por tenant
- sem HTML template
- sem dashboard/métricas específicas de delivery
- sem política de bounce/suppression
- sem event bus distribuído para `order.created` e `shipment.*`

### Go condicionado
- pode executar dry-run por tenant usando:
  - `process_email_logs --tenant-id <id>`
  - `notification_readiness --tenant-id <id>`
- pode testar envio real apenas em tenant piloto, volume pequeno, com:
  - `NOTIFICATIONS_EMAIL_DRY_RUN=0`
  - `DEFAULT_FROM_EMAIL`
  - backend/provider configurado
  - rollback imediato religando dry-run

### Decisão final
- **Go para dry-run operacional**
- **Go condicionado para piloto real isolado**
- **No-Go para produção ampla**

### Próxima abordagem natural
- **Owner/Admin Identity Implementation**
- motivo:
  - desbloqueia owner-facing notifications
  - reduz ambiguidade de identidade em accounts
  - prepara comunicações administrativas reais por tenant

## Wave CV — Owner/Admin Identity Model Execution
- `OwnerUser` foi implementado como entidade administrativa explícita por tenant
- ele não substitui `Customer` nem `AccountProfile`
- o objetivo é abrir caminho para recipient resolver owner-facing seguro

### Escopo executado
- `accounts.models.OwnerUser`
- migration `accounts.0003_owneruser`
- teste de persistência básica
- documentação de domínio/accounts

### Próxima wave
- **Wave CW — Owner Recipient Resolver Execution**
- foco:
  - resolver owners ativos e habilitados para notificações
  - gerar `NotificationRecipientTarget` owner_user

## Wave CW — Owner Recipient Resolver Execution
- foi implementado resolver owner-facing usando `OwnerUser`
- apenas owners ativos e com `receives_notifications=True` geram targets
- o resolver é tenant-scoped e não usa `AccountProfile`

### Escopo executado
- `notification_owner_recipient_resolver.py`
- `resolve_owner_recipient_targets`
- testes de:
  - owner ativo
  - owner inativo ignorado
  - owner sem notificações ignorado
  - owner de outro tenant ignorado

### Próxima wave
- **Wave CX — Owner Event Log Integration**
- foco:
  - criar logs owner-facing para eventos já integrados quando houver owner resolvido

## Wave CX — Owner Event Log Integration
- eventos já integrados agora podem criar logs owner-facing quando houver owner elegível
- o primeiro recorte owner-facing é `payment.failed`
- `payment.paid` permanece customer-facing por enquanto, pois não há intent owner-facing no catálogo para confirmação de pagamento

### Escopo executado
- handler `record_owner_order_event_email_logs`
- integração de owner log no webhook `payment.failed`
- testes de handler owner-facing
- teste de webhook criando log customer e owner

### Próxima wave
- **Wave CY — Owner/Admin Identity Closure**
- foco:
  - fechar abordagem de owner identity
  - validar migrations/checks/testes integrados

## Wave CY — Owner/Admin Identity Closure
- a abordagem Owner/Admin Identity Implementation está fechada
- owner-facing notifications agora têm identidade administrativa explícita
- `payment.failed` cria log para customer e owner elegível

### Pronto
- `OwnerUser` persistido por tenant
- resolver owner-facing tenant-scoped
- integração owner-facing em `payment.failed`
- proteção contra uso de `AccountProfile` como fallback owner

### Ainda pendente
- UI/admin para gerenciar owners
- roles/permissões administrativas completas
- intents owner-facing adicionais
- owner-facing para `order.created` e `shipment.*` depois do publisher oficial

### Próxima abordagem natural
- **Notification Admin Operations Review**
- foco:
  - expor operação mínima para listar/ver readiness/logs no admin interno
  - sem envio real amplo ainda

## Wave CZ — Notification Admin Operations Review
- antes de uma UI administrativa completa, operações precisam de query e comando simples para inspecionar logs
- o recorte deve continuar tenant-scoped
- o objetivo é troubleshooting, não envio real

### Próxima wave
- **Wave DA — Notification Admin Log Query Execution**
- foco:
  - listar `EmailLog` por tenant/status
  - expor management command operacional

## Wave DA — Notification Admin Log Query Execution
- foi criada query admin para listar logs de e-mail por tenant
- o comando `list_email_logs` permite inspeção operacional por status

### Escopo executado
- `notification_admin_queries.py`
- `list_admin_email_logs`
- comando `list_email_logs`
- testes de query e comando

### Próxima wave
- **Wave DB — Notification Admin Operations Closure**
- foco:
  - fechar abordagem operacional mínima
  - decidir se próxima abordagem deve ser UI admin ou provider real

## Wave DB — Notification Admin Operations Closure
- a abordagem de operações administrativas mínimas está fechada
- já existem comandos para:
  - readiness por tenant
  - processamento em lote
  - listagem de logs por tenant/status

### Decisão de encerramento
- não criar UI admin agora
- próxima abordagem natural: **Notification Provider Rollout Plan**
- motivo:
  - já há dry-run, logs, renderer, CTA, readiness e operação
  - o próximo bloqueio para piloto real é configuração/provider e rollout controlado

## Wave DC — Notification Provider Rollout Plan
- provider real não deve ser ligado sem readiness explícita de configuração
- o primeiro passo é checar dry-run, backend de e-mail e remetente padrão
- credenciais reais continuam fora do repositório e devem vir por ambiente

### Próxima wave
- **Wave DD — Notification Provider Readiness Check Execution**
- foco:
  - criar checker de configuração
  - expor comando operacional

## Wave DD — Notification Provider Readiness Check Execution
- foi criado checker de readiness do provider de notifications
- o comando `notification_provider_readiness` informa se envio real pode ser tentado

### Escopo executado
- `notification_provider_readiness.py`
- `NotificationProviderReadiness`
- comando `notification_provider_readiness`
- testes de blockers e configuração mínima

### Próxima wave
- **Wave DE — Notification Provider Rollout Closure**
- foco:
  - fechar rollout plan sem credenciais reais
  - deixar checklist operacional final

## Wave DE — Notification Provider Rollout Closure
- a abordagem Provider Rollout Plan está fechada sem armazenar credenciais no repositório
- envio real continua exigindo configuração externa e validação por comando

### Checklist antes de piloto real
- `notification_provider_readiness` sem blockers
- `notification_readiness --tenant-id <id>` revisado
- `list_email_logs --tenant-id <id>` revisado
- `process_email_logs --tenant-id <id> --limit <n>` testado em dry-run
- `NOTIFICATIONS_EMAIL_DRY_RUN=0` apenas para tenant/ambiente piloto
- rollback documentado: religar `NOTIFICATIONS_EMAIL_DRY_RUN=1`

### Decisão final da abordagem
- **Go para readiness automatizada de provider**
- **No-Go para credenciais/provider hardcoded**
- **No-Go para envio amplo sem piloto isolado**

### Próxima abordagem natural
- **Notifications Track Final Wrap-Up**
- foco:
  - consolidar todas as abordagens executadas
  - parar a recursão técnica neste eixo se não houver novo requisito externo

## Wave DF — Notifications Track Final Wrap-Up
- a trilha de notifications está tecnicamente concluída para esta fase
- o sistema evoluiu de contrato futuro para pipeline operacional em dry-run com readiness e guardrails

### Cadeia final disponível
- intents transacionais
- dispatch preview
- recipient targets customer/owner
- dispatch envelope
- `EmailLog`
- writer idempotente
- lifecycle de log
- integração `payment.failed` customer + owner
- integração `payment.paid` customer
- delivery adapter dry-run
- renderer plain-text com CTA tenant-aware
- batch command
- readiness commands
- provider readiness check
- publisher mínimo como boundary futura

### Decisão final
- notifications está pronto para:
  - dry-run operacional por tenant
  - piloto real isolado com configuração externa validada
- notifications não está pronto para:
  - envio amplo multi-tenant
  - owner/admin UI completa
  - HTML marketing/template visual
  - Celery real sem configuração de fila
  - eventos `order.created`/`shipment.*` sem publisher oficial

### Próxima macro-abordagem recomendada
- **Owner/Admin Management UI**
- alternativa técnica:
  - **Celery Email Worker Implementation**
- decisão prática:
  - como provider real depende de ambiente externo, a evolução mais segura no repositório é UI/ops para gerenciar `OwnerUser` e preparar piloto

## Wave DG — Owner Admin Services Execution
- a abordagem Owner/Admin Management UI começou pelos services de application.
- isso mantém a UI fina e evita lógica de negócio em views.

### Escopo executado
- query service para listar owners por tenant
- command service para alternar `receives_notifications`
- testes tenant-scoped

## Wave DH — Owner Admin Views Execution
- foi criada uma UI operacional mínima para owners em `/ops/owners/`.
- a tela reaproveita o template de listagem administrativa existente.
- a ação disponível alterna a elegibilidade do owner para notificações administrativas.

### Próxima wave
- **Wave DI — Owner/Admin Management UI Closure**
- foco:
  - validar a surface
  - registrar limites restantes

## Wave DI — Owner/Admin Management UI Closure
- a abordagem Owner/Admin Management UI está fechada.
- owners agora podem ser inspecionados e ter notificações ativadas/desativadas por tenant.

### Pronto
- `OwnerUser` explícito
- resolver owner-facing
- integração owner-facing em `payment.failed`
- listagem operacional `/ops/owners/`
- toggle de `receives_notifications`

### Ainda pendente
- criação/edição completa de owners pela UI
- roles/permissões reais
- autenticação/autorização administrativa formal nessa surface

### Próxima abordagem natural
- **Celery Email Worker Boundary**
- foco:
  - preparar task/worker fino que reaproveite o command application
  - manter execução síncrona/management command como fallback

## Wave DJ — Celery Email Worker Boundary Execution
- Celery já estava configurado no projeto com autodiscover.
- foram criadas tasks finas em `notifications.tasks`.
- as tasks chamam `email_delivery_commands`, sem acessar adapter/model lifecycle diretamente.

### Escopo executado
- `process_email_log_task`
- `process_planned_email_logs_task`
- testes chamando `.run()` sem worker real
- batch limitado e tenant-scoped

### Próxima wave
- **Wave DK — Celery Email Worker Closure**
- foco:
  - documentar comandos/tasks disponíveis
  - validar que worker real continua opcional para esta fase

## Wave DK — Celery Email Worker Closure
- a abordagem Celery Email Worker Boundary está fechada.
- worker real pode ser ligado futuramente sem mudar a regra de delivery.

### Operação disponível
- management command:
  - `process_email_logs --tenant-id <id> --limit <n>`
- Celery tasks:
  - `notifications.process_email_log`
  - `notifications.process_planned_email_logs`

### Decisão de encerramento
- manter dry-run como default.
- Celery é boundary de execução, não dono da regra.
- próxima abordagem natural: **Notification Production Pilot Runbook**.

## Wave DL — Notification Production Pilot Runbook
- o piloto real deve ser executado por tenant, com volume pequeno e rollback simples.
- não deve haver envio amplo multi-tenant sem observabilidade adicional.

### Pré-check
1. configurar backend/provider de e-mail por ambiente
2. configurar `DEFAULT_FROM_EMAIL`
3. manter `NOTIFICATIONS_EMAIL_DRY_RUN=1`
4. gerar eventos reais ou fixtures de `EmailLog`
5. rodar `notification_provider_readiness`
6. rodar `notification_readiness --tenant-id <id>`
7. rodar `list_email_logs --tenant-id <id>`

### Dry-run operacional
1. rodar `process_email_logs --tenant-id <id> --limit 5`
2. conferir logs como `skipped`
3. conferir `notification_readiness --tenant-id <id>`
4. validar CTAs e recipients

### Piloto real isolado
1. reduzir backlog para volume conhecido
2. desligar dry-run apenas no ambiente/tenant piloto: `NOTIFICATIONS_EMAIL_DRY_RUN=0`
3. rodar `notification_provider_readiness`
4. processar lote pequeno:
   - management command, ou
   - Celery task `notifications.process_planned_email_logs`
5. conferir status `sent`/`failed`
6. se houver falha inesperada, religar `NOTIFICATIONS_EMAIL_DRY_RUN=1`

### Critérios de sucesso
- zero cross-tenant logs
- recipients corretos
- CTAs absolutos válidos
- falhas rastreáveis em `EmailLog.last_error`
- rollback testado

### Critérios de No-Go
- provider readiness com blockers
- owners sem configuração revisada
- backlog desconhecido
- falhas não explicadas
- ausência de rollback operacional

### Próxima abordagem natural
- **Notification Metrics/Prometheus Integration**
- foco:
  - expor contadores de status/falhas para monitoramento real

## Wave DM — Notification Metrics/Prometheus Review
- métricas de notifications devem seguir o padrão já usado em payments.
- o primeiro recorte deve expor contadores de `EmailLog` por tenant e status.
- o endpoint precisa ficar protegido por token operacional.

### Próxima wave
- **Wave DN — Notification Email Log Metrics Execution**
- foco:
  - exportar contadores Prometheus
  - expor endpoint protegido

## Wave DN — Notification Email Log Metrics Execution
- foi criado exporter Prometheus para contadores de `EmailLog`.
- o endpoint `/notifications/metrics/email-logs/` exige `NOTIFICATIONS_OBSERVABILITY_TOKEN`.

### Escopo executado
- `notification_metrics_queries.py`
- `NotificationMetricsView`
- rota `notifications:email-log-metrics`
- setting `NOTIFICATIONS_OBSERVABILITY_TOKEN`
- testes de exporter e endpoint

### Próxima wave
- **Wave DO — Notification Metrics Closure**
- foco:
  - validar e registrar como Prometheus deve fazer scrape

## Wave DO — Notification Metrics Closure
- a abordagem Notification Metrics/Prometheus Integration está fechada.
- Prometheus já pode fazer scrape do endpoint quando `NOTIFICATIONS_OBSERVABILITY_TOKEN` estiver configurado.

### Scrape
- URL:
  - `/notifications/metrics/email-logs/`
- autenticação:
  - header `X-Hubx-Observability-Token`
  - ou `Authorization: Bearer <token>`
- métrica principal:
  - `hubx_notifications_email_log_total{tenant_id,status}`

### Limites
- ainda não há métricas de latência.
- ainda não há métricas de provider/bounce.
- ainda não há dashboard Grafana.

### Próxima abordagem natural
- **Notification Grafana Dashboard Spec**
- foco:
  - especificar painel inicial com backlog, falhas, sent/skipped e tenant drilldown

## Wave DP — Notification Grafana Dashboard Spec
- o dashboard inicial deve consumir `hubx_notifications_email_log_total`.
- o objetivo é operação de rollout, não análise de marketing.

### Painéis iniciais
- **Backlog planejado por tenant**
  - query: `sum by (tenant_id) (hubx_notifications_email_log_total{status="planned"})`
  - uso: detectar fila acumulada antes/depois de processamento
- **Falhas por tenant**
  - query: `sum by (tenant_id) (hubx_notifications_email_log_total{status="failed"})`
  - uso: priorizar investigação operacional
- **Sent vs skipped**
  - query: `sum by (status) (hubx_notifications_email_log_total{status=~"sent|skipped"})`
  - uso: comparar envio real vs dry-run
- **Distribuição por status**
  - query: `sum by (status) (hubx_notifications_email_log_total)`
  - uso: visão geral do pipeline

### Alert rules iniciais
- **NotificationFailedLogsPresent**
  - expressão: `sum(hubx_notifications_email_log_total{status="failed"}) > 0`
  - severidade: warning
  - ação: revisar `list_email_logs --status failed`
- **NotificationBacklogHigh**
  - expressão: `sum(hubx_notifications_email_log_total{status="planned"}) > 100`
  - severidade: warning
  - ação: verificar worker/batch e dry-run

### Limites conhecidos
- métrica atual é gauge por estado persistido, não contador de eventos por minuto
- não mede latência entre created/requested/sent
- não mede bounce/provider rejection

### Próxima abordagem natural
- **Notification Alert Rules Execution**
- foco:
  - materializar regras Prometheus em arquivo versionado de infra/docs

## Wave DQ — Notification Alert Rules Execution
- regras Prometheus de notifications foram versionadas em `infra/observability`.
- também foi adicionado exemplo de scrape protegido por `NOTIFICATIONS_OBSERVABILITY_TOKEN`.

### Escopo executado
- `infra/observability/prometheus/notifications-alert-rules.yml`
- `infra/observability/prometheus/notifications-scrape.example.yml`
- atualização do runbook de observability

### Regras iniciais
- `HubxNotificationsFailedLogsPresent`
- `HubxNotificationsBacklogHigh`
- `HubxNotificationsRequestedStuck`

### Próxima abordagem natural
- **Notification Grafana Dashboard Execution**
- foco:
  - materializar dashboard JSON inicial para Grafana

## Wave DR — Notification Grafana Dashboard Execution
- dashboard inicial de Grafana foi versionado em `infra/observability`.
- o painel cobre backlog, falhas, distribuição por status e drilldown tenant/status.

### Escopo executado
- `infra/observability/grafana/notifications-email-logs-dashboard.json`
- atualização do runbook de observability

### Próxima abordagem natural
- **Notification Observability Final Review**
- foco:
  - validar JSON
  - fechar observabilidade de notifications nesta fase

## Wave DS — Notification Observability Final Review
- a abordagem de observabilidade de notifications está fechada nesta fase.
- o sistema agora possui exporter, scrape example, alert rules e dashboard inicial.

### Pronto
- endpoint Prometheus protegido:
  - `/notifications/metrics/email-logs/`
- métrica:
  - `hubx_notifications_email_log_total{tenant_id,status}`
- scrape example:
  - `infra/observability/prometheus/notifications-scrape.example.yml`
- alert rules:
  - `infra/observability/prometheus/notifications-alert-rules.yml`
- dashboard:
  - `infra/observability/grafana/notifications-email-logs-dashboard.json`

### Ainda pendente
- métricas de latência de delivery
- métricas de provider/bounce
- roteamento Alertmanager específico de notifications

### Próxima macro-abordagem recomendada
- **Notification Alertmanager Routing**
- foco:
  - versionar exemplo de rota Alertmanager para alertas de notifications

## Wave DT — Notification Alertmanager Routing Execution
- foi criado exemplo de roteamento Alertmanager para alertas de notifications.
- o arquivo segue o padrão já usado por payments.

### Escopo executado
- `infra/observability/alertmanager/notifications-routing.example.yml`
- atualização do runbook de observability

### Próxima abordagem natural
- **Notification Observability Wrap-Up**
- foco:
  - validar arquivos de observability
  - fechar essa sequência de operação/monitoramento

## Wave DU — Notification Observability Wrap-Up
- a sequência de observability de notifications está fechada.
- há cobertura versionada para scrape, alert rules, dashboard e routing.

### Pronto
- endpoint de métricas no app
- scrape Prometheus example
- alert rules Prometheus
- dashboard Grafana
- routing Alertmanager example

### Próxima macro-abordagem recomendada
- **Order Created Event Publisher**
- motivo:
  - notifications já tem delivery/observability suficientes
  - o próximo desbloqueio funcional é publicar `order.created` por boundary clara em vez de acoplar checkout diretamente

## Wave DV — Order Created Event Publisher Review
- `order.created` precisava de uma boundary explícita antes de gerar notifications.
- o checkout continua sendo o ponto atual de materialização do pedido, mas não deve conhecer detalhes de notifications.
- a solução foi criar um publisher em `orders.application`.

### Decisão prática
- checkout chama `order_event_publisher.publish_order_created`
- publisher é dono da semântica `order.created`
- notifications continua como subscriber/consumidor
- writer idempotente evita duplicação de `EmailLog`

## Wave DW — Order Created Event Publisher Execution
- foi criado publisher de evento em `orders.application`.
- checkout completion publica `order.created` somente quando um novo pedido é criado.
- o evento cria logs customer-facing e owner-facing quando houver destinatários elegíveis.

### Escopo executado
- `orders.application.order_event_publisher`
- integração em `checkout_completion_commands`
- testes do publisher
- teste de checkout criando `EmailLog`:
  - `customer.order.received`
  - `owner.order.created`

### Próxima wave
- **Wave DX — Order Created Event Publisher Closure**
- foco:
  - validar idempotência/replay
  - registrar limites restantes

## Wave DX — Order Created Event Publisher Closure
- a abordagem `order.created` está fechada.
- checkout publica por boundary de `orders`, e notifications consome sem acoplamento direto com checkout.

### Pronto
- `order.created` customer-facing:
  - `customer.order.received`
- `order.created` owner-facing:
  - `owner.order.created`
- publisher testado
- checkout completion testado
- replay de sessão concluída não recria pedido nem republica logs

### Ainda pendente
- transformar publisher in-process em event bus distribuído no futuro
- adicionar métricas específicas de publicação/consumo de eventos

### Próxima macro-abordagem recomendada
- **Shipping Event Publisher**
- motivo:
  - `shipment.sent` e `shipment.delivered` ainda estão no catálogo de notifications
  - precisam de fluxo/publisher claro em shipping antes de integração real

## Wave DY — Shipping Event Publisher Review
- `shipment.sent` e `shipment.delivered` já existem no catálogo de notifications.
- o módulo `shipping`, porém, ainda não possui `Shipment` real ou fluxo operacional de tracking.
- a integração automática fica bloqueada até existir shipment persistido.

## Wave DZ — Shipping Event Publisher Execution
- foi criada boundary de publisher em `shipping.application`.
- ela prepara a integração futura sem disparar eventos falsos.

### Escopo executado
- `shipping.application.shipping_event_publisher`
- testes unitários do publisher

### Próxima wave
- **Wave EA — Shipping Event Publisher Closure**

## Wave EA — Shipping Event Publisher Closure
- a boundary de eventos logísticos está pronta.
- notifications não dispara envio fake porque `shipping` ainda não possui `Shipment` real.

### Próxima macro-abordagem recomendada
- **Shipment Minimal Model & Commands**
- foco:
  - criar persistência mínima de shipment/tracking
  - criar comandos tenant-scoped para envio/entrega
  - só então ligar `shipment.sent` e `shipment.delivered`

## Wave EB — Shipment Minimal Model Execution
- `Shipment` mínimo foi implementado no módulo `shipping`.

## Wave EC — Shipment Command Execution
- comandos de shipment agora publicam eventos logísticos reais.
- `shipment.sent` gera log customer-facing.
- `shipment.delivered` gera log customer-facing e owner-facing.

### Próxima wave
- **Wave ED — Shipment Minimal Model & Commands Closure**

## Wave ED — Shipment Minimal Model & Commands Closure
- notifications agora tem integração real com shipping via comandos tenant-scoped.
- `shipment.sent` e `shipment.delivered` deixam de ser apenas intenções futuras quando acionados por `shipping.application.shipment_commands`.
- a entrega só publica evento depois que a remessa foi marcada como enviada.

### Próximo limite fora de notifications
- falta uma UI/admin operacional para operadores chamarem esses comandos sem acesso direto ao shell/código.

## Wave EE — Shipping Admin Operations UI Execution
- `/ops/shipping/` agora aciona os comandos de shipment.
- notifications recebe logs reais quando a operação interna marca envio ou entrega.

### Impacto
- `customer.shipment.sent` fica acionável pela operação interna.
- `customer.shipment.delivered` fica acionável pela operação interna.
- `owner.shipment.delivered` fica acionável pela operação interna.

## Wave EG — Orders Shipping Command Integration
- atalhos logísticos de `/ops/orders/` agora também passam pelos comandos de shipment.
- isso reduz o risco de pedido em trânsito/entregue sem evento correspondente de notifications.

## Wave FH — Notifications Operational Parity Review
- a revisão mostrou que notifications já tinha:
  - readiness geral
  - readiness de provider
  - listagem tenant-scoped de `EmailLog`
  - processamento tenant-scoped de lote
  - endpoint Prometheus
  - scrape, alert rules, dashboard e routing
- a lacuna principal era a ausência de runbook dedicado.

### Escopo executado
- `docs/modules/notifications-operational-runbook.md`
- consolidação de:
  - variáveis principais
  - readiness provider
  - readiness por tenant
  - triagem de logs
  - processamento de lote
  - observabilidade
  - diagnóstico rápido

### Leitura operacional
- não houve mudança no pipeline de delivery.
- a operação de notifications agora fica no mesmo padrão documental de shipping e payments.

### Próxima macro-abordagem recomendada
- **Notifications Retention/Triage Review**
- motivo:
  - o runbook deixa explícito que ainda não há pruning de `EmailLog`; vale decidir se a próxima evolução deve ser triagem mais rica ou retenção segura.

## Wave FI — Notifications Stale Log Triage Execution
- a listagem operacional de `EmailLog` passou a aceitar filtro por idade.
- a decisão foi não implementar pruning de `EmailLog` nesta fase.

### Escopo executado
- `list_email_logs --stale-hours=<horas>`
- filtro combinado com:
  - `--tenant-id`
  - `--status`
  - `--limit`
- teste cobrindo log `requested` antigo sem listar log recente do mesmo tenant
- runbook atualizado com comando para logs travados

### Leitura operacional
- `EmailLog` é trilha útil de entrega e auditoria de comunicação.
- antes de remover registros, o sistema precisa de política de retenção mais clara.
- triagem stale já ajuda a investigar:
  - backlog em `planned`
  - entregas presas em `requested`
  - falhas que exigem reprocessamento/suporte

### Próxima macro-abordagem recomendada
- **Notifications Operational Wrap-Up Review**
- motivo:
  - notifications agora tem runbook, triagem por idade e observability completa para esta fase.

## Wave FJ — Notifications Operational Wrap-Up Review
- o pacote operacional de notifications pode ser considerado completo para esta fase.
- a abordagem consolidou operação e triagem sem alterar o pipeline de geração/entrega.

### O que ficou pronto
- runbook dedicado:
  - `docs/modules/notifications-operational-runbook.md`
- readiness:
  - `notification_readiness`
  - `notification_provider_readiness`
- triagem:
  - `list_email_logs`
  - `list_email_logs --stale-hours`
- processamento:
  - `process_email_logs`
- observabilidade:
  - scrape Prometheus
  - alert rules
  - dashboard Grafana
  - routing Alertmanager

### O que fica fora de escopo
- pruning de `EmailLog`
- arquivamento frio
- métricas de latência de delivery
- métricas de bounce/rejection do provider
- reprocessamento automático de falhas

### Leitura objetiva
- notifications agora está em paridade operacional com shipping e payments.
- os três domínios críticos de operação pós-compra têm runbook e observabilidade básica.

### Próxima macro-abordagem recomendada
- **Operational Docs Index Review**
- motivo:
  - já existem runbooks separados; o próximo passo é criar um índice operacional único para navegar shipping, payments e notifications.
