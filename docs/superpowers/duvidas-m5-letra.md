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

Convertidos: `documentos/documentos.css`, `sobre/sobre.css`, `notificacoes/notificacoes.css` e o
`IconeDoc` (`documentos/pecas.tsx`, pelo `emRem`, com o teste `documentos/iconeDoc.test.tsx`).

### G2-1. A conferência não mostra as telas de documento com itens nem a faixa do mural
- **Achado:** o ambiente de conferência sobe com os arquivos e o push desligados, então as telas
  `documentos` e `documentos-publicos` só mostram "Nenhum documento", e a faixa "Falta um passo:
  ative as notificações" do mural e o passo a passo do iPhone nunca aparecem. Era aí que estavam
  os problemas com letra grande.
- **Decisão:** conferi também com as respostas da API simuladas (Chrome próprio, o mesmo perfil
  de fonte do `conferir-letra.mjs`; script fora do repositório): lista com três documentos de
  título comprido, documento aberto (morador e gestão, com versão anterior), aviso com "Ver o
  documento", faixa do mural, "Receber os avisos" com push disponível no computador e no iPhone,
  e Minha unidade. Antes da conversão (CSS da base): rolagem lateral a 32 px e 360 em **4 telas**
  (os botões Abrir/Baixar do documento aberto, nas duas visões; o "Ver o documento" do aviso; o
  "Agora não" da faixa). Depois: **0** em todas, a 16, 24 e 32 px, em 360 e 1280; 16 px igual ao
  de antes, fora a G2-4.
- **Recomendação:** na rodada completa do coordenador, se der, semear um documento (precisaria
  do armazenamento de arquivos local) e ligar o push de mentira no ambiente; hoje o script não
  enxerga essas peças.

### G2-2. Com a letra muito grande, o ícone fica em cima e o texto embaixo
- **Onde:** os botões "Abrir o documento" e "Baixar" da folha, o cartão "Ver o documento" do
  aviso automático, a frase da faixa do mural (ao lado do sino) e a explicação com o ícone "i" em
  "Receber os avisos" e Minha unidade.
- **Decisão:** `flex-wrap: wrap` e o texto com `flex: 1 1 10rem` (no botão, só o wrap): com a
  letra de fábrica cabe ao lado, como antes; a 200 % num celular, a palavra mais comprida
  ("documento", "notificações") não cabia ao lado do ícone e passava da borda. A alternativa,
  quebrar a palavra no meio ("notificaçõ-es"), lê pior.
- **[Erick]:** no cartão "Ver o documento", com letra a 200 % ficam o ícone numa linha, o texto
  na outra e a seta na última. É legível, mas se a Dona Socorro estranhar, dá para esconder o
  ícone grande da esquerda só com letra grande.

### G2-3. Janela "O que mudou" com letra grande numa tela baixa: a janela inteira rola
- **Achado:** a 200 % num celular, o topo fixo da janela (logo, "Versão 1.5.1", "do Portal
  Capibaribe Prime") ocupava ~430 px dos 756 px da janela, e as novidades rolavam numa fresta de
  ~150 px entre o topo e o "Fechar".
- **Decisão:** `@media (max-height: 35em)` (560 px de altura com a letra de fábrica, 1120 px a
  200 %): a janela inteira rola, com o topo junto, e só o "Fechar" fica preso embaixo. Com a
  letra de fábrica num celular em pé, nada muda (o print é igual); com o celular **deitado** e a
  letra de fábrica (altura < 560 px), passa a rolar inteira também, o que ali também ajuda.
- **Margens da janela em px:** os 12 px até a borda da tela (`calc(100% - 24px)`) ficam em px,
  com o motivo "margem lateral da página no celular" (o mesmo da base, decisão 5). A caixa de
  dentro desconta os 2 px da borda da janela em px (`… - 2px`), senão sobrava ou faltava 1 px
  com letra grande.
- **Linha do tempo:** o ponto de cada versão ficava 1 px fora do centro da linha (2 px, que não
  cresce) com letra grande, e saía 2 px para fora da área que rola. `left: calc(-0.5rem - 1px)`
  e `margin-left: calc(0.5rem - 1px)` mantêm o ponto centrado na linha em qualquer tamanho. A
  linha que liga os números do passo a passo do iPhone fica em 2 px pelo mesmo motivo
  ("marcador fino").

### G2-4. Com a letra de fábrica, o ícone do título em "Receber os avisos" deixou de encolher
- **Achado:** em "Coloque o Portal no computador/na tela inicial" e "Ative as notificações", o
  ícone era item de flex (`.com-icone`, do comum) e encolhia quando o título ocupa a linha toda:
  a 360 px e letra de fábrica ele já saía menor que 24 px; a 200 %, um ícone de ~10 px ao lado de
  letra de 36.
- **Decisão:** `flex: none` no ícone, só dentro de `.notif-cartao`. **É a única diferença dos
  prints a 16 px** do G2 (o ícone volta a 24 px e o título anda 2 px para a direita, a 360 px).
- **Para o comum:** o mesmo `flex: none` em `.com-icone svg` resolveria em todo lugar; não mexi
  (`estilo.css` não é do grupo).

### G2-5. O que ficou para o comum (não mexi)
- **Topo fixo enorme com letra grande:** a 200 % e 360 px, o `.topo` (título, placa "Bloco 1
  101", lua) ocupa 250 a 470 px dos 780 da tela; no aviso com título longo, mais da metade. O
  `.topo h1` só tem `line-clamp` no documento aberto (U17).
- **Abas de baixo a 200 %:** "Enquetes" e "Documentos" encostam um no outro (o teto da decisão 1
  deixa cada palavra em ~20 px numa aba de 90).
- **Lista (`.item`) a 200 %:** com a seta do lado, títulos como "condomínio" e "Representantes"
  quebram no meio da palavra ("condomíni-o"); é o `minmax(0, 1fr)` do comum, sem rolagem, mas lê
  pior. Menos `padding` no `.item` com letra grande, ou a seta menor, daria a folga.

### G2-6. Alvos menores que 44 px
- Nenhum nas telas do G2, antes ou depois, nas medidas do script e nas simuladas.

### Rodada antes/depois (`conferir-letra.mjs --grupo G2`)

Antes (`/tmp/portal-letra-g2-antes`) e depois (`/tmp/portal-letra-g2-depois`) deram a mesma
tabela; o que mudou foi por tela (a letra da janela "O que mudou" estava parada em 18 e passou a
25,5 e 34, que é 17 × 1,5 e × 2, o tamanho de fábrica dela; "novo documento", a menor letra, de
15 para 30 a 32 px):

| fonte | largura | letra mediana (esperado) | rolagem | algo fora | cortado | alvo < 44 |
|---|---|---|---|---|---|---|
| 16 | 360 | 18 (18) | 0 | 0 | 0 | 0 |
| 16 | 1280 | 17 (18) | 0 | 0 | 0 | 0 |
| 24 | 360 | 27 (27) | 0 | 0 | 0 | 0 |
| 24 | 1280 | 27 (27) | 0 | 0 | 0 | 0 |
| 32 | 360 | 36 (36) | 0 | 0 | 0 | 0 |
| 32 | 1280 | 36 (36) | 0 | 0 | 0 | 0 |

`comparar-prints.mjs` a 16 px: diferença só em dado (o número de avisos não lidos na aba, o
horário e a quantidade de "aparelhos conectados" em Minha unidade) e no ícone da G2-4.

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
