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

## Costura

Em `m5/integrado` (base + G1 + G2 + G3). O que os grupos deixaram para o comum, e a conferência
passando a ver todas as telas. Guarda nova: `web/testes/costura-m5.test.ts` (16 testes; 14
falhavam com o CSS de antes da costura; os 2 que passavam conferem o que não podia mudar).

### C1. Ícone que encolhe: uma regra só, para todo SVG
- **Decisão:** `svg { flex-shrink: 0 }` no `estilo.css` (seletor de elemento, o mais fraco: quem
  quiser um ícone que encolha diz no próprio componente) e `.selo::before { flex: none }` (o
  pontinho do "Novo" e do "Seu apartamento ainda não votou").
- **Por quê no SVG e não em `:is(.botao, .texto-link, .com-icone, .rotulo) > svg`:** a lista de
  peças flex que levam ícone não é só essa (`.doc-escolher`, `.enq-mais`, `h3.com-icone` dos
  aparelhos, os botões do visualizador…), e cada peça nova esqueceria. O `Icone`, o `IconeAnexo`
  e o `IconeDoc` são todos `<svg>`; nenhum SVG do Portal deve encolher.
- **Apagados os contornos:** G1 (`.fixado .rotulo svg`, `.avisos-busca label svg`,
  `.avisos-arquivados .texto-link svg`, `.anexos-escolher label svg`), G2 (`.notif-cartao
  .com-icone svg`), G3 (o `flex: none` do `.selo.enq-falta::before`). Os `flex: none` em SVG que
  já existiam antes do M5 (`.doc-quem svg`, `.enq-cartao svg`…) ficaram: não atrapalham.
- **Efeito colateral, resolvido junto:** sem encolher, o ícone empurrava o rótulo e
  "notificações" passava da borda do "Ativar notificações" a 200 %. Com letra grande, o `.botao`
  ganha `flex-wrap: wrap` (ícone em cima, texto embaixo, como o "Abrir o documento" da G2-2).
- **Com a letra de fábrica:** muda um ícone, o do "Como instalar o Portal na tela inicial" em
  Minha unidade a 360 px, que já encolhia (22,7 × 24 → 24 × 24).

### C2. Conferência: medidas novas, permanentes no `conferir-letra.mjs`
- **Ícone encolhido:** SVG com largura e altura fora da proporção do `viewBox`, e pontinho
  redondo em CSS (`::before` com `border-radius: 50%`) que deixou de ser redondo.
- **Palavra quebrada:** palavra de 2 a 12 letras cujas letras caem em duas linhas (com
  `Range.getClientRects`). Não contam: quebra no hífen, endereço e e-mail (são uma "palavra" só,
  comprida) e palavra de 13 letras ou mais ("Representantes", "acompanhamento"), que a 200 % num
  celular de 360 px não cabe numa linha mesmo (spec 3.5).
- **Texto que passa da borda** do controle (botão, link, rótulo, campo): conta como "cortado". Foi
  o que achou o "Documentos" encostado nas abas e o "notificações" fora do botão.
- **Não contam como cortado:** a foto recortada na moldura (`object-fit`, só a imagem passa da
  caixa) e o resumo de propósito (`line-clamp`, como o título do documento no topo, U17, que
  aparece inteiro logo abaixo); este fica listado à parte no resumo, "não conta".
- **Janela aberta** ("O que mudou", foto grande): mede só a janela e o print é da tela, não da
  página inteira (a janela é fixa; a página atrás está coberta). Antes, o "O que mudou" media a
  Minha unidade de trás.

