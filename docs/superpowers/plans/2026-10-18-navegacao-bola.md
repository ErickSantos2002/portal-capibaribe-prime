# Navegação do celular com a bola do Menu — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No celular, uma barra com arco, 4 abas e uma bola "Menu" que abre uma folha com todos os
lugares explicados. Tudo sai de uma lista única que também alimenta o menu lateral agrupado do
computador.

**Architecture:** `casca/menu.ts` vira a lista única de lugares (`Lugar`). `Navegacao.tsx` desenha
a barra do celular (as entradas com `naBarra`, mais a bola) e o menu lateral agrupado. Um
componente novo, `casca/MenuFolha.tsx`, é um `<dialog>` aberto com `showModal()`, que tem dentro
a bola-X de fechar. `casca/letra.ts` ganha a marca `data-largura="estreita"`, usada pelo rótulo
"Docs". A barra tem tamanho fixo, com medidas `min(<rem>, <vw>)`.

**Tech Stack:** React 19 + TS, react-router 8, CSS puro (`web/src/estilo.css`), vitest + jsdom,
`node --test` para os testes de CSS (`web/testes/`), Playwright headless para a conferência
(`scripts/dev/conferir-letra.mjs`).

**Spec:** `docs/superpowers/specs/2026-10-18-navegacao-bola-design.md`. Leia o spec inteiro antes
da Tarefa 1. Os desenhos de referência ficam em
`.superpowers/brainstorm/222262-1792337475/content/` (`navbar.html` opção C, `menu.html` opção 1,
`menu-muitos.html`). São só para ler o código: **não abra no navegador**.

## Global Constraints

- **Nenhuma janela de navegador visível**, em nenhum momento. Nada de MCP playwright nem de Chrome
  ou Firefox abertos. Só scripts com `headless: true`. O dono usa o PC enquanto você trabalha.
- Regra do M5 (guarda em `web/testes/letra.test.ts`): letra em rem, sem unidade, ou
  `min(<rem>, <vw>)` como teto. Espaço em rem. px só em borda, canto, foco e sombra (ou com
  `/* px: motivo */`). **Nenhuma media query de tamanho**: largura via `@container raiz (… rem)`,
  e o resto via marcas no `<html>` (`casca/letra.ts`).
- A barra do celular nunca passa de **104 px** de altura total a 16, 24 e 32 px de letra (a
  saliência da bola conta; a safe-area não conta). A letra da barra tem **piso de 15 px** e não
  acompanha a letra grande.
- Rótulos: "Avisos", "Enquetes", "Documentos" ("Docs" só com `data-largura="estreita"`, ou seja,
  `innerWidth < 340`), "Minha unidade", e a bola: "Menu" / "Fechar". Título da folha: "Para onde
  você quer ir?". Grupos: "Dia a dia" e "Gestão".
- Frases: Avisos "Recados da Comissão e da obra" · Enquetes "Vote pela sua unidade" · Documentos
  "Memorial, atas e contratos" · Minha unidade "Senha, contato e e-mail" · Unidades "Quem já
  entrou e os contatos". O lugar atual troca a frase por "Você está aqui".
- `<nav aria-label="Seções do Portal">` continua existindo, porque os testes de `rotas.test.tsx`
  dependem dele.
- O tema escuro tem tokens próprios para a bola, com contraste ≥ 3:1 entre o ícone e o fundo.
  Nada de hex solto no CSS da barra (exceto dentro dos tokens).
- Versão **1.7.0** em `web/package.json`, com o item em `web/src/sobre/novidades.ts` **no mesmo
  commit**.
- Commits com o e-mail pessoal (já configurado no repo) e terminando em
  `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`. O pre-commit tem que
  passar, sem `--no-verify`.

## Review Focus

1. **O voltar do Android com a folha aberta:** fecha a folha e não sai da página nem reabre a
   folha depois. O teste fica na Tarefa 4: o evento `cancel`/`close` fecha, e a navegação não usa
   `pushState`.
2. **Tocar num lugar dentro da folha:** navega e fecha. O foco não fica preso num dialog que saiu
   do DOM, e o voltar seguinte leva à tela anterior, não ao menu. Teste na Tarefa 4.
3. **A letra a 32 px num celular de 320 px:** sem rolagem lateral, com a barra ≤ 104 px e "Docs"
   no lugar de "Documentos". Teste na Tarefa 5 (conferência) e na Tarefa 3 (CSS).
