# Component API

Este documento é a referência interna dos componentes oficiais já implementados no Design System do `Hubx.market`.

Objetivos:

- padronizar nomenclatura de `props`, `variants`, `sizes`, `states` e `slots`
- reduzir ambiguidade entre admin, storefront e checkout
- servir como fonte de verdade para implementação e reuso em Django templates

## Convenções

### Props transversais

Quando fizer sentido, componentes devem preferir estas props:

- `variant`
- `size`
- `disabled`
- `loading`
- `title`
- `label`
- `description`
- `items`
- `actions`

### Estados padrão

Nem todo componente implementa todos os estados abaixo, mas esta é a matriz padrão do Design System:

- `default`
- `hover`
- `focus`
- `active`
- `disabled`
- `loading`
- `error`
- `empty`
- `processing`

### Naming

- `props` em `snake_case`
- `variants` em `snake_case` ou rótulos simples previsíveis
- `sizes` em escala curta: `xs`, `sm`, `md`, `lg`
- `slots` representam regiões de conteúdo opcional ou blocos injetáveis

---

## Form Components

### `button.html`

- **Purpose:** ação principal ou secundária do usuário
- **Variants:** `primary`, `secondary`, `ghost`, `danger`, `success`, `link`
- **Sizes:** `sm`, `md`, `lg`
- **States:** `default`, `hover`, `focus`, `disabled`, `loading`
- **Props:** `label`, `type`, `href`, `icon_name`, `icon_right_name`, `icon_left`, `icon_right`, `loading`, `disabled`, `full_width`
- **Slots:** nenhum
- **Example usage:**

```django
{% include "shared/components/actions/button.html" with label="Salvar" variant="primary" type="submit" %}
```

```django
{% include "shared/components/actions/button.html" with label="Descartar" variant="danger" icon_name="alert-triangle" %}
```

### `input.html`

- **Purpose:** entrada textual base para formulários
- **Variants:** `default`
- **Sizes:** `sm`, `md`, `lg`
- **States:** `default`, `focus`, `disabled`, `invalid`
- **Props:** `name`, `label`, `value`, `placeholder`, `prefix`, `suffix`, `help_text`, `error_text`, `invalid`, `disabled`, `id`, `input_type`
- **Slots:** `prefix`, `suffix`
- **Accessibility:** renderiza `aria-invalid`, associa ajuda/erro via `aria-describedby` e marca `required` visualmente.
- **Example usage:**

```django
{% include "shared/components/forms/input.html" with name="email" label="E-mail" input_type="email" %}
```

### `select.html`

- **Purpose:** seleção simples com opções vindas do backend
- **Variants:** `default`
- **Sizes:** `sm`, `md`, `lg`
- **States:** `default`, `focus`, `disabled`, `invalid`
- **Props:** `name`, `label`, `options`, `selected`, `placeholder`, `help_text`, `error_text`, `invalid`, `disabled`, `multiple`, `id`
- **Slots:** nenhum
- **Accessibility:** segue o mesmo contrato de `aria-invalid`, `aria-describedby` e `required` de `input.html`.
- **Example usage:**

```django
{% include "shared/components/forms/select.html" with name="segment" label="Segmento" options=segment_options selected=selected_segment %}
```

### `textarea.html`

- **Purpose:** entrada de texto longo
- **Variants:** `default`
- **Sizes:** `md`, `lg`
- **States:** `default`, `focus`, `disabled`, `invalid`
- **Props:** `name`, `label`, `value`, `rows`, `placeholder`, `help_text`, `error_text`, `invalid`, `disabled`, `id`
- **Slots:** nenhum
- **Accessibility:** usa `ds-textarea`, `aria-invalid` e `aria-describedby` para ajuda/erro.
- **Example usage:**

```django
{% include "shared/components/forms/textarea.html" with name="description" label="Descrição" rows=4 %}
```

### `checkbox.html`

- **Purpose:** escolha booleana ou múltipla
- **Variants:** `default`
- **Sizes:** `sm`, `md`
- **States:** `default`, `checked`, `disabled`, `invalid`
- **Props:** `name`, `label`, `description`, `value`, `checked`, `disabled`, `error_text`, `invalid`, `id`
- **Slots:** nenhum
- **Accessibility:** descrição e erro são associados ao controle por `aria-describedby`.
- **Example usage:**

