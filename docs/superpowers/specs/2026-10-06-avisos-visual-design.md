# Spec · Avisos com formatação, categoria e evento

| | |
|---|---|
| **Data** | 06/10/2026 |
| **Marco** | entre o M1 e o M2 (não depende do ensaio nem da Comissão) |
| **Branch** | `avisos/visual` |
| **Decidido com** | o Erick, no brainstorm de 06/10/2026 (mockups no visual companion) |

## 1. Por quê

O mural é uma lista de títulos e o aviso aberto é texto corrido. O primeiro aviso real (boas-vindas)
precisou de MAIÚSCULAS para imitar título de seção. O grupo gosta de coisa "organizadinha": o
aviso precisa de estrutura (seções, listas, destaque), de um jeito de saber do que se trata antes
de abrir (categoria) e, quando é um evento, de "quando e onde" sem caçar no texto.

## 2. Decisões do Erick

1. **Mural no modelo A:** cartão com faixa lateral na cor da categoria, data da publicação em
   bloco à esquerda (dia grande, mês abreviado embaixo), rótulo da categoria com ícone acima do
   título, resumo embaixo. O fixado continua com o fundo ipê, e ganha a categoria.
2. **Aviso aberto com formatação + quadro de evento:** cabeçalho com a data em bloco e a categoria;
   se for evento, um quadro "Quando / Onde" logo abaixo do cabeçalho; depois o texto formatado.
3. **Categorias:** Geral (padrão), Obra, Reunião, Financeiro, Urgente.

## 3. Decisões do coordenador

### 3.1 Formato do texto: Markdown restrito, guardado como texto

O texto continua na coluna `aviso_versao.texto` (mesmo limite de 10.000 caracteres). Marcas aceitas,
e só elas:

| Marca | Vira |
|---|---|
| linha que começa com `## ` | título de seção (h2 dentro do aviso; o h1 é o título do aviso) |
| `**trecho**` dentro de uma linha | negrito |
| linhas seguidas começando com `- ` | lista com marcador |
| linhas seguidas começando com `1. `, `2. `… | lista numerada |
| linhas seguidas começando com `> ` | caixa de destaque (fundo ipê suave, ícone de informação) |
| linha em branco | separa parágrafos |
| endereço `http(s)://` | link, como já é hoje |

Todo o resto é texto literal: `#` sozinho, `###`, `*itálico*`, `<b>`, `![img]()`, tabelas, HTML,
crase. **O renderizador é nosso** (função pura `texto → árvore de elementos React`), sem
`dangerouslySetInnerHTML` e sem biblioteca de Markdown: o subconjunto é pequeno e assim nenhum
caminho transforma texto em HTML. Texto antigo sem marca nenhuma aparece exatamente como hoje
(parágrafos e quebras de linha; o `white-space: pre-line` atual vira parágrafos e `<br>`).

Rejeitados: editor visual com JSON (dependência pesada, versão difícil de comparar, validação
nova no servidor) e HTML sanitizado (porta de XSS, conflita com a CSP).

**Resumo do mural** (`resumir` em `servicos/avisos.py`): passa a tirar as marcas antes de cortar
(`## `, `**`, `- `, `1. `, `> `), para o resumo nunca mostrar asterisco. A busca continua sobre o
texto bruto.

### 3.2 Categoria e evento ficam na versão

Migração **0004** (mesmo padrão da 0002/0003: grants ao `app`, upgrade/downgrade/upgrade testado):

- `aviso_versao.categoria text not null default 'geral'` com check em
  `('geral','obra','reuniao','financeiro','urgente')`. Fica na versão (não no aviso) porque corrigir
  pode mudar a categoria e o "ver como era antes" precisa mostrar a antiga.
- `aviso_versao.evento_quando timestamptz null` e `aviso_versao.evento_onde text null`
  (`onde` com limite de 120 caracteres, sem caractere de controle, como o título). Check: `onde`
  só existe se `quando` existir (evento sem data não é evento; local é opcional).
- Linhas existentes: `geral`, sem evento. A trigger de versão da 0003 (aviso arquivado) continua.
- O `app` continua sem UPDATE em `aviso_versao` (correção é versão nova).

**Produção:** aplicar a 0004 no Neon (conexão direta do dono) **antes** do push, senão a restauração
de teste do backup reprova (head ≠ produção).

### 3.3 API

- `NovoAviso` e `CorrigirAviso` ganham `categoria` (padrão `geral`) e `evento` opcional
  `{quando: datetime com fuso, onde: str | null}`. `quando` no passado é aceito (aviso sobre algo
  que já aconteceu é legítimo); validação de texto igual à do título para `onde`.
