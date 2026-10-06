# Avisos com formatação, categoria e evento · Plano

> **Para quem executa:** superpowers:executing-plans, tarefa por tarefa, com TDD
> (superpowers:test-driven-development): cada comportamento ganha antes um teste que falha.

**Objetivo:** o aviso ganha estrutura (Markdown restrito renderizado por nós), categoria (5) e,
quando é evento, "Quando / Onde"; o mural passa ao modelo A.

**Arquitetura:** categoria e evento moram em `aviso_versao` (migração 0004, só colunas e CHECKs);
a API repassa e compara na correção; o front tem um analisador puro `texto → blocos`
(`web/src/avisos/formatacao.ts`) e um componente que transforma os blocos em elementos React,
sem `dangerouslySetInnerHTML` e sem biblioteca de Markdown.

**Pilha:** FastAPI + Pydantic 2 + SQLAlchemy 2 + Alembic (Python 3.12) · React 19 + Vitest ·
Playwright + axe no navegador.

**Spec:** `docs/superpowers/specs/2026-10-06-avisos-visual-design.md`

## Restrições globais

- Categorias, nesta ordem: `geral` (padrão), `obra`, `reuniao`, `financeiro`, `urgente`.
- `evento_onde`: 1 a 120 caracteres, sem caractere de controle; só existe com `evento_quando`.
- O `app` continua sem UPDATE em `aviso_versao`; correção é versão nova.
- Marcas aceitas: `## `, `**…**`, `- `, `1. `, `> `, linha em branco, `http(s)://`. O resto é
  texto literal.
- Fuso das datas na tela: `America/Recife`. Categoria nunca só por cor (ícone + nome).
- Nenhum `style=` em JSX (CSP); cores só por token de `estilo.css` (claro e escuro).
- Português do Brasil com acentuação em tudo; commits com `Co-Authored-By`.

## Pontos de atenção da revisão

1. Texto antigo com linha começando por `- ` vira lista (mudança visível, aceita pela spec).
2. `**` sem par, `##` sem espaço, `- ` sem texto: ficam literais, nunca somem.
3. Evento no passado e evento sem local: o quadro e o mural não podem quebrar.
4. Correção que muda só a categoria ou só o evento não pode dar `sem_mudanca`.
5. Hora do evento digitada no formulário é de Recife (−03:00), não do aparelho.

---

### Tarefa 1 · Migração 0004 e modelo

**Arquivos:** `api/migracoes/versions/0004_categoria_e_evento_do_aviso.py`,
`api/app/modelos/avisos.py`, `api/testes/test_migracoes.py`, `api/testes/test_avisos_banco.py`,
`api/testes/conftest.py` (sem mudança de tabela).

- Testes primeiro: check de categoria (`aviso_versao_categoria`), de `onde` sem `quando`
  (`aviso_versao_evento_completo`) e de tamanho do `onde` (`aviso_versao_evento_onde_tamanho`),
  direto no banco como `app`; `app` sem UPDATE nas colunas novas; migração com aviso existente
  (versão anterior à 0004) vira `geral` sem evento; downgrade da 0004 volta à 0003 e sobe de novo.
- Implementar a 0004 no padrão da 0002/0003 (`_papel_app`, SQL à mão, grant explícito de
  `select, insert` ao `app`) e as colunas/CHECKs iguais no modelo (o `test_modelos` compara).
- Commit.

### Tarefa 2 · API: esquemas, serviço e `resumir`

**Arquivos:** `api/app/esquemas/avisos.py`, `api/app/servicos/avisos.py`,
`api/testes/test_avisos_visual.py` (novo), `api/testes/test_contrato.py`,
`web/src/avisos/tipos.ts`, `docs/superpowers/specs/m1-contrato.md`.

- `Categoria(StrEnum)`; `Evento(Entrada)`: `quando: datetime` (com fuso) e `onde: str | None`.
- `NovoAviso`/`CorrigirAviso`: `categoria = geral`, `evento: Evento | None = None`.
- `AvisoResumo`: `categoria`, `evento_quando`; `AvisoCompleto` e `VersaoAviso`: `categoria`,
  `evento`.
- Testes: categoria inválida 422; `onde` sem `quando` 422; data sem fuso 422; correção que muda
  só categoria/evento cria versão e a anterior guarda os valores dela; conta comum não publica;
  `resumir` sem marcas.
- Tipos TS e contrato atualizados (o `test_contrato` confere). Commit.

### Tarefa 3 · Renderizador e barra de marcas (funções puras)

**Arquivos:** `web/src/avisos/formatacao.ts` (+ teste), `web/src/avisos/marcas.ts` (+ teste).

- `analisar(texto): Bloco[]` (parágrafo com linhas, título, lista, lista numerada, destaque) e
  `trechos(linha): Trecho[]` (texto, negrito, link http(s)).
- `aplicarMarca(texto, inicio, fim, marca)` para a barra (Título, Negrito, Lista, Destaque).
- Testes de cada marca, malformadas, `<script>`, `<img onerror>`, `javascript:`,
  `[x](javascript:…)`, texto antigo. Commit.

### Tarefa 4 · Tokens, ícones e componentes do aviso

**Arquivos:** `web/src/estilo.css` (tokens `--cat-*`), `web/src/casca/Icone.tsx` (ícones novos),
`web/src/avisos/categorias.ts`, `web/src/avisos/componentes.tsx`, `web/src/avisos/avisos.css`,
`web/src/avisos/Mural.tsx`, `web/src/avisos/AvisoAberto.tsx`, `web/src/avisos/telas.test.tsx`.

- `TextoDoAviso` passa a usar o renderizador; `CorpoDoAviso` (cabeçalho com data em bloco,
  categoria, assinatura e destino; quadro Quando/Onde; texto) é usado no aviso aberto, nas
  versões antigas e na prévia.
- Mural modelo A: faixa, data em bloco, rótulo da categoria, resumo, linha do evento
  ("Sáb, 11/10 · 9h" ou "Já aconteceu").
- Testes de tela antes. Commit.

### Tarefa 5 · Formulário (novo e corrigir)

**Arquivos:** `web/src/avisos/Formularios.tsx`, `web/src/avisos/telas.test.tsx`.

- Categoria em 5 rádios de verdade; barra de marcas; "Ver como fica"; "É um evento?" com dia,
  hora e local; ajuda curta das marcas. Corrigir vem com categoria e evento da versão em vigor.
- Testes: barra insere marca, prévia, chave de evento manda `evento`, categoria vai no corpo.
  Commit.

### Tarefa 6 · Navegador, revisão independente e fechamento

- Script Playwright próprio (`docs/superpowers/prints/avisos-visual/verificar-avisos-visual.mjs`):
  320/390/1366, claro/escuro, CSP, rolagem lateral, axe no mural, aviso (com e sem evento, com
  versão antiga) e formulário (escrever e prévia); categoria por setas do teclado.
- Dois revisores sem contexto (UX "Dona Socorro" e código/segurança); corrigir os confirmados
  com teste de regressão; registrar descartes em `docs/superpowers/duvidas-avisos-visual.md`.
- Tudo verde: pytest, pyright, ruff, lint, typecheck, npm test, build, migração do zero.
