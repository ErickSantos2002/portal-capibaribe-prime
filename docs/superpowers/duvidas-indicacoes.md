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

## Correções das revisões (código e UX)

Escolhas feitas ao corrigir os achados das revisões independentes. Cada conserto tem teste de
regressão que falhava antes.

13. **Cota do Gmail no histórico.** A reserva dos e-mails do primeiro aviso saiu da linha de
    `aviso_servico` (que "apagar meus dados" e o reset apagam, e a cota voltava) e foi para o
    `historico`, que o app só insere e ninguém apaga: ação do Portal `indicacao_aviso_email`
    (unidade nula, entidade `prestador`, `{"reservados": n}`), somada em
    `emails_nas_ultimas_24h`. Foi o mais simples e coerente: o `notificacao_envio` é por aviso
    do mural e tem chave estrangeira para ele; uma tabela nova só para isso seria mais uma coisa
    para o backup e a LGPD. Efeito visível: o Histórico da administração mostra "mandou e-mail à
    administração sobre um aviso numa indicação" (sem a placa de quem avisou). A coluna
    `emails_reservados` saiu da 0010 (ainda não aplicada no Neon).
14. **Celular sem o nono dígito.** Com 10 dígitos e o terceiro de 6 a 9, a API põe o 9; de 2 a
    5 é fixo; 0 e 1 são recusados ("Escreva o WhatsApp ou o telefone com DDD…"). O check da
    0010, o modelo e a tela seguem a mesma regra.
15. **Limite de avisos:** 10 por apartamento a cada 24 horas, na trigger (como os de indicação e
    opinião). A frase do 429: "Seu apartamento já avisou a gestão muitas vezes hoje. Tente de
    novo amanhã."
16. **Telefone fixo:** "Ligar: (81) 3333-4444" vira o botão principal e o WhatsApp fica como
    botão leve, sem sumir (fixo pode ter WhatsApp Business). O número só pode quebrar entre o
    DDD e o resto.
17. **Rascunho da opinião** (409 e "Dar minha opinião lá"): vai no `state` da navegação e só
    preenche o formulário quando a unidade ainda não opinou; com opinião, vale a dela.
18. **Foco.** Além do que a revisão pediu, "Corrigir os dados" também devolve o foco ao botão ao
    fechar, e "Continuar escrevendo" em "Sair sem publicar?" faz o mesmo que o Esc (foco no
    Voltar).
19. **Erro de formulário.** No padrão das enquetes: um erro só, a caixa do topo diz qual; mais de
    um, "Confira os campos marcados.". O erro do campo some ao editar, também em "Corrigir os
    dados".
20. **Busca ou categoria sem resultado.** Com busca: "Limpar a busca". Só com filtro (categoria
    ou "com aviso"): "Ver todas". Com categoria, também "Indicar alguém". "Todos" fica
    desmarcado enquanto o filtro "com aviso" está ligado (e tocar nele desliga os dois).
21. **Contraste da categoria:** token novo `--ipe-texto` no `estilo.css` (arquivo comum), porque
    nenhum token existente dava 4,5:1 em ipê. `--ipe-forte` continua nos focos e marcações.
22. **Privacidade:** a frase diz que Minha unidade mostra nome, celular e e-mail, e que as
    opiniões ficam à vista na página de cada prestador, nas Indicações.

## Para o coordenador

- **Primeiro cartão com a letra a 200 % em 320 px.** A faixa rola dentro dela também com a
  letra grande, o rótulo da busca ficou em duas linhas e a faixa mais baixa: o cartão subiu de
  y = 715 para y = 581 numa janela de 780, acima das abas de baixo (698). Mas o botão flutuante
  "Indicar alguém" ocupa de 570 a 682 nessa combinação e cobre o começo do cartão. Com 24 px, ou
  de 360 px para cima com 32 px de altura de janela maior, o cartão aparece inteiro. Resolver de
  vez pediria mexer no botão flutuante com a letra grande (padrão comum a outras telas), o que
  não fiz sem perguntar.
- **Prestador escondido não anonimizado**, como pedido: fica para a decisão do dono.