4. **Lugar atual fora da barra** (`/unidades`, `/unidades/1101`, `/historico`): a bola fica acesa
   e nenhuma aba fica `aria-current`. Teste na Tarefa 3.
5. **O último cartão da lista não fica escondido atrás da bola:** o `main` tem `padding-bottom` e
   `scroll-padding-bottom` ≥ a altura da barra. Teste na Tarefa 3 (CSS) e conferido na Tarefa 5.

---

### Tarefa 1: Lista única de lugares

**Files:**
- Modify: `web/src/casca/menu.ts`, `web/src/documentos/menu.ts`, `web/src/enquetes/votar/menu.ts`
- Modify: `web/src/m3contrato.test.ts`, `web/src/m4contrato.test.ts` (só se as asserções sobre
  `itensDoMenu` mudarem)
- Test: `web/src/casca/menu.test.ts` (novo)

**Interfaces:**
- Produces:
  ```ts
  export type Grupo = 'dia-a-dia' | 'gestao'
  export const NOMES_DOS_GRUPOS: Record<Grupo, string> // 'Dia a dia', 'Gestão'
  export interface Lugar {
    para: string; icone: NomeDoIcone; texto: string
    curto?: string          // rótulo da barra estreita ("Docs")
    frase: string; grupo: Grupo
    naBarra?: 1 | 2 | 3 | 4 // posição fixa: 1,2 à esquerda da bola; 3,4 à direita
  }
  export function lugaresDo(eu: Eu): Lugar[]              // todos os que valem para eu, na ordem
  export function daBarra(lugares: Lugar[]): (Lugar | null)[] // sempre 4 posições; null = vaga
  export function agrupados(lugares: Lugar[]): { grupo: Grupo; nome: string; lugares: Lugar[] }[]
  export function lugarAtual(lugares: Lugar[], pathname: string): Lugar | undefined // prefixo mais longo
  ```
  `Item` e `itensDoMenu` saem. `itemEnquetes`/`itemDocumentos` passam a devolver `Lugar | null`.

- [ ] **Passo 1: testes que falham** em `menu.test.ts`:
  - `lugaresDo(morador)` → textos `['Avisos','Enquetes','Documentos','Minha unidade']`;
    `lugaresDo(comissão)` e `lugaresDo(admin)` → mais `'Unidades'` no fim, com `grupo: 'gestao'`
    e sem `naBarra`.
  - `daBarra(lugaresDo(qualquer papel)).map(l => l?.texto)` →
    `['Avisos','Enquetes','Documentos','Minha unidade']`.
  - Sem um lugar da barra (lista sem Enquetes) → `daBarra` devolve `null` na posição 2, e
    ninguém sobe.
  - Todo lugar tem `frase` não vazia, e Documentos tem `curto: 'Docs'`.
  - `agrupados` do admin → `[{nome:'Dia a dia', 4 lugares}, {nome:'Gestão', ['Unidades']}]`. O
    do morador não tem o grupo Gestão (grupo vazio some).
  - `lugarAtual(l, '/unidades/1101')?.texto === 'Unidades'`;
    `lugarAtual(l, '/avisos/12')?.texto === 'Avisos'`; `lugarAtual(l, '/historico')` →
    `undefined`.
  - Invariante: nenhum lugar com `naBarra` repetido.
- [ ] **Passo 2:** `cd web && npx vitest run src/casca/menu.test.ts`, e eles têm que falhar.
- [ ] **Passo 3:** implementar em `menu.ts`, com as frases e os rótulos das Global Constraints.
  Atualizar `itemEnquetes`/`itemDocumentos` (com `naBarra` 2 e 3, `grupo: 'dia-a-dia'`).
- [ ] **Passo 4:** `npx vitest run`. A suíte inteira tem que passar. Ajustar só as asserções do
  m3/m4contrato que citam `itensDoMenu`, mantendo o que elas provam (a ordem e quem vê).
- [ ] **Passo 5:** commit `feat(web): lista única de lugares do menu (navegação com bola)`.

### Tarefa 2: Marca de tela estreita

**Files:** Modify `web/src/casca/letra.ts`. Test `web/src/casca/letra.test.tsx`.