```django
{% include "shared/components/forms/checkbox.html" with name="accept_terms" label="Aceito os termos" checked=True %}
```

### `radio.html`

- **Purpose:** escolha única entre opções
- **Variants:** `default`
- **Sizes:** `sm`, `md`
- **States:** `default`, `checked`, `disabled`, `invalid`
- **Props:** `name`, `label`, `description`, `value`, `checked`, `disabled`, `error_text`, `invalid`, `id`
- **Slots:** nenhum
- **Accessibility:** descrição e erro são associados ao controle por `aria-describedby`.
- **Example usage:**

```django
{% include "shared/components/forms/radio.html" with name="plan" value="pro" label="Plano Pro" checked=True %}
```

### `switch.html`

- **Purpose:** toggle de ativação rápida
- **Variants:** `default`
- **Sizes:** `sm`, `md`
- **States:** `default`, `checked`, `disabled`, `invalid`
- **Props:** `name`, `label`, `description`, `value`, `checked`, `disabled`, `error_text`, `invalid`, `id`
- **Slots:** nenhum
- **Accessibility:** descrição e erro são associados ao controle por `aria-describedby`.
- **Example usage:**

```django
{% include "shared/components/forms/switch.html" with name="featured" label="Destacar loja" checked=True %}
```

### `field_help.html`

- **Purpose:** texto auxiliar curto associado a um campo
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`
- **Props:** `text`, `help_text`, `id`
- **Slots:** nenhum
- **Example usage:**

```django
{% include "shared/components/forms/field_help.html" with text="Texto visível apenas para apoio ao preenchimento." %}
```

### `field_error.html`

- **Purpose:** mensagem de erro associada a um campo
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `error`
- **Props:** `text`, `error_text`, `id`
- **Slots:** nenhum
- **Accessibility:** renderiza `role="alert"`.
- **Example usage:**

```django
{% include "shared/components/forms/field_error.html" with text="Campo obrigatório." %}
```

### `form_actions.html`

- **Purpose:** agrupador de ações primárias e secundárias de formulário
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`, `disabled`, `loading`
- **Props:** `primary_label`, `primary_variant`, `primary_type`, `secondary_label`, `secondary_href`, `loading`, `disabled`
- **Slots:** nenhum
- **Example usage:**

```django
{% include "shared/components/forms/form_actions.html" with primary_label="Salvar" secondary_label="Cancelar" secondary_href=cancel_url %}
```

---

## Data Display, Navigation, Feedback, and Overlays

### `card.html`

- **Purpose:** card base para agrupamento visual de conteúdo e ações leves
- **Variants:** `default`
- **Sizes:** `md`, `lg`
- **States:** `default`, `hover`
- **Props:** `title`, `subtitle`, `content`, `footer`, `actions`, `clickable`, `padding`
- **Slots:** `actions`, `content`, `footer`
- **Example usage:**

```django
{% include "shared/components/data_display/card.html" with title="Resumo" subtitle="Bloco base" content="Conteúdo do card." %}
```

### `table.html`

- **Purpose:** tabela base para dados estruturados e renderização simples de linhas/colunas
- **Variants:** `default`, `compact`
- **Sizes:** nenhum
- **States:** `default`, `empty`
- **Props:** `columns`, `rows`, `empty_message`, `table_id`, `caption`, `table_label`
- **Slots:** nenhum
- **Example usage:**

```django
{% include "shared/components/data_display/table.html" with columns=columns rows=rows empty_message="Sem registros." %}
```

**Accessibility notes**

- Cabeçalhos usam `scope="col"`.
- Use `caption` para contexto lido por tecnologia assistiva quando a tabela estiver dentro de uma composição complexa.
- Use `table_label` quando não houver título/caption disponível.

### `badge.html`

- **Purpose:** status curto e reutilizável
- **Variants:** `neutral`, `success`, `warning`, `danger`, `info`, `active`, `inactive`, `pending`, `paid`, `shipped`, `delivered`
- **Sizes:** `xs`, `sm`
- **States:** `default`
- **Props:** `label`, `icon`, `icon_name`, `variant`, `size`
- **Slots:** `icon`
- **Example usage:**

