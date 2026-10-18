# Dúvidas das indicações de serviços (1.8.0)

Decisões que nem o spec (`specs/2026-10-18-indicacoes-design.md`) nem o plano
(`plans/2026-10-18-indicacoes.md`) fecharam e que mudam o que o morador vê. Em cada uma, a escolha
foi a que o spec mais sugere; dá para trocar sem mexer em regra nenhuma.

1. **Título do prestador aberto.** O topo diz "Indicação" e o nome do prestador vem logo abaixo,
   em destaque (o nome vai também para a aba do navegador), como no documento aberto. Nome
   comprido no topo ocupava duas ou três linhas no celular.
2. **"Sair sem publicar?" própria.** A pergunta dos avisos diz "o que você escreveu e os anexos
   vão se perder"; aqui não há anexo, então a frase é "O que você escreveu na indicação vai se
   perder." (mesmo desenho e os mesmos botões).
3. **Contagem zero.** Prestador sem nenhum "recomendo" visível mostra "Nenhum vizinho recomenda
   ainda" (o spec só fala de "N vizinhos recomendam").
4. **Busca ou categoria sem resultado** mostra "Nenhuma indicação encontrada." O convite "Ainda
   não tem indicação aqui. Seja o primeiro a indicar alguém." fica só para a lista vazia de
   verdade (sem filtro), com o botão.
5. **Avisar a gestão.** A confirmação diz "A Comissão e a administração vão olhar esta indicação.
   Elas não veem quem avisou." (decisão 9 do plano: o aviso chega sem a placa). O campo se chama
   "O que está errado? (opcional)", com contador até 300.
6. **Opinião escondida.** A frase é "A gestão escondeu a sua opinião. Ela não aparece para os
   vizinhos e não pode ser mudada nem apagada." (o spec só dá o começo).
7. **"Esconder esta opinião"** aparece em todas as opiniões visíveis para a gestão, inclusive na
   dela mesma, e some quando o prestador já está escondido.
8. **Ícone do lugar no menu:** um polegar para cima, no traço de `Icone.tsx`.
9. **Recados** (a caixa do topo): "Indicação publicada. Obrigado!", "Esse telefone já está na
   lista. Dê a sua opinião aqui.", "Sua opinião foi publicada/mudada/apagada.", "A gestão foi
   avisada. Obrigado!", "Os dados do prestador foram corrigidos.", "Prestador escondido da
   lista.", "Opinião escondida.", "Aviso resolvido.".
10. **E-mail do primeiro aviso.** Assunto "Portal Capibaribe Prime: aviso numa indicação"; o corpo
    diz que um vizinho avisou que tem algo errado, com o nome e a categoria do prestador e o
    botão "Abrir a indicação". Sem o motivo e sem a placa.
11. **Prestador escondido e "apagar meus dados".** A trigger da 0010 recusa qualquer mudança no
    prestador escondido, menos o `criado_por` virar nulo: sem isso, quem indicou um prestador que
    depois foi escondido não conseguiria apagar os próprios dados.
12. **Conferência visual:** além das cinco telas do plano, a `indicacao-opinar` (o prestador com
    o formulário da opinião aberto, `?opinar=1`), que nenhuma outra tela media. Foi ela que achou
    o "Recomendo / Não recomendo" passando da tela com a letra a 200 % em 320 e 360 px.

## Lembrete para o coordenador

A migração **0010 precisa ir para o Neon antes do push** (regra do backup).
