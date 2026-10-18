# Navegação do celular: barra com arco e a bola do Menu (design)

Data: 18/10/2026 · Versão alvo: **1.7.0** (novidade visível = minor)
Origem: brainstorming com o Erick; desenhos em `.superpowers/brainstorm/222262-1792337475/content/`
(`navbar.html` opção **C**, `menu.html` opção **1**, `menu-muitos.html`), fora do git. Revisão
independente de UX feita antes deste documento (achados incorporados abaixo, marcados **[rev]**).

## 1. Por quê

- A gestão vê **5 abas** embaixo (Avisos, Enquetes, Documentos, Minha unidade, Unidades). Com
  72 px por aba, a letra precisa de teto e "Documentos" quase encosta nas vizinhas.
- A E2 (pós-entrega) traz reservas, encomendas, chamados e visitantes. A barra de abas não comporta
  mais lugares: Material e Apple limitam a 5 destinos e mandam o resto para um "Mais".
- O Erick quer a barra no jeito do **app da PlayStation**: um arco no topo, ícones e uma **bola no
  meio** que abre um menu para escolher o destino.

## 2. Objetivos, não-objetivos, anti-objetivos

**Objetivos**
- Barra de baixo com **4 lugares fixos** e uma bola central **Menu** que abre uma folha com **todos**
  os lugares, cada um explicado.
- **Um lugar novo = uma entrada numa lista única**, que alimenta a barra, a folha e o menu lateral
  do computador.
- Deve funcionar com letra grande (M5), tema escuro, Android, iPhone (Safari e PWA instalado) e
  leitor de tela.

**Não-objetivos**
- O menu lateral do computador continua como está, exceto pelos grupos e frases (seção 6).
- Busca dentro do menu: só se um dia passar de uns 12 lugares.
- Os lugares da E2 não entram agora. Aparecem nos desenhos só como exemplo.

**Anti-objetivos (fracasso, mesmo funcionando)**
- A Dona Socorro não saber o que é cada aba, porque ficou só o ícone ou o nome foi abreviado sem
  necessidade.
- A bola ser lida como "criar/+" (um FAB).
- O voltar do Android reabrir o menu, ou não fechar a folha.
- Rolagem lateral em qualquer largura ou tamanho de letra.
- A barra comer uma fatia grande da altura da tela.

## 3. A barra (decisões do Erick)

- **Opção C:** barra clara (`--folha`) com a **borda de cima em arco**. Ícone **e nome** em todas
  as abas.
- Ordem: **Avisos · Enquetes · [bola] · Documentos · Minha unidade**. "Minha unidade" quebra em
  duas linhas, entre as palavras.
- Aba ativa: cor `--mata`, negrito e um **tracinho brilhante** em cima (o "glow" do PS: barra de
  3 px com `box-shadow` da mesma cor). O contador de não lidos continua em Avisos, como hoje.
- **Bola central:** círculo `--mata` com o ícone de **grade de 9 pontos** em ipê e a palavra
  **"Menu"** sempre escrita embaixo. Com a folha aberta, vira **X** com **"Fechar"**.
- Unidades **sai da barra** e vai para o grupo Gestão da folha.

### Ajustes da revisão
- **[rev] Altura:** o arco é raso (uns 16 px de flecha) e a bola sobressai **no máximo meia
  altura** dela acima da barra. Meta: barra com no máximo ~96 px a 15 px de letra, contando a
  saliência. A barra de hoje tem ~64 px.
- **[rev] Letra:** com a coluna da bola no meio, os nomes inteiros só cabem com a letra da barra
  praticamente fixa: **piso de 15 px** (o do projeto) e teto pela largura, algo como
  `min(0.9375rem, calc((100vw - <coluna da bola>) / 17))`. Cada aba usa `min-content` (o truque
  atual de `estilo.css`). A letra da barra **não acompanha** a letra grande. Quem usa letra grande
  lê os nomes na folha, que **não tem teto**.
- **Barra de tamanho fixo em qualquer letra (minha escolha, depois do builder check):** tudo na
  barra (letra, ícone, bola, arco, espaçamentos, altura mínima) fica preso pela largura da tela,
  na forma `min(<rem de fábrica>, <vw>)` ou equivalente sem px, para **parar de crescer na letra de
  fábrica**. Critério: **barra ≤ 104 px de altura total a 16, 24 e 32 px de letra**, saliência da
  bola incluída e safe-area do iPhone excluída. A conferência a 24/32 px cobra esse número.