```django
{% include "shared/components/data_display/badge.html" with label="Pago" variant="paid" %}
```

**Implementation notes**

- Helpers em views devem emitir `ds-badge` + variante semântica (`ds-badge-success`, `ds-badge-warning`, `ds-badge-danger`, `ds-badge-info` ou `ds-badge-neutral`).
- Não usar classes Tailwind de cor para status renderizado pelo backend.

### `pagination.html`

- **Purpose:** navegação entre páginas de listagem
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`, `disabled`, `active`
- **Props:** `page`, `total_pages`, `prev_url`, `next_url`, `page_items`
- **Slots:** nenhum
- **Example usage:**

```django
{% include "shared/components/navigation/pagination.html" with page=2 total_pages=8 prev_url="?page=1" next_url="?page=3" page_items=page_items %}
```

**Accessibility notes**

- A página atual usa `aria-current="page"`.
- Estados sem link usam `aria-disabled="true"`.

### `tabs.html`

- **Purpose:** alternância entre painéis ou contextos relacionados
- **Variants:** `default`
- **Sizes:** `sm`, `md`
- **States:** `default`, `active`, `disabled`
- **Props:** `items`, `active_key`, `aria_label`
- **Slots:** nenhum
- **Accessibility:** item ativo usa `aria-current="page"`; item desabilitado usa `aria-disabled` e sai do tab order quando for link.
- **Example usage:**

```django
{% include "shared/components/navigation/tabs.html" with items=tabs active_key="orders" %}
```

### `breadcrumb.html`

- **Purpose:** navegação hierárquica curta para contexto e retorno
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`
- **Props:** `items`, `aria_label`
- **Slots:** nenhum
- **Accessibility:** último item recebe `aria-current="page"`.
- **Example usage:**

```django
{% include "shared/components/navigation/breadcrumb.html" with items=breadcrumbs %}
```

### `page_header.html`

- **Purpose:** cabeçalho consistente para páginas internas
- **Variants:** `default`
- **Sizes:** `md`, `lg`
- **States:** `default`
- **Props:** `eyebrow`, `title`, `description`, `meta`, `actions`
- **Slots:** `actions`
- **Example usage:**

```django
{% include "shared/components/layout/page_header.html" with title="Pedidos" description="Gerencie o fluxo operacional da loja." %}
```

### `stat_card.html`

- **Purpose:** indicador resumido para dashboards e analytics
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`
- **Props:** `title`, `subtitle`, `value`, `delta`, `trend`, `icon`
- **Slots:** nenhum
- **Example usage:**

```django
{% include "shared/components/data_display/stat_card.html" with title="Receita" value="R$ 42.500" delta="+12,4%" trend="positive" %}
```

**Implementation notes**

- Renderiza `ds-stat-card` e `ds-trend`; use `trend="positive"` ou `trend="negative"` para deltas.
- Use em dashboards/admin; não recriar cards de KPI com HTML local.

### `chart_card.html`

- **Purpose:** card analítico com título, métrica, delta e região opcional para gráfico
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`
- **Props:** `title`, `description`, `value`, `delta`, `trend`, `meta`, `actions`, `chart`, `footer`, `showcase_mode`
- **Slots:** `actions`, `chart`, `footer`
- **Example usage:**

```django
{% include "shared/components/data_display/chart_card.html" with title="Vendas" value="R$ 12.400" delta="+8,2%" trend="positive" chart=chart_markup %}
```

**Implementation notes**

- Renderiza `ds-chart-card`; `showcase_mode` usa barras tokenizadas apenas para preview visual.
- Gráficos reais devem ser passados pelo slot/prop `chart`, mantendo o frame do DS.

### `activity_feed.html`

- **Purpose:** feed cronológico compacto para eventos de usuário, sistema e integrações
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`, `empty`
- **Props:** `title`, `description`, `items`, `empty_title`, `empty_description`, `showcase_mode`
- **Slots:** nenhum
- **Example usage:**

```django
{% include "shared/components/data_display/activity_feed.html" with title="Atividade recente" items=activity_items %}
```

### `audit_log.html`

- **Purpose:** tabela estruturada de auditoria para eventos críticos do sistema
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`, `empty`
- **Props:** `title`, `description`, `entries`, `empty_title`, `empty_description`, `showcase_mode`
- **Slots:** nenhum
- **Example usage:**

