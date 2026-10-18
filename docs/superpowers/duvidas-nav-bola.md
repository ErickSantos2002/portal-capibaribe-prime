# Dúvidas da navegação com a bola (decisões tomadas sem perguntar)

Spec: `docs/superpowers/specs/2026-10-18-navegacao-bola-design.md` · Plano:
`docs/superpowers/plans/2026-10-18-navegacao-bola.md`. Cada item é uma decisão que muda o que o
morador vê e que nem o spec nem o plano fechavam. Escolhi o que o spec mais sugere; se não servir,
cada uma é uma troca pequena.

1. **A bola acende sempre que nenhuma aba da barra é a atual**, não só nos lugares da folha. Ex.:
   `/historico` (da administração) não é um lugar da lista, e mesmo assim a bola fica com o
   tracinho e "Menu" em negrito. É o que o Review Focus 4 do plano pede, e é o "você está num
   lugar do menu" do spec.
2. **O tracinho da bola fica embaixo de "Menu"**, não em cima do círculo. Em cima, ele cairia fora
   da barra, por cima da página. Nas abas, continua em cima, como no desenho. A revisão (U5) pediu
   os dois na mesma posição; **não mudei**: o único lugar comum seria embaixo do nome nas abas
   também, e o tracinho em cima é o "glow" do app da PlayStation que o spec pede (seção 3). O
   que a revisão também pediu, e foi feito, é que o lugar atual não dependa só dele (U6, abaixo).
3. **A bola-X mora num pé fixo da folha**, da altura da barra, fora da parte que rola. Assim o
   "Fechar" nunca fica por cima de um lugar quando a lista rola. O preço é uma faixa no fim da
   folha. No desenho (`menu.html`), a folha parava acima da barra, mas o spec decidiu que ela
   cobre a barra.
4. **Com letra grande num celular** (a tela com menos de 15 letras de largura, ex.: 360 px a
   150 % ou 320 px a 200 %), o nome de cada lugar ganha a linha inteira: o ícone, menor (círculo
   de 2rem), sobe para cima dele, a seta sai, e um fio separa as linhas (revisão U4; antes o ícone
   também sumia e a lista virava texto corrido). Sem isso, "Documentos" quebrava no meio.
5. **O teto de 104 px da barra vale para celular (largura < 600 px).** No layout de celular numa
   tela larga (notebook de 1280 px a 150 % ou 200 %, que não cabe o menu lateral), o teto pela
   largura (`vw`) não segura nada, e a barra acompanha a letra como o resto da página: 143 px a
   24 px de letra e 190 px a 32 px (eram 136 e 182 antes do U5, que subiu o topo das abas em
   4 px). Segurar isso exigiria px ou vh na letra, que o guarda do M5 proíbe. **Aceito pelo dono.**
   A revisão mediu com zoom de verdade (1280 × 800 a 150 % e a 200 %, letra de fábrica): a barra
   tem 91 px (95 depois do U5), dentro da meta. O caso de 136 a 190 px só aparece com zoom **e**
   letra grande ao mesmo tempo.
6. **O número de não lidos na aba tem teto de 13 px a 320 px** (`min(0.8125rem, 4.06vw)`): com o
   teto antigo a letra dele caía para 10 px no celular estreito.
7. **O realce de "passar o mouse" na folha só vale com mouse** (`@media (hover: hover)`). No
   toque, o `:hover` grudava na linha tocada e parecia um segundo "você está aqui".
8. **"Menu" na mesma linha dos nomes das abas (revisão U5; antes ficava 5 a 8 px abaixo).** A
   bola agora mede exatamente o espaço até o nome da aba (`--bola` = flecha + saliência + topo +
   ícone), e o topo das abas subiu de 6 para 10 px para a bola não encolher demais: 56 px na letra
   de fábrica (eram 60), 45 a 320 px. A barra foi a 95 px a 412/16 (meta ≤ 96) e a 103,4 px a
   412/32 (meta ≤ 104). Medido no Chrome: "Menu" e os nomes a 1 px um do outro em 320, 360 e 412,
   a 16 e 32 px.

## Revisões independentes (código e UX), corrigidas

- **C1.** As regras do menu lateral do computador (`.nav a`, `.nav .conta`) pegavam os lugares da
  folha, que também mora no `.nav`: brancos sobre a folha branca no claro, no iPhone grande que gira
  com ela aberta. Agora são `.nav-lateral …`. E a folha fecha quando a barra some (o layout virou o
  do computador): `ResizeObserver` na barra. Girar um notebook com letra grande não fecha, porque lá
  continua o layout de celular (conferido a 1280 px com letra 24 e 32).
- **C2.** O número de não lidos fica preso pela direita da aba. Com um algarismo, no mesmo ponto de
  antes; "120" cresce para a esquerda, por cima do ícone. **Não só na tela estreita:** medido no
  Chrome, ele vazava 3 px a 320, e também 7 a 8 px a 360 e 412 com letra grande; por isso a regra é
  a da barra toda. Agora dentro da aba nos 6 casos.
- **C5.** Arrastar de dentro da folha até o véu não fecha (o toque tem que começar no véu).
- **U1.** Ao abrir, o lugar atual rola para a vista dentro da lista; o foco continua no título.
  Conferido a 360 px com 16, 24 e 32 px de letra (Unidades, o último, inteiro à vista).
- **U2.** Fio embaixo do cabeçalho (há lugares acima) e fio com sombra leve em cima do pé (há
  lugares abaixo), só quando a lista rola.
- **U3.** "Fechar" em `1rem`, sem teto (16, 24, 32 px). O pé cresce junto, a partir da altura da
  barra: até 24 px de letra a bola-X fica no ponto exato da bola; a 32 px, ela sobe 5 px (o "Fechar"
  maior embaixo dela). No mesmo ponto na horizontal.
- **U6.** Lugar atual: fundo arredondado atrás do ícone da aba e no anel da bola acesa (token
  `--barra-aceso`). No claro é o `--mata-suave`; **no escuro não**: o `--mata-suave` do escuro
  (`#1c2e23`) dá 1,2:1 com a barra e não aparece; o token do escuro é `#2b4a37` (1,7:1 com a barra,
  e o ícone verde por cima com 4,9:1).
- **U7.** No escuro, o anel da bola é a `--linha` (token `--bola-anel`; no claro, o `--papel`).
- **Testes:** a conta da altura na tela estreita agora lê a letra da tela estreita (C3), e o Tab
  preso da folha tem teste (C4).

## Fora do escopo, achado na conferência

A conferência acusa 4 problemas que já existiam antes desta branch (conferido rodando o build do
commit `b1c2c11` no mesmo ambiente): o painel de unidades a 360 px com a letra de fábrica tem os
apartamentos com 38 px de largura (alvo < 44), e o aviso fixado do mural a 320 px e 200 % corta o
texto da faixa ("Fixado pela Administração do Portal"). Não mexi.