### C3. Ambiente de conferência com arquivos e push, sem R2 (G2-1, G1 "não conferido")
- **Arquivos:** `scripts/dev/api-conferencia.py` sobe a mesma `app.main:app` trocando só a
  dependência `obter_armazenamento` pelo `ArmazenamentoFalso` dos testes (em memória), como o
  `conftest.py` faz. Os links assinados apontam para um R2 fictício
  (`conferencia.r2.cloudflarestorage.com`, que a CSP de produção libera); o
  `conferir-letra.mjs` intercepta esse endereço (rota do Playwright) e busca o conteúdo na rota
  `/api/_conferencia/bucket/…` que o próprio script de dev acrescenta. A foto do aviso chega por
  `…/abrir`, que redireciona; como o Playwright não intercepta o pedido redirecionado (sem a
  rota, o Chrome tentava o domínio de verdade da Cloudflare), a rota segue o redirecionamento ela
  mesma. Nada sai para a rede, nada vai para produção (só roda com `PORTAL_AMBIENTE=local`).
- **Por que não o `moto`:** só está instalado o `moto[s3]` (dentro do processo), sem o servidor;
  e o navegador precisa de um endereço que a CSP aceite. Interceptar no Playwright, como o G2 fez
  à parte, agora está versionado no próprio script.
- **Push:** o `ambiente-conferencia.sh` gera um par VAPID na hora (nunca gravado) e liga o push;
  ninguém se inscreve, nenhuma notificação sai. Com isso aparecem a faixa "Falta um passo" no
  mural e o "Receber os avisos" como para o morador.
- **`--semear` agora cria também:** um aviso com duas fotos (PNG gerado pelo script, sem arquivo
  no repositório) e um PDF; um documento das unidades com duas versões e o aviso automático da
  versão nova ("Ver o documento"); um documento público.
- **Telas novas (28 no total, eram 21):** `primeiro-acesso` (a primeira unidade ainda não
  ativada, com a senha inicial: cai na troca obrigatória), `aviso-anexos`, `foto-grande` (o
  visualizador aberto), `documento` (morador) e `documento-gestao`, `aviso-documento`,
  `receber-avisos-iphone` (a página se apresenta como Safari do iPhone: o passo a passo da tela
  inicial). A faixa de push entrou no `mural` (o morador ainda não ativou).

### C4. `.opcao` e `.item` com letra grande
- **Decisão:** no comum, `@container conteudo (max-width: 17.5rem)` (o limite dos avisos, G1.1:
  nada muda com a letra de fábrica, nem num celular de 320 px): `.opcao` com gap e padding de
  0.5rem e o rádio de 1.25rem (o rótulo inteiro continua sendo o alvo); `.item` com padding menor
  (0.75rem; 0.5rem do lado da seta), `column-gap` de 0.25rem e a seta de 1rem. "apartamentos",
  "Receber", "condomínio" deixaram de quebrar.

### C5. Topo fixo numa tela baixa para a letra · [Erick]
- **Escolha entre** `line-clamp` no `h1` do topo e o topo deixar de ser fixo: o `line-clamp` não
  serve, porque no aviso aberto o assunto só aparece no topo (cortado, a pessoa não lê o
  título). **Decidido:** `@media (max-height: 35em)` (o mesmo limite da janela "O que mudou",
  G2-3): o `.topo` fica `position: static` e rola com a página, e o `scroll-padding-top` desce de
  5rem para 0.75rem (sem topo fixo, não há o que cobrir em cima). As abas de baixo continuam
  presas. 35em = 560 px de altura com a letra de fábrica, 840 a 150 %, 1120 a 200 %.
- **Com a letra de fábrica:** num celular em pé, nada muda (prints iguais). Com o celular
  **deitado** (altura < 560 px), o topo passa a rolar também, o que ali também ajuda.
- **[Erick]:** com letra grande, o botão de voltar e o de tema somem quando a pessoa rola para
  baixo (estão no topo). Voltar continua pelo gesto/botão do celular. Se a Dona Socorro sentir
  falta, a alternativa é fixar só a linha da seta de voltar.