- **Celular estreito [decisão do Erick: "abreviar ou trocar"]:** a 320 px, "Documentos" a 15 px
  não cabe. **Minha escolha:** nessa faixa, só o rótulo da aba vira **"Docs"**. A página continua
  "Documentos" e o `aria-label` da aba continua "Documentos". O limite é a **largura real da
  tela** (~340 px CSS), **não** em rem: a letra da barra já não cresce, então a letra grande não
  pode empurrar todo celular para "Docs". Se o guarda de px do M5 recusar a media query em px, o
  builder documenta uma exceção nomeada no guarda, ou decide por JS (`innerWidth`). **O piso de
  15 px é absoluto:** o "Docs" resolve o resto. Conta: a 320 px, com "Docs", as quatro palavras e
  a bola somam ~265 px. Os outros rótulos não mudam.
- **[rev] Lugar atual fora da barra** (Unidades e, no futuro, Reservas etc.): nenhuma aba fica
  ativa. A **bola** ganha o tracinho e o "Menu" vai para negrito, mostrando que você está num lugar
  do menu.
- **[rev] Contador de um lugar que mora só na folha** (ex.: Encomendas, no futuro): pontinho ipê
  na bola, com `aria-label`. Não há caso hoje. Basta a lista de lugares aceitar um contador.
