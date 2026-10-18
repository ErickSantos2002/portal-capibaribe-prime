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
   da barra, por cima da página. Nas abas, continua em cima, como no desenho.
3. **A bola-X mora num pé fixo da folha**, da altura da barra, fora da parte que rola. Assim o
   "Fechar" nunca fica por cima de um lugar quando a lista rola. O preço é uma faixa no fim da
   folha. No desenho (`menu.html`), a folha parava acima da barra, mas o spec decidiu que ela
   cobre a barra.
4. **Com letra grande num celular** (a tela com menos de 15 letras de largura, ex.: 360 px a
   150 % ou 320 px a 200 %), a folha esconde o círculo do ícone e a seta de cada lugar. Sem isso,
   "Documentos" quebrava no meio da palavra. Ficam o nome, a frase e o realce do lugar atual.
5. **O teto de 104 px da barra vale para celular (largura < 600 px).** No layout de celular numa
   tela larga (notebook de 1280 px a 150 % ou 200 %, que não cabe o menu lateral), o teto pela
   largura (`vw`) não segura nada, e a barra acompanha a letra como o resto da página: 136 px a
   24 px de letra e 182 px a 32 px, numa tela de 900 px de altura. Segurar isso exigiria px ou vh
   na letra, que o guarda do M5 proíbe. Se incomodar, o caminho é uma exceção nomeada no guarda.
6. **O número de não lidos na aba tem teto de 13 px a 320 px** (`min(0.8125rem, 4.06vw)`): com o
   teto antigo a letra dele caía para 10 px no celular estreito.
7. **O realce de "passar o mouse" na folha só vale com mouse** (`@media (hover: hover)`). No
   toque, o `:hover` grudava na linha tocada e parecia um segundo "você está aqui".
8. **"Menu" fica uns 5 px mais baixo que os nomes das abas.** O círculo da bola é mais alto que o
   ícone das abas, e o nome vem logo abaixo dele. Alinhar exigiria encolher a bola ou subir a
   barra.

## Fora do escopo, achado na conferência

A conferência acusa 4 problemas que já existiam antes desta branch (conferido rodando o build do
commit `b1c2c11` no mesmo ambiente): o painel de unidades a 360 px com a letra de fábrica tem os
apartamentos com 38 px de largura (alvo < 44), e o aviso fixado do mural a 320 px e 200 % corta o
texto da faixa ("Fixado pela Administração do Portal"). Não mexi.