```django
{% include "shared/components/data_display/audit_log.html" with title="Log de auditoria" entries=audit_entries %}
```

### `data_table.html`

- **Purpose:** bloco reutilizável de listagem administrativa com toolbar, tabela, paginação e empty state
- **Variants:** `default`, `dense`, `selectable`
- **Sizes:** nenhum
- **States:** `default`, `empty`
- **Props:** `title`, `description`, `count`, `columns`, `rows`, `table_id`, `caption`, `table_label`, `actions`, `selection_count`, `bulk_actions`, `page`, `total_pages`, `prev_url`, `next_url`, `page_items`, `empty_icon`, `empty_title`, `empty_description`, `empty_primary_action`, `empty_secondary_action`, `hx_target_id`
- **Slots:** `actions`, `bulk_actions`
- **Example usage:**

```django
{% include "shared/components/data_display/data_table.html" with title="Pedidos" columns=columns rows=rows page=page_obj.number total_pages=page_obj.paginator.num_pages %}
```

**Implementation notes**

- Prefira `filter_bar.html` para filtros complexos ou HTMX acima da tabela.
- `data_table.html` deve preservar o mesmo `hx_target_id` entre loading, empty e rows para updates parciais previsíveis.

**Legacy-supported props**

Estas props ainda são aceitas por compatibilidade, mas filtros complexos devem preferir `filter_bar.html`:

- `search_name`
- `search_value`
- `search_label`
- `search_placeholder`
- `filters`

### `data_table_toolbar.html`

