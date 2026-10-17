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
