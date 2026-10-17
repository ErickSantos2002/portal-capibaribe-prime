# Dúvidas e decisões do M5 · Letra que cresce

Decisões tomadas sem perguntar durante a base (`m5/letra-base`). Cada item: a dúvida, o que foi
decidido e por quê. **[Erick]** marca o que só o Erick decide (preferência, aparelho, o que a
Dona Socorro aceitaria); o resto é decisão técnica, revisável na revisão do marco. Os grupos
G1, G2 e G3 acrescentam as suas no fim, cada um na sua seção.

## Base

### 1. Teto nas abas de baixo do celular · [Erick]
- **Dúvida:** com a letra a 200 % num celular de 360 px, a palavra "Documentos" não cabe numa
  aba de 90 px (quatro abas) ou 72 px (cinco, na gestão). As saídas eram: quebrar a palavra no
  meio ("Documen-tos"), rolar as abas para o lado, esconder o texto e deixar só o ícone, ou pôr um
  teto na letra das abas.
- **Decisão:** teto só ali, pela largura da tela: `min(0.9375rem, 5.5vw)` com quatro abas (até
  20 px num celular de 360 px, 23 px num de 412) e `min(0.9375rem, 4.3vw)` com cinco (15,5 px a
  360). O ícone continua crescendo; o resto da tela não tem teto; o menu lateral do computador
  também não.
- **Por quê:** é a única peça em que o texto não pode descer de linha sem virar sílabas soltas,
  e o ícone ao lado já diz qual é a aba. Rolar as abas esconderia "Minha unidade".
- **Recomendação:** manter. Se no aparelho a Dona Socorro não ler as abas, a alternativa é com
  letra grande trocar as abas por um botão "Menu"; é mudança de navegação, para outro marco.

### 2. No iPhone, tudo fica uns 6 % maior que no Android · [Erick]
- **Dúvida:** o Dynamic Type do iPhone chega pelo `font: -apple-system-body`, e o tamanho
  "Grande" (o de fábrica) dele é 17 px, não 16. O texto base de `1.125rem` vira 19 px no iPhone e
  18 px no Android.
- **Decisão:** aceitar os 17 px: é o tamanho de texto que o próprio iPhone usa nos apps dele, e
  compensar (`calc(... * 16 / 17)`) teria de ir em cada tamanho do Portal.
- **Recomendação:** conferir no iPhone de alguém (tarefa 6 do plano) se a tela ficou "grande
  demais" com a letra de fábrica; se ficou, a troca é uma linha no `estilo.css`.

### 3. A meta `text-scale` desliga o zoom de texto automático do celular
- **Decisão:** usar. Sem ela, o Chrome do Android não repassa o tamanho de letra do sistema; com
  ela, desliga o "autosizer" (aumento automático em blocos largos), que num site feito para o
  celular, como o Portal, não fazia nada útil (Chrome 146, spec 2.1).
- **Fica para o aparelho:** Chrome < 146 só ignora a meta (o Portal fica como era).

### 4. Alvos de toque menores que 44 px que já existiam · [Erick]
- **O que a conferência achou** (com a letra de fábrica, antes e depois iguais): a grade de
  apartamentos do painel e de "Quem leu" a 360 px tem casas de 38 × 44 px (8 por linha; o
  RNF-02 pede 44); o celular na ficha da unidade é um link de 21 px de altura.
- **Decisão:** não mexer na base: mudar a grade com a letra de fábrica muda o desenho que já
  está em uso (8 casas = 1 andar). Com letra grande, a grade passa a 4 por linha e as casas ficam
  com 79 px. O link do celular é do G3 (`administracao.css`), que pode dar `min-height: 2.75rem`
  sem mudar o desenho.
- **Recomendação:** casas de 38 px com 4 px de folga atendem o mínimo da WCAG 2.2 (24 px, 2.5.8),
  não o de 44 (2.5.5) que o Portal se impôs. Se quiser os 44 também com a letra de fábrica, a
  saída é a grade em 4 por linha já a 360 px (cada andar em 2 linhas); prefiro manter 8.

### 5. Margem lateral da página fica em px
- **Decisão:** os 16 px de cada lado do `.conteudo` e do `.topo` no celular ficam em px, com o
  comentário da regra. Todo o resto do espaço é rem.
- **Por quê:** a 200 %, `1rem` de cada lado seriam 64 px a menos de leitura numa tela de 360 px,
  e é a largura de leitura que mais falta faz com letra grande. No computador (≥ 56.25em) a margem
  é rem: lá sobra espaço.