- **Purpose:** toolbar de apoio para listagens administrativas com título, busca, filtros, contagem e ações
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`
- **Props:** `title`, `description`, `count`, `search_name`, `search_value`, `search_label`, `search_placeholder`, `filters`, `actions`, `selection_count`, `bulk_actions`
- **Slots:** `filters`, `actions`, `bulk_actions`
- **Example usage:**

```django
{% include "shared/components/composite/data_table_toolbar.html" with title="Pedidos" count=orders_count actions=toolbar_actions %}
```

**Implementation notes**

- Busca simples usa input `type="search"` e tamanho compacto.
- A barra de seleção usa superfície tokenizada e deve aparecer apenas quando houver seleção real.

### `bulk_actions_bar.html`

- **Purpose:** barra de ações em massa para itens selecionados em listagens
- **Variants:** `default`, `danger`
- **Sizes:** nenhum
- **States:** `default`
- **Props:** `selection_count`, `actions`
- **Slots:** `actions`
- **Example usage:**

```django
{% include "shared/components/composite/bulk_actions_bar.html" with selection_count=selected_count actions=bulk_actions %}
```

### CSS-only page primitives

- **Purpose:** primitives compartilhadas sem partial próprio para superfícies pequenas.
- **Classes oficiais:** `ds-link-card`, `ds-link-danger`, `ds-progress`, `ds-progress-bar`, `ds-subpanel`, `ds-callout-list`, `ds-plan-card`, `ds-public-option-icon`.
- **Usage:** usar em templates quando a estrutura local for simples demais para novo component include, mas ainda precisar de tokenização DS.
- **Rule:** não combinar backgrounds/bordas Tailwind para recriar essas superfícies.

### `filter_bar.html`

- **Purpose:** barra de busca e filtros para listagens e catálogos
- **Variants:** `default`, `accordion`
- **Sizes:** nenhum
- **States:** `default`
- **Props:** `method`, `action`, `hx_get`, `hx_post`, `hx_target`, `hx_swap`, `title`, `description`, `search_name`, `search_value`, `search_label`, `search_placeholder`, `status_name`, `status_selected`, `status_label`, `status_placeholder`, `status_options`, `extra_filters`, `submit_label`, `reset_url`, `reset_label`, `show_actions`, `accordion`, `accordion_open`
- **Slots:** `extra_filters`
- **Example usage:**

```django
{% include "shared/components/composite/filter_bar.html" with search_name="q" search_value=request.GET.q reset_url=reset_url %}
```

**HTMX/accessibility notes**

- Quando usar HTMX, sempre informe `hx_target` e `hx_swap`.
- O loading indicator usa `aria-live="polite"`.
- A variante accordion usa `<details>`/`<summary>` nativos para teclado.

### `empty_state.html`

- **Purpose:** fallback visual para ausência de conteúdo
- **Variants:** `default`, `search`, `filter`, `first_run`, `error`
- **Sizes:** `md`, `lg`
- **States:** `empty`
- **Props:** `icon`, `icon_name`, `title`, `description`, `primary_action`, `secondary_action`, `centered`, `size`
- **Slots:** `primary_action`, `secondary_action`
- **Accessibility:** o ícone é decorativo; título e descrição carregam o significado.
- **Example usage:**

```django
{% include "shared/components/feedback/empty_state.html" with title="Nenhum produto encontrado" description="Ajuste os filtros para continuar." %}
```

### `alert.html`

- **Purpose:** mensagem contextual persistente para informação, sucesso, aviso ou erro
- **Variants:** `info`, `success`, `warning`, `danger`
- **Sizes:** nenhum
- **States:** `default`
- **Props:** `title`, `description`, `icon`, `icon_name`, `dismissible`
- **Slots:** nenhum
- **Accessibility:** `danger`/`error` usam `role="alert"`; demais variantes usam `role="status"`.
- **Example usage:**

```django
{% include "shared/components/feedback/alert.html" with variant="info" title="Informação" description="Mensagem contextual." %}
```

### `dropdown.html`

- **Purpose:** menu simples de ações leves
- **Variants:** `default`, `secondary`
- **Sizes:** `sm`, `md`
- **States:** `default`, `open`
- **Props:** `label`, `title`, `items`, `trigger`, `open`
- **Slots:** `trigger`
- **Accessibility:** usa `<details>/<summary>` nativos; itens desabilitados usam `aria-disabled` ou `disabled`.
- **Example usage:**

```django
{% include "shared/components/overlays/dropdown.html" with label="Ações" items=menu_items %}
```

### `drawer.html`

- **Purpose:** painel lateral contextual
- **Variants:** `default`
- **Sizes:** `md`, `lg`
- **States:** `default`, `open`
- **Props:** `open`, `title`, `description`, `body`, `footer`, `dismissible`, `id`
- **Slots:** `body`, `footer`
- **Accessibility:** quando aberto, renderiza `role="dialog"`, `aria-modal`, `aria-labelledby` e `aria-describedby` quando há descrição.
- **Example usage:**

```django
{% include "shared/components/feedback/drawer.html" with open=True title="Resumo do pedido" body=drawer_body %}
```

### `modal.html`

- **Purpose:** overlay de foco para confirmação, formulário ou conteúdo contextual
- **Variants:** `default`
- **Sizes:** `sm`, `md`, `lg`
- **States:** `default`, `open`
- **Props:** `open`, `title`, `description`, `body`, `primary_action`, `secondary_action`, `dismissible`, `id`
- **Slots:** `body`, `primary_action`, `secondary_action`
- **Accessibility:** quando aberto, renderiza `role="dialog"`, `aria-modal`, `aria-labelledby` e `aria-describedby` quando há descrição.
- **Example usage:**

```django
{% include "shared/components/feedback/modal.html" with open=True title="Confirmar ação" body=modal_body %}
```

### `public_hero.html`

- **Purpose:** hero oficial para superfícies públicas centrais do SaaS
- **Variants:** `default`
- **Sizes:** responsivo
- **States:** `default`
- **Props:** `hero_image_url`, `hero_eyebrow`, `hero_title`, `hero_description`, `primary_label`, `primary_href`, `primary_icon`, `secondary_label`, `secondary_href`, `secondary_icon`, `tertiary_label`, `tertiary_href`, `tertiary_icon`
- **Slots:** nenhum
- **Example usage:**

```django
{% include "shared/partials/public_hero.html" with hero_title="Escolha o plano para criar sua loja virtual." primary_label="Iniciar onboarding" primary_href="#aquisicao" %}
```

**Implementation notes**

- Usa asset raster real e classes `public-hero-*` do DS.
- Não inserir `<style>` local nem hero baseado em cards.

---

## Commerce / Storefront Components

### `product_card.html`

- **Purpose:** card genérico de catálogo/listagem para storefront
- **Variants:** `default`, `featured`, `compact`
- **Sizes:** nenhum
- **States:** `default`, `hover`
- **Props:** `href`, `image_url`, `image_alt`, `eyebrow`, `title`, `subtitle`, `badge_label`, `badge_variant`, `price`, `compare_price`, `price_helper`, `meta`, `stock_state`, `stock_label`, `stock_helper`, `action_label`, `actions`, `clickable`
- **Default CTA:** `Comprar`, levando ao `href` do produto para confirmar variante, quantidade e compra.
- **Slots:** `actions`
- **DS contract:** `ds-product-card`, `ds-product-card-media`, `ds-product-card-body`, `ds-product-card-commerce`, `ds-product-card-actions`
- **Accessibility:** `img` deve receber `image_alt` ou cair para `title`; links mantêm o título textual visível.
- **Example usage:**

```django
{% include "shared/components/composite/product_card.html" with href=product.href title=product.title price=product.price stock_state=product.stock_state clickable=True %}
```

### `order_summary.html`

- **Purpose:** resumo composable do pedido para checkout, customer area e contexto administrativo
- **Variants:** `checkout`, `customer`, `admin`
- **Sizes:** nenhum
- **States:** `default`
- **Props:** `title`, `description`, `steps`, `items`, `subtotal`, `shipping`, `discount`, `installments`, `total`, `note`, `actions`, `showcase_mode`
- **Slots:** `actions`
- **DS contract:** `ds-order-summary`, `ds-order-summary-items`, `ds-order-summary-totals`, `ds-order-summary-actions`
- **Example usage:**

```django
{% include "shared/components/composite/order_summary.html" with items=order_items subtotal=subtotal total=grand_total actions=summary_actions %}
```

### `checkout_steps.html`

- **Purpose:** indicador de progresso do checkout
- **Variants:** `default`, `compact`
- **Sizes:** nenhum
- **States:** `default`
- **Props:** `steps`, `aria_label`, `showcase_mode`
- **Slots:** nenhum
- **DS contract:** `ds-checkout-steps`, `ds-checkout-step`, `ds-checkout-step-marker`, `ds-checkout-step-connector`
- **Accessibility:** etapa atual usa `aria-current="step"`; `aria_label` deve nomear o fluxo quando houver mais de um stepper na página.
- **Example usage:**

```django
{% include "shared/components/composite/checkout_steps.html" with steps=checkout_steps %}
```

### `cart_item.html`

- **Purpose:** item reutilizável para carrinho, review e resumo
- **Variants:** `default`, `compact`, `checkout`
- **Sizes:** nenhum
- **States:** `default`
- **Props:** `image_url`, `image_alt`, `title`, `subtitle`, `meta`, `price`, `compare_price`, `quantity`, `actions`, `compact`, `quantity_readonly`
- **Slots:** `actions`
- **DS contract:** `ds-cart-item`, `ds-cart-item-media`, `ds-cart-item-body`, `ds-cart-item-controls`, `ds-cart-item-actions`
- **Example usage:**

```django
{% include "shared/components/commerce/cart_item.html" with title=item.title price=item.price quantity=item.quantity %}
```

### `price_display.html`

- **Purpose:** exibição reutilizável de preço, comparativo e helper
- **Variants:** `default`, `sale`, `muted`, `emphasis`
- **Sizes:** `sm`, `md`, `lg`
- **States:** `default`
- **Props:** `value`, `compare_value`, `helper`, `align`
- **Slots:** nenhum
- **DS contract:** `ds-price`, `ds-price-row`, `ds-price-amount`, `ds-price-compare`, `ds-price-helper`
- **Example usage:**

```django
{% include "shared/components/commerce/price_display.html" with value="R$ 299,90" compare_value="R$ 349,90" helper="ou 3x de R$ 99,97" %}
```

### `quantity_selector.html`

- **Purpose:** controle visual simples de quantidade
- **Variants:** `default`, `compact`
- **Sizes:** `sm`, `md`
- **States:** `default`, `disabled`
- **Props:** `value`, `disabled`, `decrement_type`, `increment_type`, `decrement_label`, `increment_label`
- **Slots:** nenhum
- **DS contract:** `ds-quantity-selector`, `ds-quantity-btn`, `ds-quantity-value`
- **Accessibility:** botões expõem `aria-label`; valor usa `aria-live="polite"` para atualizações parciais.
- **Example usage:**

```django
{% include "shared/components/commerce/quantity_selector.html" with value=2 %}
```

### `payment_method_selector.html`

- **Purpose:** seleção de forma de pagamento em checkout
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`, `disabled`
- **Props:** `name`, `methods`, `selected`
- **Slots:** nenhum
- **DS contract:** `ds-choice-list`, `ds-choice-card`, `ds-choice-radio`, `ds-choice-title`, `ds-choice-description`, `ds-choice-meta`
- **Method contract:** cada `method` aceita `label`, `value`, `description`, `meta`, `badge`, `badge_variant`, `checked`, `disabled`.
- **Example usage:**

