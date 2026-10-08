# Dúvidas e decisões do M2 · Épico B (e-mail e "esqueci a senha")

Decisões tomadas sem perguntar durante o épico B. **[Erick]** marca o que só o Erick pode
confirmar; **[coordenador]** marca o que mexe em arquivo comum ou precisa de atenção no merge; o
resto é decisão técnica que pode ser revista na revisão do marco.

## 1. Dois testes comuns tiveram de mudar **[coordenador]**
- `web/src/m2contrato.test.ts`: saiu só a linha `expect(rotasRecuperacao).toEqual([])` (e o
  import dela). O épico A vai tirar a linha vizinha (`rotasNotificacoes`): no merge, o teste
  "pontos de encaixe" fica sem as duas, e a resolução é apagar as duas.
- `api/testes/test_m2_em_construcao.py`: apagada a seção do épico B, como o contrato manda, e os
  imports que só ela usava (`CABECALHO_PORTAL`, `ROTAS_RECUPERACAO`). O épico A apaga a dele; o
  arquivo provavelmente some no merge.

## 2. `Entrar.test.tsx` passa, mas o nome dele ficou velho **[coordenador]**
- O teste "esqueci a senha: até o M2, falar com a administração" clica em "Esqueci minha senha"
  e procura "Fale com a administração do Portal no grupo do WhatsApp". Continua verde porque a
  tela nova tem essa frase (a dica para quem não tem e-mail), mas o nome descreve o M1. Não
  mexi (arquivo do épico A do M1, comum no M2). Sugestão no fechamento: renomear para "esqueci
  a senha leva à tela do link" ou apagar (o `recuperacao.test.tsx` já cobre).
- A classe `.acesso-esqueci` de `web/src/acesso/acesso.css` deixou de ser usada (era o
  `<details>` do M1). Pode sair no fechamento.

## 3. Rodapé do aviso por e-mail diz que apagar o e-mail desliga o "esqueci a senha" **[Erick]**
- **Dúvida:** o contrato pede o rodapé "Você recebe porque cadastrou este e-mail… Para não
  receber mais, apague o e-mail em Minha unidade." A dúvida 7 do contrato registra que isso
  também desliga a recuperação de senha.
- **Decisão:** o rodapé ganhou "Sem e-mail, o “esqueci a senha” também deixa de funcionar."
- **Por quê:** a Dona Socorro que apaga o e-mail para parar as cópias não pode descobrir isso só
  no dia em que esquecer a senha. Se o Erick achar comprido, é uma constante
  (`RODAPE_DO_AVISO` em `app/servicos/email.py`).
- **Substituído na 1.3.0 (ajustes do M2):** o rodapé agora diz "Para não receber mais, desmarque
  “Receber os avisos por e-mail” em Minha unidade.", e o alerta sobre o "esqueci a senha" saiu
  (desmarcar não apaga o e-mail). Ver o fim de `duvidas-m2.md`.

## 4. O texto puro do e-mail leva o aviso como foi escrito
- **Decisão:** na parte de texto puro vão as marcas (`## `, `- `, `1. `, `> `, `**`), sem
  converter. Na parte HTML, o Markdown restrito do Portal é convertido (porte de
  `web/src/avisos/formatacao.ts`, com teste de paridade usando os mesmos exemplos do front).
- **Por quê:** essas marcas foram escolhidas por serem legíveis como texto; tirar o `- ` de uma
  lista a deixaria pior. Quase todo leitor de e-mail mostra a parte HTML.

## 5. O que conta como falha de um destino e o que interrompe o canal
- **Decisão (corrigida na revisão, item 16):** destinatário recusado (`SMTPRecipientsRefused`)
  e mensagem recusada comum (`SMTPDataError`, ex.: 552 5.3.4) contam como falha daquele destino
  e o envio segue. `SMTPDataError` com código 421 ou 5.4.5 / 4.7.x no texto, remetente recusado
  e qualquer outro erro (conexão caiu, tempo esgotado, senha de app errada) interrompem o canal.
- **Por quê:** o Gmail avisa a cota diária estourada recusando o remetente ou a mensagem
  (`550 5.4.5`); continuar seria bater na mesma parede 300 vezes. A peça comum já marca `interrompido` com as
  contagens até ali e loga só o tipo do erro.