### C6. Abas de baixo nunca encostam
- **Medido** (texto de cada aba e a folga até a borda dela, 320, 360 e 412 px, letra 16 a 32):
  "Documentos" mede 5,5 vezes a letra; com o teto da dúvida 1 (20 px a 360), dá 109 px numa aba
  de 90, e invadia 9 px de cada lado ("Enquetes" encostava). Baixar o teto não resolvia sem
  descer da letra mínima de 15 px (U10).
- **Decisão, dentro do teto:** `min-width: min-content` nas abas quando a tela é estreita para a
  letra (`@media (max-width: 22em)`: 352 px com a letra de fábrica, 528 a 150 %): "Documentos"
  ganha a largura da palavra e as outras dividem o resto (a 360 px e 200 %, as quatro somam 338 px
  e sobram pelo menos 7 px entre duas palavras). O número de não lidos ficou preso dentro da aba
  (`left: min(…, 100% - 1.25rem)`; com a letra de fábrica, a mesma posição).
- **Cinco abas (gestão) · [Erick]:** ali "Documentos" já não cabia **com a letra de fábrica**
  (83 px numa aba de 72: "EnquetesDocumentos" colados no painel a 360 px). O `min-content` vale
  sempre com cinco abas. **É a diferença de propósito nos prints a 16 px**: as abas de baixo do
  painel (`painel-360-16`), que agora têm espaço entre "Enquetes" e "Documentos". Se preferir o
  desenho antigo, é tirar uma linha.

### C7. Achados nas telas novas (consertados)
- **Foto grande:** "Próxima" saía da tela (o `.botao` tem `width: 100%`; agora `flex: 1 1 0` e
  `min-width: 0`) e "Foto 1 de 2" virava "F…" ao lado do "Fechar" (o topo do visualizador agora
  quebra a linha). Com letra grande (o visualizador é o próprio contêiner, 17.5rem), "Anterior" e
  "Próxima" ficam um embaixo do outro.
- **Aviso com anexos, letra grande:** as fotos em duas colunas de ~150 px cortavam o selo
  "Ampliar"; agora uma por linha (a foto maior também ajuda quem pôs a letra grande). O PDF põe o
  ícone em cima e o nome com a largura toda ("fiscalizaçã/o" deixou de quebrar).
- **"O que mudou", letra grande:** o padding da janela, o recuo da linha do tempo e o da lista
  deixavam ~150 px de texto (51 palavras quebradas no meio a 200 %). A `.janela-caixa` virou
  contêiner (`janela`) e, abaixo de 17.5rem, os recuos encolhem; a linha do tempo continua.

### C8. Alvos menores que 44 px: os mesmos de antes
- Só a grade de apartamentos a 360 px com a letra de fábrica (painel e "Quem leu", 38 × 44,
  dúvida 4). Nenhum alvo novo: o rádio menor da `.opcao` não é o alvo (o rótulo é).

### C9. Rodada completa antes × depois
`conferir-letra.mjs`, 28 telas, 360 e 1280 px, letra 16/24/32, tema claro; container
`m5-letra-costura`. "Antes" = `m5/integrado` (`b5d2107`) com o script novo; "depois" = costura.
Telas com o problema (e quantos achados, quando difere):

| fonte | largura | rolagem | fora | cortado | ícone encolhido | palavra quebrada | alvo < 44 | letra mediana |
|---|---|---|---|---|---|---|---|---|
| 16 | 360 | 0 → 0 | 0 → 0 | 1 → 0 | 1 → 0 | 0 → 0 | 2 → 2 | 18 → 18 |
| 16 | 1280 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 17 → 17 |
| 24 | 360 | 0 → 0 | 1 → 0 | 9 → 0 | 6 (9) → 0 | 0 → 0 | 0 → 0 | 27 → 27 |
| 24 | 1280 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 27 → 27 |
| 32 | 360 | 0 → 0 | 1 → 0 | 9 → 0 | 7 (39) → 0 | 6 (61) → 0 | 0 → 0 | 36 → 36 |
| 32 | 1280 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 36 → 36 |