```django
{% include "shared/components/commerce/payment_method_selector.html" with methods=payment_methods selected=payment_method_selected %}
```

### `shipping_method_selector.html`

- **Purpose:** seleção de forma de entrega em checkout
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`, `disabled`
- **Props:** `name`, `methods`, `selected`, `showcase_mode`
- **Slots:** nenhum
- **DS contract:** `ds-choice-list`, `ds-choice-card`, `ds-choice-radio`, `ds-choice-row`, `ds-choice-title`, `ds-choice-description`, `ds-choice-meta`
- **Method contract:** cada `method` aceita `label`, `value`, `description`, `meta`, `price`, `checked`, `disabled`.
- **Example usage:**

```django
{% include "shared/components/commerce/shipping_method_selector.html" with methods=shipping_methods selected=shipping_method_selected %}
```

### `product_gallery.html`

- **Purpose:** galeria de produto com imagem principal e thumbs
- **Variants:** `default`
- **Sizes:** nenhum
- **States:** `default`, `empty`
- **Props:** `title`, `items`, `images`, `main_image_url`, `main_image_alt`, `aria_label`, `showcase_mode`
- **Slots:** nenhum
- **DS contract:** `ds-product-gallery`, `ds-product-gallery-main`, `ds-product-gallery-visual`, `ds-product-gallery-thumbs`, `ds-product-gallery-thumb`
- **Example usage:**

```django
{% include "shared/components/commerce/product_gallery.html" with title=product.name items=gallery_items %}
```

### `variant_selector.html`

- **Purpose:** seleção de variações de produto com opções estruturadas vindas do backend
- **Variants:** `buttons`, `chips`, `swatches`, `dropdown`
- **Sizes:** nenhum
- **States:** `default`, `selected`, `disabled`, `out_of_stock`, `error`
- **Props:** `name`, `label`, `options`, `selected`, `placeholder`, `help_text`, `error_text`, `invalid`, `variant`, `showcase_mode`
- **Slots:** nenhum
- **DS contract:** `ds-variant-selector`, `ds-variant-list`, `ds-variant-option`, `ds-variant-chip`, `ds-variant-swatch`
- **Example usage:**

```django
{% include "shared/components/commerce/variant_selector.html" with name="size" label="Tamanho" variant="buttons" options=size_options selected=selected_size %}
```

**Option contract**

Cada item em `options` deve usar:

- obrigatórias: `label`, `value`
- opcionais: `selected`, `disabled`, `out_of_stock`, `meta`, `color`

### `stock_indicator.html`

- **Purpose:** comunicar disponibilidade de produto de forma curta
- **Variants:** `in_stock`, `low_stock`, `out_of_stock`, `backorder`
- **Sizes:** `xs`, `sm`
- **States:** `default`
- **Props:** `state`, `label`, `helper`, `size`
- **Slots:** nenhum
- **DS contract:** `ds-stock-indicator`, `ds-stock-helper`
- **Example usage:**

```django
{% include "shared/components/commerce/stock_indicator.html" with state="low_stock" helper="Restam 4 unidades" %}
```

---

## Remaining Documentation Gaps

Nenhum gap conhecido para os contratos de commerce/checkout cobertos nesta onda. Próximas mudanças devem ampliar exemplos reais por tenant quando novos estados forem adicionados.