## 6. Uma conexão por lote, tempo limite de 20 s
- **Decisão:** a cópia de um aviso abre **uma** conexão SMTP e manda todas as mensagens por
  ela (uma mensagem por unidade, um destinatário em cada); o "esqueci a senha" abre uma só para
  o link. `TEMPO_LIMITE_SMTP = 20` s por operação; 465 com TLS direto (padrão do Gmail) e
  STARTTLS em outra porta; certificado conferido.
- **A medir no portão do M2:** quanto leva cada mensagem no Gmail de verdade. Se 300 mensagens
  passarem dos 240 s, o resto vira `pulados` (dúvida 20 do contrato).

## 7. Sem `List-Unsubscribe` **[Erick]**
- **Dúvida:** cabeçalho de "cancelar inscrição" ajuda a não cair no spam.
- **Decisão:** não pôr. O jeito de parar é apagar o e-mail em Minha unidade (dúvida 7 do
  contrato), que exige entrar; um link de cancelar sem entrar pediria uma rota e um token novos.
  As exigências de remetente em massa do Gmail valem a partir de 5.000 mensagens por dia, longe
  dos 450 do Portal. Pus `Auto-Submitted: auto-generated` (respostas automáticas de férias não
  voltam para a conta do Portal).

## 8. E-mail sem imagem nem logo
- **Decisão:** HTML só com texto, tabela de 600 px e estilos inline (faixa verde com o nome do
  Portal, rótulo da categoria com nome e cor, botão "Abrir no Portal" e o endereço escrito
  embaixo para quem não consegue tocar no botão).
- **Por quê:** imagem vem bloqueada por padrão em muito leitor de e-mail e, sem domínio próprio
  (ADR-0008), apontaria para a Vercel. Fonte Atkinson com recuo para Arial (leitor de e-mail
  raramente carrega fonte).

## 9. Pedido de unidade desativada: nada, nem histórico
- **Decisão:** unidade com `ativa = false` é tratada como inexistente no pedido (não grava
  `recuperacao_pedida`).
- **Por quê:** é a regra do `entrar` (desativada = inexistente) e o contrato fala em "unidade
  ativa"; o histórico serve para a administração procurar uma família de verdade.

## 10. Resposta e tempo iguais com e sem e-mail: como é testado
- O teste do contrato já quebra o banco dentro da requisição do pedido. O épico B acrescentou:
  respostas byte a byte iguais (corpo e tamanho) para unidade com e-mail, sem e-mail e
  inexistente, e a rota chamada direto só agenda o mesmo trabalho, sem rodar nada, para os
  três casos. Não há teste que mede milissegundos: no `TestClient` o trabalho de segundo plano
  roda antes de a chamada voltar, então a medida não provaria nada; o que garante o tempo igual
  é a rota não fazer nada diferente dentro da requisição.

## 11. "Esqueci minha senha": dica para quem não tem e-mail **antes** de pedir
- **Decisão:** além da caixa depois do pedido (como no protótipo), a tela mostra embaixo do
  botão "Não cadastrou e-mail? Fale com a administração do Portal no grupo do WhatsApp. Ela volta
  sua senha para a inicial.".
- **Por quê:** quem sabe que não tem e-mail não precisa pedir um link que nunca chega. Não revela
  nada da unidade (é igual para todas). Ficou de fora o botão "Pedir de novo" do spec: pedir de
  novo é voltar à tela, e o limite de 3 por hora já existe.

## 12. Tela do link com outra unidade já entrada no aparelho
- **Decisão:** `/redefinir-senha` é pública; se o aparelho estiver entrado como outra unidade,
  salvar a senha nova troca a sessão deste aparelho para a unidade do link.
- **Por quê:** o link prova a posse do e-mail daquela unidade; é o caso do celular da família
  que tem duas unidades. O texto acima do botão avisa que este aparelho entra e os outros da
  família saem.

## 13. O `#token` sai da barra antes de conferir
- **Decisão:** a tela lê o token uma vez, troca o endereço por `/redefinir-senha` (sem o `#`,
  `replace`) e só então chama `conferir`. Link sem token mostra a mesma tela de link vencido
  ("Este link está incompleto…") sem chamar a API.

## 14. Conferência visual sem e-mail de verdade
- A API local subiu com `smtplib.SMTP_SSL` trocado por um objeto que grava cada mensagem num
  arquivo `.eml` (script fora do repositório, na área temporária). Banco próprio
  `portal_dev_m2_email`. Nenhuma mensagem saiu da máquina.

## 15. Texto sugerido para as novidades da 1.2.0 **[coordenador]**
- "Esqueceu a senha? Na tela de entrar, toque em “Esqueci minha senha”: se o apartamento tiver
  e-mail cadastrado, chega um link para criar uma senha nova. E quem cadastrou e-mail passa a
  receber os avisos também por lá."

