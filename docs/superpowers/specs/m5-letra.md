# Spec · M5 · Letra que cresce (base e regra)

| | |
|---|---|
| **Origem** | Backlog U18 (`docs/07-roadmap.md`, "Backlog sem data"): as fontes em `px` não acompanham o tamanho de letra escolhido no celular |
| **Persona** | Dona Socorro, 62 (`docs/06-prototipo.md`): texto base 18 px, alvos ≥ 44 px (RNF-02) |
| **Plano** | `docs/superpowers/plans/m5-letra.md` (base + grupos G1, G2, G3) |
| **Dúvidas** | `docs/superpowers/duvidas-m5-letra.md` |
| **Guarda** | `web/testes/letra.test.ts` |
| **Conferência** | `scripts/dev/ambiente-conferencia.sh` + `scripts/dev/conferir-letra.mjs` |

## 1. O problema

O `body` tinha `font-size: 18px` e todos os outros tamanhos em px (~700 ocorrências em 12 CSS).
Um tamanho em px é absoluto: não importa o que a pessoa escolha no aparelho ou no navegador, o
texto fica igual. Medido no Chrome com a "Tamanho da fonte" do navegador em 16, 24 e 32 px
(100 %, 150 %, 200 %), antes desta tarefa a letra mediana das telas ficava em **18 px nos três**
(seção 6).

## 2. Como o tamanho de letra do aparelho chega numa página (pesquisa)

**FATO** = documentado em fonte oficial ou especificação. **A TESTAR** = só um aparelho real
confirma; está no plano (tarefa 6) e nas dúvidas.

### 2.1 Chrome no Android

