# Validação UI Admin SaaS, Planos Públicos e Aquisições

Data: 2026-07-01

Alvo local: `http://127.0.0.1:8002`

## Evidências

- `03-plans-desktop-fixed.png`: primeira dobra pública desktop.
- `04-plans-mobile-fixed.png`: primeira dobra pública mobile.
- `05-plans-success.png`: formulário público após POST com lead fictício.
- `06-acquisitions-list.png`: fila platform de aquisições.
- `07-acquisition-detail.png`: detalhe do lead em leitura.
- `08-acquisition-detail-actions.png`: estado read-only do card de ações.

## Fluxo Validado

- `/plans/` renderiza planos ativos, hero com imagem raster realista e cards de plano.
- Formulário público criou um lead fictício para `valida-browser-41002378` sem provisionar tenant, owner, assinatura, catálogo ou cobrança.
- `/ops/platform/acquisitions/` listou o lead criado com status `Novo`.
- `/ops/platform/acquisitions/1/` exibiu dados do lead, plano solicitado e contato.
- Sessão sem role explícita exibiu estado read-only no detalhe, sem ações de conversão/descarte.

## Ajustes Feitos Durante A Validação

- Corrigido contraste do H1 do hero público para branco explícito sobre a imagem.
- Corrigido header público responsivo: labels visíveis no desktop e compactos no mobile via media query local.
- Corrigido badge `Recomendado` para não sobrepor o título do plano.
- Ajustado texto da fila platform para `Aquisição platform`, `1 lead` e meta sem texto interno de compatibilidade.
- Ajustado detalhe da aquisição para usar o mesmo idioma e mostrar mensagem read-only no card de ações quando falta permissão de gestão.

## Observações

- A sessão do navegador validada não possuía `platform.tenants.manage`; por isso a auditoria visual cobriu o estado seguro de leitura. Os botões de conversão/descarte continuam condicionados à permissão de gestão e devem ser exercitados com sessão autenticada de owner/admin em validação posterior.