### 6. Logo e imagens não crescem
- **Decisão:** a largura do logo fica em px (220, 148, 260, 190), com o comentário. Os ícones
  crescem (são parte do texto, spec 3.4).
- **Por quê:** imagem não é texto; crescer só empurra o formulário da entrada para baixo.

### 7. `playwright-core` como devDependency do `web/`
- **Dúvida:** os scripts de conferência anteriores usavam o Playwright/puppeteer do cache do
  `npx` (caminho da máquina, quebra em outra).
- **Decisão:** `playwright-core ~1.63` em `devDependencies` (sem baixar navegador: usa o
  `google-chrome-stable` do sistema, ou `CHROME=<caminho>`). Não muda a versão do Portal nem o que
  vai para produção.

### 8. O `font-size` da fonte de teste vem do perfil do Chrome, não do CDP
- **Achado:** o `Page.setFontSizes` do protocolo do Chrome muda a fonte padrão, mas o print da
  página inteira o desfaz (os primeiros prints a 32 px saíram com a letra de 16, com as medidas
  certas). O script agora abre um Chrome por tamanho, com as Preferences de um perfil temporário
  (`webkit.webprefs.default_font_size`, a mesma opção que a pessoa muda), e confere em cada
  tela que o `html` ficou com o tamanho pedido (senão acusa erro).

### 9. Nenhum estilo inline em px nos `.tsx`
- **O que achei:** o único `style={{…}}` é a largura em `%` da barra de resultado da enquete; os
  `width`/`height` do `<img>` do logo só reservam a proporção. Os ícones (`width={tamanho}`) eram
  o único tamanho em px no código: `Icone` foi para rem na base; `IconeAnexo` (G1) e `IconeDoc`
  (G2) ficam para os grupos, pelo mesmo `emRem`.

## G1 · avisos

## G2 · documentos, sobre, notificações

## G3 · enquetes, acesso, recuperação, administração

Branch `m5/letra-g3`. Os cinco CSS em rem (primeira passada com `px-para-rem.mjs`, depois linha a
linha): sobrou px só em borda, canto, contorno de foco, sombra e sublinhado (spec 3.3); nenhum
`/* px: motivo */` foi preciso. O ponto 21 de `web/testes/estilo-m4.test.ts` passou a ler o `gap`
do `.enq-lado` em rem (≥ 1rem, os mesmos 16 px), e o ponto 18, a media query em `56.25em`.

### G3.1 "Dia/Hora do término" empurrava a tela
- **Achado:** a 360 px com letra de 32, a caixa de data mede o texto inteiro (357 px numa coluna
  de 328) e a página rolava 13 px para o lado.
- **Decisão:** `.enq-lado` com `grid-template-columns: minmax(0, 1fr)` (e `repeat(2, minmax(0,
  1fr))` lado a lado). A caixa cabe na largura e o "mm/dd/yyyy" continua inteiro. Lado a lado a
  partir de `37.5em` (era 600 px).

### G3.2 Celular na ficha da unidade: alvo de 21 px → 45 px, sem mudar o desenho
- **Decisão:** `padding-block: 0.75rem` no link. Ele é inline, e o padding vertical de um inline
  aumenta a área de toque (e o anel de foco) sem mexer na altura da linha: com a letra de fábrica,
  o print da ficha saiu igual pixel a pixel, e o alvo passou a 45 px (90 px a 200 %).
- **Fica:** a grade de apartamentos de 38 × 44 px (dúvida 4), que é do comum e não mudou.

### G3.3 Mudanças de desenho só com letra grande (com a letra de fábrica, iguais)
Nenhuma era rolagem nem corte (o script não acusava), mas olhando os prints a 32 px não serviam:
- **Resultado da enquete:** a contagem ("1 voto, 100%") não quebra e espremia o texto da opção em
  colunas de 3 letras ("Sáb/ado/de/man/hã"). Agora a linha quebra (`flex-wrap`, texto com `flex:
  1 1 8rem`): com letra grande a contagem desce para baixo do texto.
- **Cédula da nova enquete:** marca e número ao lado deixavam a caixa da opção com 130 px. Com
  letra grande (o mesmo `@container conteudo (max-width: 19.75rem)` da grade de apartamentos),
  a marca e o "Tirar" ficam em cima e a caixa desce com a largura toda.