- **16 px, `comparar-prints`:** 52 iguais, 4 diferentes: Minha unidade a 360 e 1280 e o "O que
  mudou" a 1280 (horário e quantidade de "aparelhos conectados", dado; a 360 também o ícone da
  C1) e o painel a 360 (as cinco abas, C6).
- **Não conferido:** tema escuro, e aparelho real (tarefa 6 do plano, do coordenador).
- **De passagem:** com `PENDENTES` vazio depois do merge dos três grupos, o `tsc -b` acusava
  `never` no `letra.test.ts`; o `Set` ganhou o tipo (`new Set<string>`). Nada muda no teste.

## Revisões

Duas revisões independentes (R = código, U = uso) depois da costura. Tudo em `m5/integrado`; a
direção do topo (A) foi decidida pelo coordenador. Testes novos: `web/src/casca/letra.test.tsx`
(detector), `casca/topo-letra.test.tsx` (topo e recado), `casca/rolar.test.ts`,
`casca/contato.test.tsx`, `web/testes/revisoes-m5.test.ts` (14 regras de CSS: as 14 falham com os
CSS de `ee10594` e passam agora) e o `letra.test.ts` reescrito (R6).

### A. Topo com letra grande: faixa fixa fina e título no conteúdo (R1, R2, U1, U2, C5)
- **O que mudou:** com `data-letra="grande"` no `html`, a `Tela` desenha o topo como faixa
  (`header.topo.faixa`): voltar **ou** a placa à esquerda, tema à direita, numa linha, e o
  recado (`.recado-lugar`) dentro dela. O `h1` vai para o começo do `main` (`.titulo-tela`),
  rolando com a página; continua o título da página (recebe o foco a cada tela, `tabindex -1`) e
  o "Pular para o conteúdo" cai nele. Com a letra de fábrica, o DOM e o desenho do topo são os de
  antes (prints iguais a 16 px, fora o documento aberto, abaixo).
- **A placa fica na faixa:** "só voltar e tema" vale para as telas de detalhe; nas de cima (sem
  voltar), a placa ocupa o lugar do voltar. Ela é mais baixa que o botão de tema (2.75rem), então
  a faixa não cresce, e é o elemento-assinatura do Portal.
- **Também no layout de computador com letra grande** (1366 × 768 a 150 %, monitor de 1920 a
  150 %): a mesma faixa (sem a placa, que o computador já escondia do topo) e o título no
  conteúdo. Separar os dois casos exigiria o React saber o layout; o desenho funciona nos dois.
- **Removido** o `@media (max-height: 35em)` que soltava o topo: com ele, o recado e o voltar
  sumiam ao rolar. O topo é sempre fixo; com o celular deitado e a letra de fábrica, volta a ser
  o topo fixo de antes (64 px).
- **Conferido no navegador:** a 360 px e 200 %, rolando "Quem leu" até o fim e tocando em
  "Copiar a lista", o recado aparece na faixa, no alto da tela (112 a 416 px).
- **Documento aberto (U17), mudança visível a 16 px, de propósito:** o topo diz só
  **"Documento"**, nas duas letras; o título inteiro está na folha, logo abaixo, agora como `h2`
  (era `p`, mesmo desenho), e na aba do navegador (`tituloDaAba` da `Tela`). O `line-clamp` do
  topo saiu. A 16 px: uma linha no topo em vez de duas cortadas ("Relatório mensal de…") e a
  página sobe ~6 px (morador, gestão; o documento público aberto sem entrar também).
- **Primeira tela:** a 150 % num iPhone (390 × 844), o "Abrir o documento" termina em 827 px (era
  892, fora da tela): com letra grande a folha tem menos respiro (0.875rem/0.75rem) e o título
  da tela fica mais junto da faixa.