**Interfaces:** Produces `export const LARGURA_ESTREITA_PX = 340`. O `<html>` ganha
`data-largura="estreita"` quando `window.innerWidth < 340` e perde a marca quando passa disso,
sempre no mesmo `atualizar()` do `resize`. `classificar(raizPx, alturaPx, larguraPx)` devolve
também `estreita: boolean`.

- [ ] **Passo 1: testes que falham:** `classificar(16, 800, 320).estreita === true`,
  `classificar(32, 800, 360).estreita === false` (a letra não interfere). Com `vigiarLetra()` e
  `innerWidth = 320` + evento `resize`, o `<html>` fica com `dataset.largura === 'estreita'`. Em
  412, a marca some.
- [ ] **Passo 2:** rodar e ver falhar.
- [ ] **Passo 3:** implementar e atualizar o comentário do topo de `letra.ts` (a terceira marca e
  por que ela é em px reais: a letra da barra não cresce).
- [ ] **Passo 4:** `npx vitest run src/casca/letra.test.tsx` tem que passar.
- [ ] **Passo 5:** commit.

### Tarefa 3: A barra do celular e o menu lateral agrupado

**Files:**
- Modify: `web/src/casca/Navegacao.tsx`, `web/src/estilo.css` (seção "navegação: abas embaixo
  no celular" e o bloco `@container raiz (min-width: 56.25rem)` da `.nav`), `web/index.html`
  (`viewport-fit=cover`)
- Modify: `web/src/casca/Icone.tsx` (ícone `grade`, 9 pontos, e `fechar`, X, com traço único
  como os outros)
- Test: `web/src/casca/navegacao.test.tsx` (novo), `web/testes/navegacao-bola.test.ts` (novo,
  CSS), `web/src/rotas.test.tsx` (manter verde)

**Interfaces:**
- Consumes: `lugaresDo`, `daBarra`, `agrupados`, `lugarAtual` (Tarefa 1); `data-largura`
  (Tarefa 2).
- Produces: `<Navegacao eu>` renderiza, dentro do `<nav aria-label="Seções do Portal">`:
  `.nav-barra` (celular: 4 posições e a bola no meio) e `.nav-lateral` (computador: grupos com
  `<h2 class="nav-grupo">`, no lugar dos links soltos de hoje; a marca, a placa e o
  `BotaoVersao` continuam). O CSS mostra uma ou outra pelo `@container raiz`. A bola é
  `<button type="button" class="nav-bola" aria-haspopup="dialog" aria-expanded={aberta}>` com
  o ícone `grade` e o texto "Menu". Ela recebe `data-aqui` quando `lugarAtual` não está na
  barra. Até a Tarefa 4, o clique só alterna o estado `aberta`. O rótulo da aba com `curto`
  rende `<span class="rot-longo">Documentos</span><span class="rot-curto" aria-hidden>Docs</span>`,
  com o CSS trocando os dois sob `[data-largura='estreita']`. O nome acessível é sempre
  "Documentos".

- [ ] **Passo 1: testes de componente que falham** (`navegacao.test.tsx`, padrão de
  `rotas.test.tsx`/`acesso/apoioDeTeste`):
  - Morador e admin: dentro de `.nav-barra`, 4 links na ordem Avisos, Enquetes, Documentos,
    Minha unidade, e um botão "Menu" entre o 2º e o 3º. "Unidades" **não** fica em
    `.nav-barra` para o admin, mas fica em `.nav-lateral`, sob o título "Gestão".
  - Em `/avisos`, o link Avisos tem `aria-current="page"`, e o contador continua
    `aria-label="3 não lidos"`.
  - Em `/unidades`: nenhum link de `.nav-barra` tem `aria-current`, e a bola tem `data-aqui`.
  - O link Documentos tem nome acessível "Documentos" mesmo com `data-largura="estreita"`.
- [ ] **Passo 2: testes de CSS que falham** (`web/testes/navegacao-bola.test.ts`, com
  `node --test`, lendo `src/estilo.css` como os outros de `web/testes/`):
  - A regra de `.nav-barra a` tem `font-size: min(0.9375rem, …vw…)` (letra que não cresce) e
    nenhum `font-size` maior dentro de `.nav-barra`.
  - Existe uma regra `[data-largura='estreita']` que esconde `.rot-longo` e mostra `.rot-curto`.
  - `.conteudo` (layout de celular com nav) tem `padding-bottom` e `scroll-padding-bottom` que
    usam a mesma variável da altura da barra (`--altura-barra`).
  - A barra usa `env(safe-area-inset-bottom)`, e o `index.html` tem `viewport-fit=cover`.
  - Os tokens da bola existem nos dois temas (`--bola-fundo`, `--bola-icone`), e a razão de
    contraste calculada entre eles é ≥ 3 em claro e em escuro (reaproveite o cálculo de contraste
    de `web/testes/revisoes-m5.test.ts` ou `estilo-m4.test.ts`, se houver; se não houver,
    escreva a fórmula WCAG no teste).
  - O guarda `web/testes/letra.test.ts` continua verde (rodar junto).
- [ ] **Passo 3:** rodar `npx vitest run src/casca/navegacao.test.tsx` e
  `node --test testes/navegacao-bola.test.ts`, e os dois têm que falhar.
- [ ] **Passo 4: implementar** a barra seguindo a seção 3 do spec:
  - Arco raso (flecha ~16 px) desenhado por CSS (`clip-path`/`mask` com `ellipse`, ou um SVG de
    fundo com `preserveAspectRatio="none"` e `fill: var(--folha)`). Os cantos transparentes não
    pegam toque (`pointer-events`).
  - Bola com saliência de no máximo meia altura, e anel em `var(--papel)`.
  - Tracinho do ativo: 3 px, com `box-shadow` da mesma cor (`/* px: … */`). A bola com
    `data-aqui` ganha o mesmo tracinho e "Menu" em negrito.
  - Colunas `1fr 1fr <bola> 1fr 1fr` com `min-content`, ou o equivalente que garanta que nada
    encoste. Todas as medidas da barra em `min(<rem>, <vw>)`.
  - `--altura-barra` como token, usado no `padding-bottom` do conteúdo.
  - O escuro da barra segue o padrão `[data-tema='escuro']` já usado em `estilo.css`.
  - Apagar as regras velhas das abas (tetos `5.5vw`/`4.3vw`, `nth-of-type(5)`, `.nav .conta` da
    aba estreita) que deixarem de valer, e atualizar os comentários que citam a dúvida 1 do M5.
  - No computador (`@container raiz (min-width: 56.25rem)`): `.nav-barra` some, e `.nav-lateral`
    mostra os grupos, com o título do grupo no estilo `.secao`, em tom claro sobre o verde.
- [ ] **Passo 5:** `cd web && npm test` (vitest + cabeçalhos/node), e tudo tem que passar.
  `npx eslint . && npx tsc -b`, também sem erro.
- [ ] **Passo 6:** commit `feat(web): barra do celular com arco e a bola do Menu`.

### Tarefa 4: A folha do Menu

**Files:** Create `web/src/casca/MenuFolha.tsx`. Modify `Navegacao.tsx` (abrir a folha) e
`estilo.css` (bloco novo `.menu-folha`; **não** usar `.folha`, que já existe no mural). Test
`web/src/casca/menu-folha.test.tsx`.

**Interfaces:**
- Consumes: `agrupados`, `lugarAtual` (Tarefa 1), o contador de não lidos que já existe em
  `Navegacao` (`useNaoLidos`).
- Produces:
  `MenuFolha({ lugares, atual, naoLidos, aoFechar }: { lugares: Lugar[]; atual?: Lugar; naoLidos: number; aoFechar: () => void })`.
  É montado só enquanto está aberto, como em `JanelaDeVersao` de `sobre/BotaoVersao.tsx`
  (`showModal()` no efeito, `onClose={aoFechar}`, clique fora fecha, Tab dá a volta). Copie esse
  padrão, não invente outro.

- [ ] **Passo 1: testes que falham** (com o mesmo stub de `showModal`/`close` de
  `sobre/sobre.test.tsx`):
  - Clicar em "Menu" abre um `dialog` com nome "Para onde você quer ir?", com o foco no título, e
    a bola fica com `aria-expanded="true"`.
  - Para o admin, a folha tem os títulos "Dia a dia" e "Gestão" e 5 links, cada um com nome e
    frase. Para o morador, não tem "Gestão".
  - Em `/avisos`, a linha Avisos tem `aria-current="page"`, mostra "Você está aqui" e o contador
    tem `aria-label="2 não lidos"`.
  - Dentro do dialog há um botão "Fechar" (a bola-X). Clicar nele fecha a folha, e o foco volta
    para "Menu".
  - Os eventos `cancel` + `close` do dialog (Esc e voltar do Android) fecham a folha, e
    `history.length` não muda ao abrir (nada de `pushState`).
  - Clicar em "Enquetes" navega para `/enquetes`, a folha some do DOM e
    `history.back()` volta para `/avisos`, não para o menu.
  - A pegadinha tem `aria-hidden="true"`.
- [ ] **Passo 2:** rodar e ver falhar.
- [ ] **Passo 3: implementar** seguindo a seção 4 do spec:
  - A folha encosta no fundo e cobre a barra. A bola-X fica no mesmo ponto da bola, e a lista
    reserva a folga dela.
  - `max-height` em `dvh` (até perto do topo), rolagem por dentro com
    `overscroll-behavior: contain`, e o fundo travado enquanto a folha está aberta (no iOS,
    `overflow: hidden` no `body` não basta: use `position: fixed` no body guardando o
    `scrollY`, ou equivalente, e restaure ao fechar).
  - Arrastar para baixo só pela pegadinha e pelo cabeçalho (pointer events). Passou de ~25% da
    altura da folha, fecha; senão, volta.
  - A animação de subir é curta e fica desligada com `prefers-reduced-motion: reduce`.
  - A letra da folha sem teto (rem normais). As linhas com no mínimo 3rem de altura.
- [ ] **Passo 4:** `npm test`, `npx eslint .`, `npx tsc -b`, tudo verde.
- [ ] **Passo 5:** commit `feat(web): folha do Menu com todos os lugares`.

### Tarefa 5: Conferência visual headless

**Files:** Modify `scripts/dev/conferir-letra.mjs`.

- [ ] **Passo 1:** na função `medir()`, acrescentar a medida da barra: se houver `.nav-barra`
  visível, registrar a altura total (do topo da bola ao fim da barra, sem a safe-area) e acusar
  um problema quando passar de **104 px**. Acusar também quando o `.nav-barra` tiver algum rótulo
  visível com `scrollWidth > clientWidth`.
- [ ] **Passo 2:** acrescentar duas telas em `TELAS`: `menu-aberto` (morador, `/avisos`, com
  `depois` clicando em `getByRole('button', { name: 'Menu' })`) e `menu-aberto-gestao` (admin,
  `/unidades`, idem).
- [ ] **Passo 3:** subir o ambiente
  (`scripts/dev/ambiente-conferencia.sh subir nav-bola 55480 8180 5180`) e rodar
  `node scripts/dev/conferir-letra.mjs --base http://localhost:5180 --tarefa nav-bola --semear --telas mural,painel,documentos,menu-aberto,menu-aberto-gestao,minha-unidade --larguras 320,360,412,1280 --fontes 16,24,32 --temas claro,escuro`.
  O resultado esperado é **0 problemas**. Se houver problema, corrija na tarefa dona (3 ou 4) com
  um teste de regressão e rode de novo.
- [ ] **Passo 4:** olhar você mesmo (Read nos PNG) os prints de `menu-aberto` e `mural` a
  320/360 × 16/32 nos dois temas. Comparar com os desenhos de referência e anotar no relatório o
  que ficou diferente e por quê.
- [ ] **Passo 5:** derrubar o ambiente (`… descer nav-bola`) e fazer o commit do script.

### Tarefa 6: Versão 1.7.0

**Files:** `web/package.json`, `web/src/sobre/novidades.ts`, spec (marcar como implementado).

- [ ] **Passo 1:** `version` em `1.7.0`. Nova primeira entrada em `NOVIDADES`, com
  `versao: '1.7.0'`, `data` de hoje e `nome: 'Menu novo no celular'`. Itens na voz do morador
  (3 no máximo): a barra nova com a bola "Menu", a folha que explica cada lugar, e que a gestão
  acha "Unidades" dentro do Menu.
- [ ] **Passo 2:** `npm test` (o teste de novidades exige que a 1ª entrada seja a versão do
  package.json), eslint e tsc.
- [ ] **Passo 3:** commit `feat: versão 1.7.0, menu novo no celular`.

**Não faça** push, merge na `main` nem deploy. O coordenador cuida disso depois da revisão
independente.
