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

Branch `m5/letra-g1`. Arquivos: `avisos/avisos.css`, `avisos/anexos.css`, `avisos/IconesAnexo.tsx`
(e o teste novo `avisos/icones-anexo.test.tsx`).

### G1.1 Um limite só para "letra grande" nos avisos: `@container conteudo (max-width: 17.5rem)`
- **Dúvida:** com a letra a 150 % e 200 % num celular de 360 px, peças lado a lado ficavam
  estreitas demais. A conferência não acusava (não é rolagem nem corte), mas o print mostrava:
  no **mural**, a data, o corpo e a seta do cartão deixavam o título com três letras por linha; no
  **aviso aberto**, o quadro "Quando / Onde" em três colunas punha o valor com uma letra por linha;
  no **novo aviso**, "Dia" e "Hora" lado a lado cortavam o "dd/mm/aaaa"; e os botões "Enviar de
  novo" e "Tirar" do anexo passavam da borda.
- **Decisão:** quando o `.conteudo` fica com menos de 17.5rem, o cartão do mural põe a data e a
  seta numa linha e o corpo embaixo, com a largura toda; o quadro do evento põe o rótulo na linha
  do ícone e o valor embaixo; o cabeçalho do aviso e a caixa de destaque empilham (data e ícone em
  cima); Dia e Hora ficam um embaixo do outro; os botões do anexo ganham a linha inteira do cartão.
- **Por quê 17.5rem (280 px com a letra de fábrica):** nada muda com a letra de fábrica, nem num
  celular de 320 px (288 px de conteúdo); num de 360 px, muda a partir de uns 19 px de letra
  (~120 %). A grade de "Quem leu" fica no 19.75rem do comum (é a conta das 8 casas).
- **Recomendação:** conferir no aparelho com a letra um pouco maior que a de fábrica (110 a 125 %),
  que é o caso de transição: se o cartão lado a lado ainda estiver apertado, baixar o limite não
  resolve; subir para 19.75rem (o da grade) resolve, mas muda o cartão no celular de 320 px.

### G1.2 Palavra mais larga que a tela quebra no meio
- **O que fica:** a 200 % e 360 px, palavras como "empreendimento" (no "Onde") e
  "extraordinária" (no título da prévia, que usa o `h2` do comum) não cabem na linha e quebram no
  meio ("empreendiment/o"). Não há rolagem nem corte; é o `overflow-wrap` da spec 3.5.
- **Decisão:** não pôr teto (`min(rem, vw)`), porque é texto corrido, não letra de vitrine (spec
  3.5). Com 150 % isso já não acontece nas telas conferidas.

### G1.3 Ícones que encolhiam: o comum devia ter `flex: none` · [coordenador]
- **Achado:** o `Icone` cresce, mas dentro de um flex sem `flex: none` ele **encolhe** quando o
  texto ao lado quebra linha: o alfinete do fixado ficava com 18 de 40 px a 200 %; a lupa do
  "Procurar nos avisos", a caixa do "Ver os avisos arquivados" e o clipe do "Anexar foto ou PDF"
  também. As peças são do comum: `.fixado .rotulo`, `.com-icone`, `.texto-link`, `.botao`.
- **Decisão:** contornado nos avisos com seletor próprio (`.fixado .rotulo svg`,
  `.avisos-busca label svg`, `.avisos-arquivados .texto-link svg`, `.anexos-escolher label svg`
  com `flex: none`), sem tocar o `estilo.css`.
- **Recomendação:** no fechamento, pôr no comum `:is(.botao, .texto-link, .com-icone, .rotulo) >
  svg { flex: none; }` (ou no próprio `Icone`) e apagar os quatro seletores dos avisos. Os outros
  épicos provavelmente têm o mesmo caso; a varredura que achou estes (SVG com largura real menor
  que a pedida) está descrita na G1.6.

### G1.4 Campos escondidos com o recorte do `.oculto`
- **Decisão:** os rádios das categorias e o campo de arquivo continuam escondidos no CSS dos
  avisos (sem mexer nos `.tsx`), agora como o `.oculto` do comum: 1 px com `/* px: escondido */`,
  `overflow: hidden` e `clip-path: inset(50%)`. Sem o recorte, o botão interno do campo de arquivo
  (que cresce com a letra) e o rádio passavam da borda: eram eles que faziam a página rolar para o
  lado no novo aviso a 24 e 32 px. Foco pelo teclado continua (o anel vai no rótulo vizinho).

### G1.5 O que ficou em px (spec 3.3)
- **Miniatura do anexo** (56 × 56 px, e a coluna dela no cartão): imagem. **Largura máxima da
  foto única** no computador (520 px): imagem. **Campos escondidos** (1 px). O resto é rem; as
  media queries (720 e 600 px) viraram 45em e 37.5em.

### G1.6 Rodada antes/depois
`conferir-letra.mjs --grupo G1` (mural, aviso, aviso-fixado, novo-aviso, quem-leu):

| fonte | largura | antes: rolagem / fora / cortado / alvo < 44 | depois |
|---|---|---|---|
| 16 | 360 | 0 / 0 / 0 / 1 tela (quem-leu) | 0 / 0 / 0 / 1 tela (quem-leu) |
| 16 | 1280 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| 24 | 360 | **1 (novo aviso)** / 0 / 0 / 1 (quem-leu) | 0 / 0 / 0 / 0 |
| 24 | 1280 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| 32 | 360 | **1 (novo aviso)** / 0 / 0 / 1 (quem-leu) | 0 / 0 / 0 / 0 |
| 32 | 1280 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

- **Letra mediana por tela** (16 → 24 → 32 px de fonte, a 360): antes, mural 15 → 19.8 → 22 e
  "Quem leu" 15 → 15 → 15; depois, mural 15 → 22.5 → 30, "Quem leu" 15 → 22.5 → 30, novo aviso
  e aviso fixado 18 → 27 → 36, aviso 16 → 24 → 32 (tudo cresce na proporção).
- **16 px: os 10 prints iguais aos de antes, pixel a pixel** (`comparar-prints.mjs`: 10 iguais).
- **Alvos < 44 que já existiam** (dúvida 4 da base): as casas da grade de "Quem leu" a 360 px com a
  letra de fábrica (38 × 44, 318 casas). Com letra grande, a grade passa a 4 por linha e as casas
  ficam largas; antes, a 24 e 32 px, continuavam em 8 por linha (o `repeat(8, …)` dos avisos
  vencia a *container query* do comum, e a letra não crescia). Nenhum alvo novo.
- **Telas a mais, fora do script** (cópia local do `conferir-letra.mjs`, não versionada): o novo
  aviso com título, texto formatado, "É um evento?" marcado e dois anexos; e a prévia aberta, com
  evento. Antes: rolagem a 24 e 32 px nas duas. Depois: zero rolagem, fora e cortado nas 12
  medidas, e os 4 prints a 16 px iguais aos de antes. A mesma cópia mediu os SVG encolhidos (G1.3):
  zero depois.
- **Não conferido aqui:** o aviso aberto **com fotos e PDF** e a foto grande (visualizador): o
  envio de arquivo não está ligado no ambiente local (sem R2), então nenhum anexo chega a existir.
  A conversão ali é a mecânica (rem), e o `IconeAnexo` está em rem; fica para a rodada do
  coordenador num ambiente com R2, ou para o aparelho.

## G2 · documentos, sobre, notificações

## G3 · enquetes, acesso, recuperação, administração