## 16. Revisão independente (código e UX): o que mudou
Duas revisões sem contexto; cada correção com teste que falhava antes.
- **Cota do Gmail na mensagem interrompe** (código 1): `SMTPDataError` com código 421 ou com
  5.4.5 / 4.7.x no texto (cota do dia, limite de envio) e `SMTPSenderRefused` interrompem o
  canal; mensagem recusada comum (ex.: 552 5.3.4) continua sendo falha só daquele destino. O
  item 5 acima fica corrigido por este.
- **Dois links da mesma unidade ao mesmo tempo** (código 2): `_token_que_vale(travar=True)`
  trava o token **e a unidade** (`for update of token_recuperacao, unidade`); teste de corrida
  com dois links e com o mesmo link.
- **Reserva presa por 24 h** (código 3): resolvido **sem tocar em `notificacoes.py`**. O
  `ENVIADOR` do e-mail, ao levantar, baixa `resultado.reservados` para o que foi tentado (a
  mensagem que estava saindo fica contada); a peça comum já grava `resultado.contagens()` no
  `interrompido`, então a sobra volta à cota. No "esqueci a senha", se nem conectou
  (`email.NadaSaiu`), o token é apagado (devolve a cota e um dos 3 pedidos da hora); se caiu
  durante o envio, o link fica (pode ter chegado).
- **Limite por IP do pedido** (código 4): fica com o coordenador (regra no firewall da Vercel
  para `/api/acesso/recuperacao`, como na dúvida 8 do contrato). Nada no código.
- **Apartamento que não existe** (UX 5): a tela de pedir usa a planta do protótipo
  (`/^[1-5][0-7]0[1-8]$/`, `UNIDADE_OK`). **[coordenador]** A tela de entrar (`Entrar.tsx`, do
  épico A do M1) usa uma regra mais solta (`/^[1-9][0-7][0-9]{2}$/`, a mesma da API) e responde
  "Bloco, apartamento ou senha incorretos" para os dois casos; não mexi nela.
- **Pedido feito** (UX 6): "Pedido feito para o Bloco N, apartamento NNN. O e-mail chega em
  alguns minutos, de Portal Capibaribe Prime (<conta>), com o assunto “…”. Se não aparecer,
  olhe também em Spam ou Lixo eletrônico. O link vale por 1 hora."; o foco vai para a caixa.
  **Mudança de contrato no épico:** `RecuperacaoPedida` ganhou `remetente` (a
  `PORTAL_SMTP_USUARIO` da configuração, ou nulo com o e-mail desligado; nunca fixo no código) e
  `assunto`, iguais para qualquer login (a rota continua sem abrir o banco). **[coordenador]**
  Por isso a asserção de texto exato de `test_pedido_responde_igual_e_deixa_tudo_para_depois`
  (`test_m2_rotas.py`, comum) virou "respostas iguais entre si e `mensagem` = `MSG_PEDIDO`".
  Palavra única: "enviar" ("Enviar link", "enviamos", "Enviado pelo Portal" no e-mail), a mesma
  da frase de H-04.
- **E-mail de recuperação** (UX 7): "Olá!", "Você (ou alguém da sua família) pediu “Esqueci
  minha senha”…", e, depois do botão, "O link abre o Portal do condomínio, em <host de
  PORTAL_URL_BASE>. O Portal nunca pede sua senha por e-mail nem por WhatsApp.".
- **Link já usado** (UX 8): com o aparelho entrado, "Você já está no Portal. Para trocar a senha
  de novo, vá em Minha unidade." + "Ir para os avisos". Sem sessão, a mensagem do 410 ganhou
  "Se você já criou a senha nova, é só entrar com ela." (mudança de texto do contrato, no
  épico).
- **Menores** (UX 9): assunto do aviso = o título, com "Urgente: " na frente se for urgente
  (antes "Aviso do Portal: <título>", do contrato); "Publicado pela Comissão em 07/10, às 21h23"
  (assinatura do mural, `ASSINATURAS` de `servicos/avisos.py`, UTC−3 fixo de Recife: sem horário
  de verão desde 2019 e sem depender do tzdata da função); prévia escondida no topo do HTML (o
  resumo do aviso); `color-scheme` e `supported-color-schemes` claros; "a senha que a Comissão
  mandou no grupo" no lugar de "a senha inicial"; recado depois de salvar com "Avise a família
  da senha nova."
