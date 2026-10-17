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