- **[rev] Tema escuro:** tokens próprios para a bola (fundo e ícone) nos dois temas, com contraste
  ≥ 3:1 entre ícone e fundo (WCAG 1.4.11). O `--mata` do escuro (#7fc79a) com o ipê dá ~1,2:1 e
  **não serve**. O anel em volta da bola usa `var(--papel)` e o arco usa `var(--folha)`, sem hex
  fixo.
- **[rev] Conteúdo atrás:** o `main` ganha `padding-bottom` e `scroll-padding-bottom` iguais à
  altura total, saliência incluída. Os cantos transparentes do arco não podem capturar toque.
  Nenhum cartão nem foco fica escondido atrás da bola (WCAG 2.4.11).
- **[rev] iPhone:** decidir se entra `viewport-fit=cover` no `index.html`. **Minha escolha: entra**,
  com `padding-bottom: env(safe-area-inset-bottom)` na barra, para o indicador de início não cobrir
  os rótulos no PWA instalado.
- Telas de detalhe continuam **sem barra** (com a seta de voltar no topo), como hoje.

## 4. A folha do Menu (decisão do Erick: opção 1, "lista com explicação")

- Folha que sobe de baixo, com cantos de cima arredondados, véu escuro atrás e uma pegadinha
  cinza. Título **"Para onde você quer ir?"**.
- **Um lugar por linha:** ícone num círculo `--mata-suave`, **nome** (grande) e **frase curta**
  embaixo ("Vote pela sua unidade"), mais uma seta. O lugar atual aparece destacado, com a frase
  "Você está aqui". As linhas de Avisos mostram o contador.
- **Grupos com título:** "Dia a dia" (Avisos, Enquetes, Documentos, Minha unidade) e "Gestão"
  (Unidades, só para quem é da gestão). A E2 vai criar outros. Os 4 da barra **se repetem** na
  folha de propósito: é o lugar com tudo.
- Frases iniciais (o builder pode polir, curtas):
  Avisos "Recados da Comissão e da obra" · Enquetes "Vote pela sua unidade" · Documentos
  "Memorial, atas e contratos" · Minha unidade "Senha, contato e e-mail" · Unidades "Quem já
  entrou e os contatos".
- Cresce até perto do topo, deixando uma faixa da tela de trás visível (`max-height` em `dvh`). A
  lista **rola por dentro** (`overscroll-behavior: contain`) e o fundo não rola (no iOS isso
  precisa ser travado à mão).
- **Fechar:** pela bola-X, tocando no véu, com Esc, pelo voltar do Android e **arrastando a
  pegadinha para baixo**. O arrasto é só um atalho: a pegadinha é `aria-hidden`, e o botão Fechar
  é a alternativa (WCAG 2.5.7). O arrasto não pode brigar com a rolagem da lista: só a pegadinha e
  o cabeçalho arrastam.
- Tocar num lugar navega e fecha a folha.
- **Barra com a folha aberta (minha escolha):** a folha encosta no fundo da tela e **cobre a
  barra**. As abas ficam atrás do véu, como todo o resto, sem redesenhar a barra dentro do dialog.
  A **bola-X** é desenhada dentro da folha, no mesmo ponto da tela onde estava a bola (o dedo não
  procura), com "Fechar" embaixo. A lista reserva a folga dela no fim.
- **Todo mundo tem a bola, o morador comum também (minha escolha):** é o mesmo mapa para todos,
  as frases ajudam quem não sabe o que é cada aba, e a E2 vai pôr lugares lá. Para o morador, hoje
  a folha repete as 4 abas, e isso é aceito.
- A letra da folha não tem teto e acompanha a letra grande como o resto do Portal.

### Acessibilidade e mecânica [rev]
- **`<dialog>` com `showModal()`**, que é o padrão do projeto (ver `sobre/BotaoVersao.tsx`). Com
  ele, o resto fica inerte, o foco fica preso e volta sozinho, o Esc fecha e, **no Chrome Android
  120+, o gesto de voltar fecha o dialog** (CloseWatcher), sem `pushState`. **Não usar o histórico
  para isso:** se em algum navegador o voltar não fechar, aceitar, porque é melhor do que o voltar
  reabrir o menu.
- Como o modal deixa a barra inerte, a **bola-X de fechar é desenhada dentro do `<dialog>`**, no
  mesmo lugar da bola de abrir.
- Bola de abrir: `<button>` com nome acessível "Menu", `aria-haspopup="dialog"` e
  `aria-expanded`. Ao abrir, o foco vai para o título da folha (`aria-labelledby`).
- Na folha: `aria-current="page"` na linha do lugar atual e `aria-label` no contador ("2 não
  lidos"), como na barra.
- Classe nova com outro nome: **`.folha` já existe** (lista do mural, `estilo.css`). Sugestão:
  `.menu-folha`.

## 5. Lista única de lugares

`casca/menu.ts` vira a fonte única. Cada lugar tem: `para`, `icone`, `texto` (nome), `curto`
(opcional, o rótulo da barra estreita), `frase`, `grupo`, `naBarra` (posição 1–4 ou nenhuma),
quem vê (função de `Eu`, como hoje com `itemEnquetes`/`itemDocumentos`) e o contador opcional. A
barra pega os de `naBarra`, e a folha e o menu lateral pegam todos, agrupados. **Pôr um lugar novo
= acrescentar uma entrada.** Se um lugar da barra não vale para alguém (a função devolve `null`),
a barra fica com menos abas e **ninguém sobe para a vaga** (minha escolha). A posição é fixa, e uma
barra que muda de ordem confunde. Testes: nenhum lugar aparece só na barra; a barra tem **no máximo
4** (hoje, 4 para todo papel); a bola existe para todo papel.

## 6. Computador

O menu lateral verde continua, agora **agrupado** (mesmos títulos de grupo) e saindo da mesma
lista, para a família ter um mapa só. Frases no lateral: **minha escolha, não**. O lateral tem
espaço para nome e ícone, e a frase ali seria ruído. Sem bola nem folha no computador.

## 7. O que fica com o builder

Medidas exatas do arco, da bola e das colunas, desde que caibam nas metas da seção 3. A animação
da folha, que deve ser curta e respeitar `prefers-reduced-motion`. A forma de travar a rolagem no
iOS. Os nomes de classes e componentes. O polimento das frases.

## 8. Pronto quando

- Testes (vitest) da lista única, da barra (4 + bola), da folha (abre, fecha pelos caminhos,
  `aria-*`, lugar atual) e da gestão (Unidades só na folha). O guarda de px do M5 continua verde.
- Conferência visual com o script do M5 (`scripts/dev/conferir-letra.mjs`) a **16/24/32 px** em
  **320/360/412**, claro e escuro: sem rolagem lateral, sem rótulo cortado, sem cartão escondido
  atrás da bola, barra ≤ ~96 px a 16 px. **Tudo headless:** nenhuma janela visível de navegador
  (o Erick usa o PC enquanto os agentes trabalham).
- Revisão independente de código e de UX, com as correções feitas e teste de regressão.
- `web/package.json` em **1.7.0**, com o item em `sobre/novidades.ts` no mesmo commit.
- Antes de anunciar no grupo: teste em Android e iPhone reais.