- `AvisoResumo` (mural) ganha `categoria` e `evento_quando`; `AvisoCompleto` e `VersaoAviso` ganham
  `categoria` e `evento` (o histórico de versões mostra o que mudou).
- Contrato atualizado em `docs/superpowers/specs/m1-contrato.md` e tipos TS em `web/src/avisos/`.

### 3.4 Telas

- **Mural (modelo A):** faixa lateral de 5px na cor da categoria; bloco de data com fundo suave
  da categoria; rótulo "ÍCONE CATEGORIA" em maiúsculas pequenas acima do título; selos "Novo" e
  "Corrigido" continuam. **Bloco de data (decisão do Erick, 06/10, depois da revisão de UX):** no
  aviso que é evento, o bloco mostra o dia do **evento** (fuso America/Recife; o ano entra no
  bloco quando não é o ano corrente); nos outros, o da publicação. O evento ganha uma linha com
  ícone de calendário que não repete a data: "Sáb, 9h · publicado 6/10" e, se já passou, "Já
  aconteceu · publicado 6/10". O leitor de tela ouve o que o bloco é: "Evento em 11 de outubro" ou
  "Publicado em 6 de outubro". A ordem do mural continua pela publicação (fixados primeiro). O
  fixado não tem bloco: a linha do evento dele é "Sáb, 11/10 · 9h".
- **Aviso aberto:** cabeçalho com bloco de data (mesma regra: evento → dia do evento) + categoria
  + h1 + "quem publicou · para quem" (a frase "Publicado pela … em …" continua com a publicação);
  quadro Quando/Onde (cartão branco, ícones de calendário e local) quando houver evento; texto
  pelo renderizador; o "Corrigido em… / Ver como era antes" continua, e a versão antiga também é
  renderizada formatada, com categoria e evento dela.
- **Formulário (novo e corrigir):** categoria em 5 botões com ícone e nome (rádio acessível);
  barra **Título · Negrito · Lista · Destaque** que insere a marca na seleção/linha do textarea;
  botão "Ver como fica" alterna entre escrever e a prévia renderizada (mesmo componente do aviso
  aberto); chave "É um evento?" que mostra Quando (data + hora, `input type=date` e `type=time`) e
  Onde. Uma linha de ajuda curta embaixo do texto explica as marcas para quem preferir digitar.
- **Cores por categoria** (tokens novos em `estilo.css`, claro e escuro, cada par com contraste
  ≥ 4,5:1 para o texto do rótulo e ≥ 3:1 para a faixa): `--cat-geral`, `--cat-obra` (terra),
  `--cat-reuniao` (azul), `--cat-financeiro` (mata), `--cat-urgente` (erro), cada um com `-suave`.
  Categoria nunca só por cor: sempre ícone + nome.
- **Ícones:** os da biblioteca que o app já usa para os outros ícones; se não houver, SVG próprio
  no mesmo traço (2px, cantos arredondados).

## 4. Fica de fora

Adicionar à agenda do celular (.ics); filtro do mural por categoria; imagens no texto (anexos são
do M3); itálico, tabela, título de nível 3.

## 5. Testes

- Renderizador: cada marca; marcas malformadas viram texto; `<script>`, `<img onerror>`,
  `javascript:` e `[x](javascript:…)` nunca viram elemento nem link; texto antigo (sem marca)
  produz o mesmo resultado visual de hoje; link só `http(s)`.
- `resumir` sem marcas.
- API: categoria inválida 422; `onde` sem `quando` 422; correção muda categoria/evento e a versão
  antiga guarda os valores dela; permissões continuam (conta comum não publica).
- Banco: check de categoria e de `onde` sem `quando` direto no banco; migração do zero
  (upgrade/downgrade/upgrade) e com dados (avisos existentes viram `geral`).
- Front (Vitest): mural com categoria, evento futuro e passado; aviso aberto com quadro; formulário
  (barra insere marca, prévia, chave de evento, categoria por teclado).
- Navegador (Playwright próprio): 320/390/1366, claro e escuro, CSP sem violação, sem rolagem
  horizontal, axe no mural, aviso aberto (com e sem evento) e formulário.
- Revisão independente (UX + código) antes do merge, como no M1.

## 6. Pronto quando

Tudo verde (pytest, pyright, ruff, lint, typecheck, npm test, build, migração do zero), revisão
independente feita e corrigida, 0004 aplicada no Neon antes do push, e o aviso de boas-vindas
reescrito no formato novo (texto aprovado pelo Erick antes de publicar a correção).