### R1. "Letra grande" que vale também no iPhone
- **Por quê:** no iPhone o Dynamic Type chega pela declaração `font: -apple-system-body` do
  `html`; media query em `em` é medida pelo tamanho **inicial** (Media Queries 4, §1.3) e lá não
  acompanha. A spec 3.7 dizia o contrário ("a unidade que todo navegador mede pelo tamanho
  inicial" como vantagem): corrigida, com o porquê (spec 2.1 e 3.7).
- **Larguras:** `#root { container: raiz / inline-size }`, e todas as media queries de largura
  viraram `@container raiz (…rem)`: `56.25em` (estilo, marca, sobre, enquetes), `22em` (abas),
  `45em` (anexos), `37.5em` (anexos, gestão, documentos). O `rem` da container query é o do
  `html`. A largura do `#root` não conta a barra de rolagem (a media query contava): num
  navegador de computador com barra clássica, o layout de 2 colunas passa a valer ~15 px de
  janela depois. Nos prints (Chrome sem barra), igual.
- **Altura e topo:** `web/src/casca/letra.ts` marca o `html` com `data-letra="grande"` (raiz ≥
  20 px) e `data-altura="baixa"` (janela < 35 letras de altura), lendo o `font-size` calculado do
  `html`; uma régua invisível de 1rem (`ResizeObserver`) e o `resize` da janela remarcam quando a
  letra ou a tela mudam com o Portal aberto; `useLetraGrande()` (`useSyncExternalStore`) é o que
  a `Tela` lê. Roda no `main.tsx`, antes do primeiro desenho. "O que mudou" numa tela baixa
  (G2-3) usa `data-altura`.
- **Por que 20 px (125 %):** ficam no desenho de fábrica o "Grande" do iPhone (17 px, o padrão),
  o passo seguinte (19 px) e o 115 % do Android (18,4); passam para letra grande o 130 % do
  Android (20,8), o "Grande" do Chrome de computador (20) e o "Extra Grande" do iPhone (21) em
  diante.
- **Conferido:** o botão flutuante (`position: fixed`) continua preso à janela com o `#root`
  contêiner (no Chrome, `container-type` não faz o contêiner virar bloco de contenção de `fixed`).
- **A TESTAR no aparelho:** Safari < 16 não tem container query (o layout fica o de celular, sem
  os lado a lado de 37.5/45rem: degrada para uma coluna), e o Safari 16 tinha contenção de layout
  no `container-type` (o flutuante ficaria preso ao fim da página; conferir num iPhone com iOS
  16, se houver); e o detector com o Dynamic Type trocado com o Portal aberto.
- **Guarda:** o `letra.test.ts` recusa media query de tamanho em qualquer unidade e container
  query em `em`.

### R2. O recado na faixa fixa
- `topo-letra.test.tsx`: com letra grande o recado está dentro do `header.topo.faixa`, não no
  conteúdo; `costura-m5` e `revisoes-m5`: o `.topo` é `sticky`, a faixa não muda o `position` e
  não há mais `@media (max-height` no comum.

### R3. Ícones com atributo em número
- `width`/`height` em número (24) e a medida em rem pelo CSS (`.icone { width: var(--icone) }`,
  `--icone: 1.5rem` no `style`), no `Icone`, no `IconeAnexo` e no `IconeDoc`, pelo
  `tamanhoDoIcone` de `casca/emRem.ts`. Variável, não `style={{ width }}`: o inline venceria as
  regras mais específicas que mudam um ícone (a seta menor das listas com letra grande, C4). O
  React aplica o `style` pelo CSSOM, que a CSP (`default-src 'self'`) não bloqueia (como a barra
  da enquete). Testes dos três ícones ajustados.

### R4 + U10. Número de não lidos na aba
- A letra do número tem o teto da letra das abas (`min(0.8125rem, 4.75vw)`, a proporção 13/15 do
  5.5vw da dúvida 1), a plaquinha é medida em `em` sobre ela (`width: max-content`, senão o "120"
  vazava), e na aba estreita (`@container raiz (max-width: 22rem)`) ela fica presa no canto de
  cima, à direita, sobre a ponta do ícone. **Medido** a 360 px (aba de 76 a 90 px), com 1, 12 e
  120 não lidos, a 16, 24 e 32: dentro da aba nos 9 casos, e sobre o ícone só 8 px de altura (o
  canto). A 16 px, posição e tamanho de antes. O Portal não tem "99+": mostra o número da API.

### R5. Painel a 320 px e 200 %
- As cinco abas com `min-content` somavam 329 px (o respiro de 0.125rem de cada lado). Com cinco
  abas na tela estreita, o respiro cai para 0.0625rem: 320 px sem rolagem a 24 e 32, com 3 a
  4 px entre "Enquetes" e "Documentos" (medido; 320 não está na rodada). Com quatro abas, o de
  antes (C6: 6 a 8 px). Zerar o respiro de todas, a primeira tentativa, deixava "Enquetes" e
  "Documentos" a 1 px no mural a 360.

### R6. Guarda `letra.test.ts`
- Fechados, cada um com teste de exemplo e com mutação real num arquivo do Portal (o teste
  falhou nas 10 mutações e voltou a passar): `px|pt|pc|cm|mm|in|q` sem diferenciar maiúscula;
  `vw`/`vh` na letra fora de `min(rem, vw)`; `var()` na letra com token absoluto (mesmo o token
  liberado por comentário); teto de 4 px em borda, contorno e sublinhado; sombra em px só no
  token `--sombra`; `/* px: */` só na mesma linha do px; `style={{}}` com px (ou número puro) nos
  `.tsx`; o `<style>` do `index.html`; e media query de tamanho (R1).
- **No CSS, por causa dela:** sombras em rem (`inset 0 -0.25rem 0` da placa, da grade, dos
  blocos, da categoria e da enquete; a do flutuante e a da janela) e as faixas coloridas de 5 e
  6 px (cartão do aviso, faixa de notificações) em rem. A 16 px, os mesmos pixels.

### R7. `ambiente-conferencia.sh`
- `subir` chama `descer` no começo e tem `trap … ERR` (e desce também quando a API não
  responde); API e preview sobem com `setsid`, e o `descer` mata o grupo inteiro e a árvore
  (`pgrep -P`), não só o pid do `uv run`/`npm exec`. **Conferido:** dois `subir` seguidos; ficaram
  só os processos do segundo (o python e o node do primeiro morreram).

### U3. Confirmação mais alta que a tela
- `centralizar()` usa `block: 'start'` quando o bloco é mais alto que a altura visível (janela
  menos o `scroll-padding` de cima e de baixo). `rolar.test.ts`.

### U4. Menu lateral mais alto que a tela
- `overflow-y: auto` no `.nav` do computador: a 1366 × 768 e 150 %, ele mede 859 px numa janela
  de 768 e rola; o último item, a placa e a versão ficam alcançáveis. 1366 × 768 entrou na
  conferência (o `--larguras` aceita `LxA`: `360,390x844,1280,1366x768`).

### U5. Layout de celular numa tela larga
- No layout de celular, o conteúdo, o que está dentro do topo e as abas de baixo ficam numa
  coluna de 45rem centralizada (`max(16px, calc((100% - 45rem) / 2))`; o fundo das barras segue
  de ponta a ponta), e o flutuante acompanha a coluna. Num celular, nada muda. **Muda a 16 px**
  numa janela entre 752 e 899 px (tablet em pé): a coluna fica com 720 px em vez da largura
  toda. Fora da rodada.

### U6. Valores da ficha (Minha unidade, ficha da unidade, lista do painel)
- `casca/Contato.tsx`: `Celular` deixa o número (sem o DDD) numa linha só (`.fone-numero`,
  `nowrap`): só o "(81)" pode ficar na linha de cima. O número inteiro em `nowrap` passaria da
  borda a 200 % num celular de 360 (~280 px numa ficha de 264). `Email` põe `<wbr>` depois do
  `@` e antes de cada ponto (o texto copiado é o mesmo) e nunca ganha hífen.
- **Mudança visível a 16 px, de propósito:** o e-mail na ficha da unidade e em Minha unidade
  quebra em "gabriela.rangel.1101@" / "example.com" (era "…@exampl" / "e.com").
- Com letra grande (`@container conteudo (max-width: 17.5rem)`), rótulo e valor um embaixo do
  outro, os dois à esquerda.

### U7. Hifenização e a confirmação da ficha
- **Pesquisa (dados de compatibilidade do MDN, `css/properties/hyphens.json`):** `hyphens: auto`
  no Chrome do Android desde o 55 e no de computador desde o 88; dicionário de português ("pt,
  pt-*") no Chrome 87+ (o do Android segue o Chrome) e no Safari 9.1+ (o do iPhone segue o
  Safari); Safari < 17 só com `-webkit-hyphens`. Só hifeniza com o `lang` certo e o dicionário
  disponível (MDN); o `<html lang="pt-BR">` já existe. Confiável: usado.
- **Decisão:** `hyphens: auto` em títulos e texto corrido, **só com letra grande** (com a de
  fábrica mudaria a quebra de textos que hoje cabem), em palavra de 11 letras ou mais, 4 antes e
  3 depois do hífen (`hyphenate-limit-chars`): "se-nha", "Co-missão" e "Ca-pibaribe" liam pior
  que a palavra inteira na linha de baixo. Endereço, e-mail e telefone nunca ("portal-capi-
  baribe"). "Representante/s" virou "Representan-/tes".
- **Conferência:** o Chrome do Linux baixa os dicionários como componente, e o perfil temporário
  nascia sem eles; o `conferir-letra.mjs` copia o `hyphen-data` do Chrome do sistema e deixa o
  carregador de componentes ligado. A quebra numa caixa com `hyphens: auto` aparece à parte no
  resumo ("hifenizada, não conta").
- **Confirmação da ficha:** com letra grande, padding de 0.625rem/0.5rem e recuo da lista de 1rem
  (eram 1rem e 1.375rem). Não abre na conferência (precisa do toque); a regra é a do comum.

### U8. Grade de apartamentos com 4 colunas
- **Painel:** em 4 colunas, cada andar ganha o rótulo em cima ("7º andar", "Térreo";
  `aria-hidden`, cada casa já diz o apartamento) na linha inteira; com 8 colunas não aparece. As
  casas continuam com 2.75rem (44 px) de altura. **"Quem leu" e "Votantes", não:** ali a grade
  lista só quem leu ou votou (um subconjunto), e a linha nunca foi um andar.
- **Os 3 números do painel:** com letra grande, uma coluna só, uma linha compacta cada ("128 já entraram"),
  número a 1.375rem, à esquerda.

### U9. Caixa de recado, erro e atenção com ícone
- Com letra grande, `.aviso-caixa` empilha (ícone em cima, texto com a largura toda). O recado
  do topo (sem ícone) deixa o "Fechar" descer para baixo da frase quando não cabe ao lado.

### U11. Espaço entre os grupos do formulário · mudança visível a 16 px, de propósito
- Token `--entre-grupos: 1.5rem` (era 1.125rem) no `label` e nas legendas; o rótulo continua a
  0.375rem do campo dele. **Achado:** a legenda de um `fieldset` ignora a margem de cima (fica na
  borda dele): "Categoria" (novo aviso), "Bloco" (entrar) e as legendas da nova enquete ficavam
  a 0 px do campo de cima. Agora o espaço vai como `padding-top` da legenda. Muda a 16 px em todo
  formulário: entrar, primeiro acesso, esqueci a senha, novo aviso, novo documento, nova enquete
  (de 24 a 54 px mais altos).

### Mural com letra grande
- O resumo do cartão e o do fixado em até 3 linhas (`line-clamp`; o texto inteiro está no aviso
  aberto). A faixa "Falta um passo": sem o sino, menos respiro e botões com a altura mínima de alvo
  (2.75rem).

### Rodada final
`conferir-letra.mjs`, 28 telas, `--larguras 360,390x844,1280,1366x768 --temas claro,escuro`,
letra 16/24/32: 672 prints (`/tmp/portal-letra-rev-final/`; o painel de novo em
`/tmp/portal-letra-rev-final2/`, depois do último ajuste dos 3 números). Container
`m5-letra-rev`. "Antes" = `ee10594` com o script novo (`/tmp/portal-letra-rev-antes/`), que já
dava zero nas medidas automáticas: os achados das revisões eram de desenho, vistos nos prints.

| fonte | largura | rolagem | fora | cortado | ícone encolhido | palavra quebrada | alvo < 44 | letra mediana |
|---|---|---|---|---|---|---|---|---|
| 16 | 360 | 0 | 0 | 0 | 0 | 0 | 4 (painel e "Quem leu", claro e escuro) | 18 |
| 16 | 390 × 844 | 0 | 0 | 0 | 0 | 0 | 4 (os mesmos) | 18 |
| 16 | 1280 | 0 | 0 | 0 | 0 | 0 | 0 | 17 |
| 16 | 1366 × 768 | 0 | 0 | 0 | 0 | 0 | 0 | 17 |
| 24 | 360 / 390 / 1280 / 1366 | 0 | 0 | 0 | 0 | 0 | 0 | 27 / 27 / 27 / 25,5 |
| 32 | 360 / 390 / 1280 / 1366 | 0 | 0 | 0 | 0 | 0 | 0 | 36 |

- **Alvos < 44:** só a grade de apartamentos de 38 × 44 a 360/390 px com a letra de fábrica, a
  mesma de antes (dúvida 4). Nenhum novo.
- **Palavra hifenizada (não conta):** listada à parte no resumo; olhada nos prints, é a quebra
  na sílaba com hífen ("Representan-tes", "acompanha-mento", "notifi-cações").
- **16 px, `comparar-prints` (claro e escuro, 112 cada):** 70 iguais e 42 diferentes, todos de
  propósito ou dado: documento aberto e documento da gestão (topo "Documento", A), entrar,
  primeiro acesso, esqueci a senha, novo aviso, novo documento e nova enquete (U11), ficha da
  unidade e Minha unidade (e-mail, U6; em Minha unidade também o horário do "aparelho
  conectado") e "O que mudou" a 1280/1366 (o horário do aparelho na página de trás, dado). O
  painel, o mural e todo o resto: iguais.
- **Olhados os prints a 24 e 32** das telas mexidas (mural, painel, ficha, Minha unidade,
  documento, aviso, entrar, novo aviso, enquete, receber os avisos, "O que mudou"), claro e
  escuro, e a 1280/1366 (coluna centralizada; faixa no layout de computador).
- **Fora da rodada, medidos com sonda própria:** abas a 320/360/412 px com 4 e 5 abas (R5),
  número de não lidos com 1, 12 e 120 (R4), o recado com a página rolada (A), o flutuante
  (R1), o menu lateral a 1366 × 768 (U4) e o "Abrir o documento" a 390 × 844 (A).
- **Suíte:** `npm test` (vitest 681, node --test 77), `npm run lint` e `npx tsc -b` verdes.

### Dúvidas novas para o Erick
- **[Erick] Topo no computador com letra grande:** a faixa (só tema, o título no conteúdo) vale
  também no layout de computador quando a letra é grande; lá o topo de antes cabia. Dá para
  restringir ao celular se ele preferir.
- **[Erick] Hifenização com letra grande:** "Representan-tes" em vez de cortar sem hífen. Se a
  Dona Socorro estranhar o hífen, é tirar uma regra.
- **[Erick] Espaço entre os grupos (U11) e o topo do documento ("Documento")**: as duas mudanças
  visíveis com a letra de fábrica.