- **"Mostrar" a senha** (entrar, trocar a senha, primeiro acesso, nova senha): dentro do campo,
  a 200 % sobravam uns 100 px para digitar. Com letra grande ele desce para baixo do campo, à
  direita. O campo é o próprio contêiner (`container-type: inline-size`), porque a tela de entrar
  fica fora do `.conteudo`. Conferido a 32 px em entrar e em Minha unidade → Trocar a senha (o
  primeiro acesso não abre no ambiente de conferência, que entra sem a troca obrigatória; usa o
  mesmo `Campo`).

### G3.4 Selo "Seu apartamento ainda não votou": canto em `1em` · [Erick]
- **Achado:** com `border-radius: 999px`, quando o selo quebra em duas ou mais linhas ele vira
  um ovo (a 200 %, um ovo de 4 linhas, com o pontinho achatado).
- **Decisão:** canto de `1em` e o pontinho com `flex: none`. Numa linha só é a mesma pílula. **É
  a única diferença com a letra de fábrica:** a 360 px o selo já quebrava em 2 linhas na lista de
  enquetes, e os cantos ficaram menos redondos (`enquetes-360-16`, 395 px diferentes no
  `comparar-prints`). Achei que melhora também ali; se preferir o de antes, é voltar o `999px`.

### G3.5 O que é do comum (não mexi; para o coordenador)
- **Ícone que encolhe ao lado de texto que quebra:** `.botao svg` e `.texto-link svg` não têm
  `flex: none`. A 200 %, o ícone de "Ver documentos públicos" (entrar) mede 27 × 40 em vez de
  40 × 40, e o de "Como instalar o Portal" (Minha unidade) quase some. Com a letra de fábrica não
  encolhe (o texto cabe). Sugestão no `estilo.css`: `.botao svg, .texto-link svg { flex: none; }`.
  O mesmo vale para o pontinho do `.selo.novo::before`.
- **`.opcao` (rádio e caixa de marcar):** a 200 %, padding de 2rem, rádio de 3rem e gap de quase
  2rem deixam uns 180 px para o texto, e "apartamentos" quebra em "apartamento/s" (o `anywhere`).
  Não corta nem rola; é feio. Seria do comum decidir (ex.: padding e gap menores com letra grande).
- **Letra menor que não cresce** nas minhas telas: só o "Versão 1.5.1" do rodapé (`sobre.css`,
  G2) e as abas de baixo (teto da dúvida 1).

### G3.6 Rodada antes × depois (`--grupo G3`, 11 telas, 66 prints)
Antes (`/tmp/portal-letra-g3-antes/`, base com os CSS do G3 ainda em px):

| fonte | largura | letra mediana (esperado) | rolagem | algo fora | cortado | alvo < 44 |
|---|---|---|---|---|---|---|
| 16 | 360 | 18 (18) | 0 | 0 | 0 | 2 (painel, ficha) |
| 16 | 1280 | 17 (18) | 0 | 0 | 0 | 1 (ficha) |
| 24 | 360 | 27 (27) | 0 | 0 | 0 | 0 |
| 24 | 1280 | 27 (27) | 0 | 0 | 0 | 1 (ficha) |
| 32 | 360 | 36 (36) | 1 (nova enquete) | 1 | 0 | 0 |
| 32 | 1280 | 36 (36) | 0 | 0 | 0 | 1 (ficha) |

Depois (`/tmp/portal-letra-g3-depois/`):

| fonte | largura | letra mediana (esperado) | rolagem | algo fora | cortado | alvo < 44 |
|---|---|---|---|---|---|---|
| 16 | 360 | 18 (18) | 0 | 0 | 0 | 1 (painel, dúvida 4) |
| 16 | 1280 | 17 (18) | 0 | 0 | 0 | 0 |
| 24 | 360 | 27 (27) | 0 | 0 | 0 | 0 |
| 24 | 1280 | 27 (27) | 0 | 0 | 0 | 0 |
| 32 | 360 | 36 (36) | 0 | 0 | 0 | 0 |
| 32 | 1280 | 36 (36) | 0 | 0 | 0 | 0 |

`comparar-prints` a 16 px: 19 iguais, 3 diferentes: Minha unidade a 360 e 1280 (horário do
"aparelho conectado", dado) e a lista de enquetes a 360 (o canto do selo, G3.4). A letra mediana
já batia antes (a base resolveu o comum; o px dos CSS do G3 era quase todo espaço, não letra);
a letra menor subiu em nova enquete (15 → 30 a 32 px), privacidade (20 → 36) e enquete aberta
(24 → 32).