- **FATO.** Sem nada na página, o Chrome do Android **não** repassa o tamanho de letra do sistema
  ao texto da página: a página nasce com 16 px no `html` e o celular só pode ampliar com zoom ou
  com o "autosizer" (aumento automático de texto em blocos largos), que é heurístico e não segue
  a escolha da pessoa. O modo "legacy" (sem a meta) é o padrão da especificação.
  [CSS Fonts 5, §2 "Text-Scale meta element"](https://www.w3.org/TR/css-fonts-5/#text-scale-meta) ·
  [explicador da CSSWG](https://drafts.csswg.org/css-env-1/explainers/meta-text-scale.html)
- **FATO.** Com `<meta name="text-scale" content="scale">`, o tamanho inicial (`medium`, o que
  vale para o `html` sem `font-size` próprio) passa a ser **16 px × o fator de escala de texto**
  do sistema e do navegador, e o navegador desliga as "intervenções" de tamanho (o autosizer).
  Só texto em unidade relativa cresce: "um `font-size: 20px` NÃO respeita a preferência"; `rem`
  respeita, **desde que o `:root` fique no tamanho padrão**.
  [CSS Fonts 5, §2.3 "The scale keyword"](https://www.w3.org/TR/css-fonts-5/#scale-keyword)
- **FATO.** Saiu no **Chrome 146** (estável em 10/03/2026), "CSS and UI": o tamanho padrão da
  raiz escala com a configuração de texto do sistema e do navegador; a meta também desliga o
  zoom da página inteira que o Windows fazia e o aumento automático de texto no celular.
  [Chrome 146 release notes](https://developer.chrome.com/release-notes/146)
- **FATO.** Media query em `em`/`rem` é medida pelo tamanho **inicial** da fonte (não pelo do
  `html` do autor), então ela também acompanha a escala quando a meta está lá.
  [Media Queries 4, §1.3 "Units"](https://www.w3.org/TR/mediaqueries-4/#units) ·
  [Josh Tumath, "Let's fix the web's text size" (jul/2026)](https://www.joshtumath.uk/posts/2026-07-02-lets-fix-the-webs-text-size/)
- **FATO (contexto).** O Firefox do Android já segue o tamanho do sistema fazendo **zoom da
  página inteira** (até o px cresce), um mecanismo diferente.
  [Adrian Roselli, "Honoring Mobile OS Text Size" (fev/2026)](https://adrianroselli.com/2026/02/honoring-mobile-os-text-size.html) ·
  [Manuel Matuzović (2026)](https://matuzo.at/blog/2026/text-scaling-meta-tag)
- **A TESTAR.** Se o "Tamanho da fonte" do Android (Configurações → Tela) e a "Escala do texto"
  das configurações de acessibilidade do próprio Chrome se somam como a nota diz; o Samsung
  Internet (Chromium, versão própria) com a meta; e Android com Chrome < 146.
- **`text-size-adjust`:** não usamos. Com a meta, o Chrome já desliga o autosizer; `none`
  atrapalha quem amplia; e no iPhone quem manda é o Dynamic Type (abaixo).
  [MDN, text-size-adjust](https://developer.mozilla.org/en-US/docs/Web/CSS/text-size-adjust)

### 2.2 Safari no iPhone e no iPad

- **FATO.** O Safari **não** repassa o Dynamic Type (Ajustes → Tela e Brilho → Tamanho do Texto)
  a sites por padrão. Ele chega só pelas fontes de sistema do WebKit: `font: -apple-system-body`
  é um estilo inteiro (tamanho e peso), que segue a escolha do aparelho.
  [WebKit, "Using the System Font in Web Content" (2015)](https://webkit.org/blog/3709/using-the-system-font-in-web-content/)
- **FATO (comunidade, não Apple).** O padrão é aplicar `font: -apple-system-body` no topo e
  limitar a aparelhos de toque com `@supports (... -webkit-touch-callout ...)`, porque no Safari do
  Mac essa fonte tem tamanho fixo; e o `font` também troca a família, que o autor devolve.
  [Adrian Roselli](https://adrianroselli.com/2026/02/honoring-mobile-os-text-size.html) ·
  [Craig Hockenberry, "Dynamic Type on the Web"](https://furbo.org/2024/07/04/dynamic-type-on-the-web/)
- **A TESTAR.** O tamanho exato no iPhone (o "Grande" padrão é 17 px, então tudo fica ~6 % maior
  que no Android: dúvida 2), os "Tamanhos maiores de acessibilidade" (até ~3×) e se o `@supports`
  com `-webkit-touch-callout: default` é verdadeiro no iPadOS em modo "site para computador".

### 2.3 Portal instalado (PWA)

- **FATO.** No Android, o PWA instalado roda no motor do Chrome (WebAPK); a meta vale do mesmo
  jeito. No iPhone, o app da tela inicial é o WebKit do Safari; o `-apple-system-body` vale do
  mesmo jeito. Nenhuma das fontes acima trata o PWA à parte.
- **A TESTAR.** Os dois, no aparelho, com o Portal instalado (é como a Dona Socorro usa).

### 2.4 Navegadores de computador

- **FATO.** Chrome (Configurações → Aparência → Tamanho da fonte) e Firefox (Configurações →
  Geral → Tamanho padrão) mudam o `medium`; com `rem` tudo acompanha, e as media queries em `em`
  também (o layout de 2 colunas vira 1 quando a letra cresce). O zoom (Ctrl +) continua
  funcionando como sempre. O sistema operacional: no Windows, os navegadores fazem zoom da
  página inteira; no macOS, ninguém reage.
  [explicador da CSSWG](https://drafts.csswg.org/css-env-1/explainers/meta-text-scale.html)
- **CONFERIDO aqui** (seção 6), com o Chrome do sistema a 16, 24 e 32 px de fonte padrão.

## 3. A regra (vale para todo CSS de `web/src`)

### 3.1 Letra
- `font-size` **sempre em `rem`** (1rem = o tamanho que o navegador dá ao `html`; 16 px de
  fábrica). O texto base de 18 px vira **`1.125rem`** no `body`. Tabela na seção 4.
- **O `html` nunca recebe `font-size`.** Um `html { font-size: 62.5% }` ou em px desligaria a
  escolha da pessoa (CSS Fonts 5, §2.3). A única coisa no `html` é o `-apple-system-body` (3.6).
- `line-height` **sem unidade** (1.5, 1.2…), nunca px.
- `em` só quando o tamanho é de propósito relativo ao pai (ex.: `letter-spacing: 0.04em`).

### 3.2 Espaço e tamanho que acompanham o texto: `rem`
Tudo que tem texto dentro, ou que existe por causa do texto, cresce junto, senão a letra grande
corta ou encavala:
- `padding`, `margin`, `gap` (dentro e entre componentes);
- `min-height`/`height` de botão, campo, aba e alvo de toque (o 44 px vira `2.75rem`; o 56 px do
  botão, `3.5rem`);
- `width`/`min-width`/`max-width` de colunas e caixas (o menu lateral de 264 px vira `16.5rem`;
  a coluna de leitura de 720 px, `45rem`);
- `scroll-padding`, `top`/`bottom`/`left`/`right` de peças fixas que ficam sobre o texto;
- os pontinhos, marcadores e setas desenhados em CSS ao lado do texto.

### 3.3 Exceções permitidas em px
**Sem justificar** (a guarda aceita a propriedade):

| Propriedade | Por quê |
|---|---|
| `border`, `border-*-width` | espessura de linha não precisa crescer |
| `border-radius` e os tokens `--r-pequeno`, `--r-medio` | canto |
| `outline`, `outline-offset` (foco) | o anel de foco já é bem visível em 3 px |
| `box-shadow`, `text-shadow`, token `--sombra` | sombra |
| `text-underline-offset`, `text-decoration-thickness` | sublinhado |

**Com o comentário `/* px: motivo */`** na mesma declaração (antes ou logo depois do `;`, na mesma
linha). Motivos aceitos:
- **margem lateral da página no celular** (`.conteudo` e `.topo`, 16 px): com a letra a 200 %,
  `2rem` de cada lado comeriam 64 px da largura de leitura de um celular de 360 px;
- **imagem** (logo, miniatura de foto): imagem não é texto, e crescer só empurraria o conteúdo;
- **escondido** (1 px do `.oculto` e dos rádios dos blocos);
- **marcador fino** que é desenho de linha (a barrinha de 3 px da aba atual).

`font-size`, `font` e `line-height` em px **nunca** passam, nem com o comentário.

### 3.4 Ícones e estilos nos `.tsx`
- Ícones SVG (`Icone`, e os ícones próprios de `avisos/IconesAnexo.tsx` e dos documentos):
  **crescem com a letra**. O `tamanho` continua em px de desenho (24 = com a letra de fábrica) e
  o SVG recebe `width`/`height` em rem pelo `emRem` de `web/src/casca/emRem.ts` (24 → `1.5rem`).
  Com a letra de fábrica, o tamanho é o mesmo de antes.
- Estilo inline com tamanho em px: o único `style={{…}}` do `web/src` é a largura em `%` da barra
  de resultado da enquete (`EnqueteAberta.tsx`), que não muda. Os `width`/`height` do `<img>` do
  logo (`Logo.tsx`) só reservam a proporção (o CSS manda no tamanho) e ficam.

### 3.5 Teto: o que acontece com letra enorme
- **Nada de rolagem lateral, nunca.** A página não pode ficar mais larga que a tela; não se
  esconde o problema com `overflow-x: hidden`.
- Palavra que não cabe na linha **quebra**: `overflow-wrap: break-word` no `body` (herdado). Onde
  a palavra é item de flex ou grid (que medem a palavra inteira antes de quebrar), `min-width: 0`
  ou `overflow-wrap: anywhere` **no próprio componente** (ex.: `.opcao`). O `anywhere` não vai no
  `body`: ele muda a medida mínima de todo item de grid e, com a letra de fábrica, "Financeiro"
  virou "Financeir/o" nas categorias do aviso.
- Linhas que se dividem em colunas (rótulo e valor, placa e título, 3 números lado a lado)
  **descem para baixo** quando não cabem (`flex-wrap`, `auto-fit`, `flex-basis` em rem), mantendo
  a letra de fábrica igual a antes.
- Grade de apartamentos (8 por andar): com letra grande, cada andar vira 2 linhas de 4, por
  *container query* sobre o `.conteudo` (`@container conteudo (max-width: 19.75rem)`).
- **Teto de verdade só nas abas de baixo do celular**: quatro ou cinco abas dividem 360 px, e a
  palavra "Documentos" não cabe numa aba de 72 a 90 px com letra maior que ~20 px. Ali,
  `font-size: min(0.9375rem, 5.5vw)` (quatro abas) e `min(0.9375rem, 4.3vw)` (cinco). O ícone
  continua crescendo; o menu lateral do computador não tem teto. Fora isso, **`min(<rem>, <vw>)`
  só para letra de vitrine** (placa grande, título da entrada), se a conferência mostrar que não
  cabe, nunca em texto corrido.

### 3.6 O que vai no `index.html` e no `html`
- `<meta name="text-scale" content="scale" />` no `web/index.html` (2.1).
- No `estilo.css`:
  ```css
  @supports (font: -apple-system-body) and (-webkit-touch-callout: default) {
    html { font: -apple-system-body; }
  }
  ```
  Só iPhone e iPad (o Safari do Mac não tem `-webkit-touch-callout`). O `html` pega o
  **tamanho** do Dynamic Type; o `body` já declara `font-family: var(--fonte)` (Atkinson
  Hyperlegible), `font-size: 1.125rem` e `line-height: 1.5`, então a família e o ritmo da casa
  voltam no body e o resto da página herda deles.

### 3.7 Layout de 2 colunas
`@media (min-width: 900px)` vira **`@media (min-width: 56.25em)`** (media query sempre em `em`, a
unidade que todo navegador mede pelo tamanho inicial). Com letra de fábrica, nada muda; com letra
a 150 % (24 px), o menu lateral só aparece a partir de 1350 px de janela, e a 200 %, de 1800 px:
num notebook de 1280 px, letra grande dá o layout de celular, com uma coluna só, que é o desejado
(a letra grande cabe, e as abas de baixo ficam). O mesmo vale para qualquer outra media query.

## 4. Tabela de conversão (1rem = 16 px)

| px | rem | | px | rem | | px | rem |
|---|---|---|---|---|---|---|---|
| 2 | 0.125 | | 15 | 0.9375 | | 28 | 1.75 |
| 3 | 0.1875 | | 16 | 1 | | 30 | 1.875 |
| 4 | 0.25 | | 17 | 1.0625 | | 32 | 2 |
| 6 | 0.375 | | 18 | 1.125 | | 44 | 2.75 |
| 8 | 0.5 | | 19 | 1.1875 | | 48 | 3 |
| 10 | 0.625 | | 20 | 1.25 | | 52 | 3.25 |
| 11 | 0.6875 | | 21 | 1.3125 | | 54 | 3.375 |
| 12 | 0.75 | | 22 | 1.375 | | 56 | 3.5 |
| 13 | 0.8125 | | 24 | 1.5 | | 64 | 4 |
| 14 | 0.875 | | 26 | 1.625 | | 900 (media) | 56.25em |

`scripts/dev/px-para-rem.mjs <arquivo.css>` faz a primeira passada mecânica (px → rem nas
declarações, px → em nas media queries, exceções da 3.3 intactas). Depois dela, à mão: os casos de
`/* px: motivo */`, o teto (3.5) e a conferência visual.

## 5. Guarda automática (`web/testes/letra.test.ts`)

Roda no `npm test` (parte `node --test`). Lê **todo** `.css` de `web/src` e falha se houver:
`font-size`/`font`/`line-height` em px; media query (`@media`, `@container`, `@supports`) em px;
qualquer outro px fora das propriedades da 3.3 e sem `/* px: motivo */`. A primeira parte do teste
prova a própria regra com CSS de exemplo (pega o errado, deixa o certo).

`PENDENTES` lista os CSS dos épicos ainda não convertidos (grupos G1, G2, G3 do plano). Enquanto
um arquivo está lá, o teste só confere que ele ainda tem px (se já não tiver, falha pedindo para
tirá-lo da lista). Quem converte um arquivo **apaga a linha dele**, e o teste passa a cobri-lo.
No fim do M5, `PENDENTES` fica vazio. `estilo.css` e `marca/marca.css` já estão cobertos.

## 6. Conferência (antes e depois da base)

`scripts/dev/conferir-letra.mjs`: Chrome headless próprio (playwright-core), 21 telas (anônimo,
morador 1101 e admin 1002, dados fictícios), 360 e 1280 px, fonte padrão do navegador em 16, 24 e
32 px pelo perfil do Chrome (`webkit.webprefs.default_font_size`, a mesma opção das
configurações). Mede rolagem lateral, elemento que passa da borda, quem empurra a página, texto
cortado, alvo < 44 px e a letra mediana. 126 prints por rodada, fora do repositório.

**Antes** (commit `e8749ee`, `/tmp/portal-letra-base-antes/`):

| fonte | largura | letra mediana (esperado) | rolagem | algo fora | cortado | alvo < 44 |
|---|---|---|---|---|---|---|
| 16 | 360 | 18 (18) | 0 | 0 | 0 | 3 telas |
| 16 | 1280 | 17 (18) | 0 | 0 | 0 | 1 |
| 24 | 360 | **18** (27) | 0 | 0 | 0 | 3 |
| 24 | 1280 | **17** (27) | 0 | 0 | 0 | 1 |
| 32 | 360 | **18** (36) | 0 | 0 | 0 | 3 |
| 32 | 1280 | **17** (36) | 0 | 0 | 0 | 1 |

Nada quebrava porque **nada crescia**.

**Depois da base** (só `estilo.css`, `marca.css`, `Icone`, a meta e o Dynamic Type; os 10 CSS dos
épicos ainda em px; `/tmp/portal-letra-base-depois/`):

| fonte | largura | letra mediana (esperado) | rolagem | algo fora | cortado | alvo < 44 |
|---|---|---|---|---|---|---|
| 16 | 360 | 18 (18) | 0 | 0 | 0 | 3 telas |
| 16 | 1280 | 17 (18) | 0 | 0 | 0 | 1 |
| 24 | 360 | **27** (27) | 1 (novo aviso) | 0 | 0 | 1 |
| 24 | 1280 | **27** (27) | 0 | 0 | 0 | 1 |
| 32 | 360 | **36** (36) | 2 (novo aviso, nova enquete) | 1 | 0 | 1 |
| 32 | 1280 | **36** (36) | 0 | 0 | 0 | 1 |

- **Com a letra de fábrica (16 px), os 42 prints são iguais aos de antes pixel a pixel** (tirando
  o horário do "aparelho conectado" em Minha unidade).
- O que sobrou é dos épicos: categorias do novo aviso e o campo de anexo (G1, `avisos.css`,
  `anexos.css`); "Dia/Hora do término" lado a lado na nova enquete (G3, `gestao.css`). A letra
  mediana por tela mostra o que ainda é px: a 32 px e 360, o mural está em 22, "Quem leu" em 15,
  documentos em 26, "O que mudou" em 18, a lista de enquetes em 30, o painel em 26.
- Alvos < 44 que **já existiam** com a letra de fábrica: a grade de apartamentos a 360 px (38 ×
  44 px, painel e "Quem leu") e o celular como link na ficha da unidade (145 × 21). Dúvida 4.
