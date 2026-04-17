# UI PR Checklist

Use esta checklist antes de aprovar ou mergear mudanças de UI no `Hubx.market`.

## Reuso e estrutura

- [ ] Reutilizei components oficiais sempre que possível
- [ ] Evitei duplicar markup já resolvido pelo Design System
- [ ] Se criei algo novo, deixei claro se é `component`, `composite`, `pattern` ou `page template`
- [ ] Não introduzi caminhos legados novos quando já existe caminho oficial

## Tokens, tema e multi-tenant

- [ ] Respeitei tokens e temas existentes
- [ ] Não hardcodei branding em component compartilhado
- [ ] Considerei `data-tenant` e `data-ui-context` quando a mudança afeta aparência global
- [ ] Considerei o preview interno de tenant/theme quando a mudança visual é relevante

## Component API

- [ ] Mantive props previsíveis e consistentes com o restante do sistema
- [ ] Reusei `variant`, `size`, `state` e props opcionais antes de criar APIs paralelas
- [ ] Evitei lógica complexa em components base
- [ ] Se a API mudou, atualizei `ui/docs/component-api.md`

## Composição e patterns

- [ ] Mantive composites finos e reutilizáveis
- [ ] Não transformei composição de página em component sem recorrência comprovada
- [ ] Se usei HTMX, a integração ficou previsível e localizada
- [ ] Estados de `loading`, `empty`, `error` e `disabled` foram considerados quando aplicável

## Showcase e documentação

- [ ] Atualizei o showcase interno quando a mudança afeta components ou page templates oficiais
- [ ] Mantive a distinção entre demos de components e prévias de page templates
- [ ] Se a mudança afeta adoção do time, deixei exemplos claros de uso
- [ ] Se a mudança for estrutural, avaliei se outros docs de `ui/docs/` também precisam de ajuste

## Validação

- [ ] Validei sintaxe dos templates Django afetados
- [ ] Revisei includes, caminhos e wrappers legados impactados
- [ ] Confirmei que a mudança continua segura para admin, storefront e checkout quando aplicável
- [ ] Se a mudança visual amplia risco real, avaliei se a suíte de regressão visual precisa de um novo snapshot em `ui/docs/visual-regression.md`
- [ ] A mudança continua de baixo risco e sem lógica de negócio indevida na camada de template

## Perguntas finais

Antes do merge, consigo responder “sim” para estas perguntas?

- [ ] Esta mudança fortalece o Design System em vez de fragmentá-lo?
- [ ] Outro desenvolvedor entenderá facilmente qual bloco oficial deve reutilizar a partir daqui?
- [ ] A próxima tela semelhante conseguirá reaproveitar o que foi feito agora?
