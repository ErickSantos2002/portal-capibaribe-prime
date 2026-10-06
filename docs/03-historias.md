# 03 · Histórias de usuário — Entrega 1 (fase de obra)

| | |
|---|---|
| **Status** | v0.1 |
| **Autor** | Erick Santos Dantas |
| **Criado em** | 02/10/2026 |
| **Base** | `02-requisitos.md` v0.2, somente a **E1** |
| **Próximo documento** | `04-modelo-de-dados.md` |

---

## 1. Como ler

Cada história segue o formato **Como … quero … para …**, e em seguida vêm os **critérios de
aceite** no formato *Dado / Quando / Então*. A história só está pronta quando todos os critérios
passam, e cada critério vira pelo menos um teste automatizado.

As histórias de E2 e E3 serão escritas quando essas entregas começarem: escrever agora seria
adivinhar, porque o prédio ainda nem foi entregue.

## 2. Personagens

Pessoas fictícias que representam quem vai usar o Portal. Servem para testar cada tela
perguntando "a Dona Socorro conseguiria?".

| Personagem | Quem é | O que importa para ela |
|---|---|---|
| **Dona Socorro**, 62 | Compradora do Bloco 1, aposentada. Usa WhatsApp e pouco mais. A filha a ajuda com o celular. | Letra grande, poucos passos, não ter medo de "estragar" nada. |
| **Rafael**, 31 | Comprador do Bloco 4 com a esposa. Mexe bem no celular e quer saber da obra. | Notificação na hora, achar documento rápido. |
| **Carla**, 45 | Membro da Comissão (administradora do grupo de WhatsApp), apartamento no Bloco 2. | Publicar rápido do celular e saber se as pessoas leram. |
| **Erick** | Administrador do sistema, unidade 1101. | Resolver problema de acesso em um clique, ver a adesão. |

## 3. Fatias da E1

A E1 é entregue em três fatias. **Cada fatia é útil sozinha**: se o projeto parar depois da
primeira, ela já resolve alguma coisa.

| Fatia | Contém | O que já resolve |
|---|---|---|
| **1 · Acesso e avisos** | Épicos A, B e C | O canal oficial existe: aviso que não se perde no grupo, com notificação. |
| **2 · Documentos** | Épico D | Documento da obra num lugar fixo, com versão e acesso controlado. |
| **3 · Enquetes** | Épico E | Consulta com um voto por unidade, resultado auditável. |

---

## Épico A · Acesso da unidade

### H-01 · Primeiro acesso — RF-03, RF-04
**Como** comprador, **quero** entrar com o número do meu bloco e apartamento e a senha que o grupo
divulgou, **para** começar a usar o Portal sem esperar ninguém me aprovar.

- **Dado** a unidade 1101 nunca acessada, **quando** alguém entra com `1101` e `mudar123`, **então**
  vai direto para a tela "Primeiro acesso", e não para o mural.
- **Dado** a tela "Primeiro acesso", **então** ela pede: nova senha (duas vezes), nome de um
  responsável, celular e e-mail (marcado como **opcional**).
- **Quando** a nova senha tem menos de 8 caracteres ou é `mudar123`, **então** o sistema recusa e
  explica o motivo em linguagem simples.
- **Quando** o primeiro acesso é concluído, **então** a unidade passa a "ativada", com data e hora
  registradas, e a pessoa cai no mural.
- **Dado** o primeiro acesso não concluído (fechou o app no meio), **quando** entrar de novo com
  `mudar123`, **então** volta para a tela "Primeiro acesso".
- **Dado** a tela de entrada, **então** o bloco é escolhido em 5 botões (1 a 5) e o apartamento é
  um campo à parte, só com números e no máximo 3 dígitos (letra ou traço nem aparecem). A tela
  junta os dois: Bloco 1 + `101` vira o login `1101`; Bloco 1 + `7` ou `07` vira `1007`.
  (Mudança de 03/10/2026, sugestão de um vizinho no teste: o código colado `1101` era um enigma.)
- **Antes** de concluir, a tela mostra o aviso: *"Se você não é desta unidade, não continue. A
  conta é da família que mora ou vai morar aqui."*

### H-02 · Entrar no dia a dia — RF-03
**Como** comprador com a conta ativada, **quero** entrar com meu login e minha senha **para** ver
o que há de novo.

- **Dado** a unidade ativada, **quando** login e senha estão certos, **então** abre o mural.
- **Dado** um login que não existe ou uma senha errada, **então** a mensagem é a mesma nos dois
  casos: *"Bloco/apartamento ou senha incorretos"*. Não revela qual dos dois errou.
- A sessão continua aberta no celular até a pessoa sair, para a Dona Socorro não precisar digitar
  a senha toda vez.

### H-03 · Bloqueio por tentativas — RF-05
**Como** administrador, **quero** que ninguém consiga chutar senhas **para** que conta tomada seja
exceção, não rotina.

- **Dado** 5 tentativas erradas seguidas na unidade 1101, **quando** vier a 6ª, **então** o login
  dessa unidade fica bloqueado por 15 minutos, mesmo com a senha certa.
- A mensagem diz quanto tempo falta e sugere falar com a administração se não foi a pessoa.
- O bloqueio fica registrado no histórico (H-11).

### H-04 · Esqueci a senha — RF-04, RF-07
**Como** comprador, **quero** recuperar o acesso **para** não perder os avisos.

- **Dado** uma unidade com e-mail informado, **quando** a pessoa pede "esqueci a senha", **então**
  recebe por e-mail um link que vale por 1 hora e só pode ser usado uma vez.
- **Dado** uma unidade sem e-mail, **então** a tela diz: *"Fale com a administração do Portal no
  grupo do WhatsApp para resetar sua senha."*
- A tela **não revela** se a unidade tem e-mail cadastrado; a mensagem é sempre *"Se houver e-mail
  cadastrado, enviamos um link. Se não chegou, fale com a administração."*

### H-05 · Instalar no celular e receber notificações — RNF-01, RF-11
**Como** Rafael, **quero** o Portal como um aplicativo no celular **para** ser avisado na hora.

- Depois do primeiro acesso, o Portal oferece **uma vez** "Instalar na tela inicial" e "Ativar
  notificações", com explicação de uma linha para cada.
- Recusar não atrapalha nada: dá para ativar depois em "Minha unidade".
- **Dado** a conta aberta em dois celulares (do casal), **quando** sai um aviso, **então** os
  dois recebem a notificação.

### H-06 · Minha unidade — RF-08, RNF-12
**Como** comprador, **quero** ver e mudar os dados da minha unidade **para** mantê-los certos.

- A tela "Minha unidade" mostra bloco, apartamento, responsável, celular, e-mail e os aparelhos
  conectados.
- Dá para trocar a senha (pedindo a atual), editar responsável, celular e e-mail, e desconectar
  um aparelho.
- **Quando** a pessoa escolhe "Apagar meus dados", **então** o sistema pede confirmação, apaga
  responsável, celular e e-mail, desconecta todos os aparelhos e a unidade volta a "não ativada"
  com senha `mudar123`. Os votos já dados continuam valendo (são da unidade, não da pessoa).

---

## Épico B · Administração

### H-07 · Painel de ativação — RF-06, RF-07
**Como** Erick, **quero** ver quais unidades já entraram **para** medir a adesão e perceber conta
tomada.

- O painel lista as 320 unidades por bloco, com: ativada ou não, data do primeiro acesso,
  responsável e celular.
- No topo: total e percentual de unidades ativadas, geral e por bloco.
- Filtros: só ativadas, só não ativadas, só com papel de gestão.
- A Comissão também vê o painel e a ficha de cada unidade, com os contatos, **só para ler**:
  voltar para a senha inicial, dar ou tirar papéis e o histórico continuam do administrador
  (decisão de 06/10/2026, tabela de permissões em `02-requisitos.md`).

### H-08 · Resetar uma unidade — RF-07
**Como** Erick, **quero** devolver uma unidade ao estado inicial em um clique **para** resolver
quando alguém entrou na conta errada ou esqueceu a senha.

- **Quando** clico em "Resetar" na unidade 2304, **então** o sistema pede confirmação mostrando o
  que vai acontecer.
- **Confirmado**, **então**: senha volta a `mudar123`, contatos são apagados, todos os aparelhos
  são desconectados, o papel de gestão (se houver) é retirado e a unidade volta a "não ativada".
- Votos já dados **continuam valendo**.
- O reset fica registrado no histórico (H-11).

### H-09 · Dar e retirar o papel de Comissão — RF-09, RN-06
**Como** Erick, **quero** dar o papel de Comissão à conta da unidade de cada membro **para** que
eles publiquem sem ter um segundo login.

- Na unidade da Carla (Bloco 2), **quando** escolho "Dar papel: Comissão", **então** na próxima
  vez que ela abrir o Portal aparecem as opções de publicar aviso, documento e enquete.
- **Quando** retiro o papel, **então** essas opções somem imediatamente, mesmo com ela logada.
- O papel de **administrador** não pode ser retirado da última unidade que o tem (o Portal não
  pode ficar sem administrador).
- Dar ou tirar o papel pede confirmação dizendo o que acontece (ao dar: passa a publicar e a
  ver o celular e o e-mail de todas as unidades).
- Toda concessão e retirada fica no histórico (H-11).

### H-10 · Corrigir blocos e unidades — RF-01, RF-02
**Como** Erick, **quero** corrigir a lista de unidades **para** acompanhar a realidade se ela for
diferente do material de venda.

- Na primeira instalação, o sistema cria as 320 unidades automaticamente (5 blocos × térreo + 7
  andares × 8 posições: 001 a 008, 101 a 108, …, 701 a 708).
- O administrador pode adicionar um bloco, desativar uma unidade e renomear um bloco.
- Uma unidade com votos ou histórico **não é apagada**, só desativada.

### H-11 · Histórico de ações — RNF-14
**Como** Erick, **quero** ver quem fez o quê **para** investigar problema e dar transparência.

- Registra: primeiro acesso, bloqueio, reset, papel dado/retirado, aviso publicado/editado/
  arquivado, documento publicado/nova versão, enquete criada/encerrada.
- Cada registro tem data e hora, unidade que fez, ação e o item afetado.
- Só o administrador vê o histórico, e ninguém consegue apagá-lo.

---

## Épico C · Avisos

### H-12 · Publicar aviso — RF-10, RF-12
**Como** Carla, **quero** publicar um aviso oficial pelo celular **para** que todos saibam pelo
canal certo.

- O formulário pede título, texto, anexos (imagens ou PDF, até 10 MB cada) e destino: **todos** ou
  **blocos escolhidos**.
- Há opção "Fixar no topo".
- Antes de publicar, uma prévia mostra como o aviso vai aparecer e quantas unidades vão recebê-lo.
- O aviso mostra "Publicado pela Comissão" e a data.

### H-13 · Ser avisado — RF-11
**Como** Dona Socorro, **quero** ser avisada quando sair algo novo **para** não depender do grupo.

- **Dado** um aviso para o Bloco 1, **quando** é publicado, **então** os aparelhos conectados das
  unidades do Bloco 1 recebem notificação com o título, e as unidades com e-mail recebem o aviso
  por e-mail.
- Unidades de outros blocos **não** recebem.
- Tocar na notificação abre o aviso.

### H-14 · Mural — RF-12, RF-13
**Como** Dona Socorro, **quero** ver os avisos num lugar só **para** achar o que importa.

- Fixados primeiro; depois do mais novo para o mais antigo.
- Aviso ainda não lido pela unidade aparece destacado.
- Campo de busca procura no título e no texto.
- Só aparecem os avisos cujo destino inclui o bloco da unidade.

### H-15 · Corrigir ou arquivar aviso — RF-14, RN-05
**Como** Carla, **quero** corrigir um aviso com erro **sem** que ele suma **para** manter o
registro oficial.

- Editar um aviso mostra para todos "Editado em <data>", com link para ver a versão anterior.
- Arquivar tira o aviso do mural, mas ele continua acessível em "Avisos arquivados".
- **Não existe** botão de apagar.

### H-16 · Saber quem leu — RF-15
**Como** Carla, **quero** saber quantas unidades leram **para** decidir se repito no grupo.

- No aviso, quem tem papel de gestão vê "Lido por X de Y unidades" e a lista das que não leram.
- Uma unidade conta como "leu" quando abre o aviso.

---

## Épico D · Documentos

### H-17 · Publicar documento — RF-30, RF-31, RF-33
**Como** Carla, **quero** publicar um documento da obra **para** que fique num lugar fixo.

- O formulário pede título, categoria (convenção, regimento, atas, contratos, obra, outros),
  data, arquivo (PDF ou imagem, até 20 MB) e nível de acesso: **público**, **compradores** ou
  **gestão**.
- Opção "Avisar as unidades" cria um aviso automático com link para o documento.

### H-18 · Consultar documentos — RF-31
**Como** Rafael, **quero** achar um documento rápido **para** tirar uma dúvida sem perguntar no grupo.

- Lista por categoria, com busca pelo título.
- O documento abre no próprio celular, com opção de baixar.
- Unidade comum não vê documentos de nível **gestão**: eles nem aparecem na lista.
- Documentos **públicos** aparecem até para quem não entrou no Portal, na tela de login.

### H-19 · Nova versão de documento — RF-32
**Como** Carla, **quero** subir a versão nova de um documento **sem** perder a antiga **para**
manter o histórico.

- "Enviar nova versão" substitui o arquivo principal, e as anteriores ficam em "Versões
  anteriores", com data.

---

## Épico E · Enquetes

### H-20 · Criar enquete — RF-20, RF-23, RN-03
**Como** Carla, **quero** consultar os compradores **para** decidir com base na opinião de todos.

- O formulário pede pergunta, opções (2 a 10), escolha única ou múltipla, data e hora de
  encerramento, destino (todos ou blocos) e se o resultado aparece **durante** ou **só no fim**.
- Toda enquete mostra a frase: *"Consulta sem valor legal."*
- Publicar a enquete gera aviso automático (H-13).
- Depois que o primeiro voto chega, pergunta e opções **não podem** mais ser editadas.

### H-21 · Votar — RF-21, RF-22, RN-01, RN-02
**Como** Rafael, **quero** votar pela minha unidade **para** participar da decisão.

- **Dado** a unidade 4203 no destino da enquete, **quando** vota, **então** o voto vale para a
  unidade inteira.
- **Dado** que a esposa do Rafael, no outro celular, já votou pela 4203, **então** o Rafael vê o
  voto da unidade e pode **trocá-lo** até o encerramento. Vale sempre o último.
- **Dado** a enquete encerrada, **então** não dá mais para votar nem trocar.
- Unidade fora do destino não vê a enquete.

### H-22 · Ver resultado — RF-24, RF-25
**Como** comprador, **quero** ver o resultado **para** saber o que foi decidido.

- Mostra votos por opção, número de unidades que votaram e participação (% das unidades do destino).
- Se o resultado é "só no fim", antes do encerramento aparece apenas a participação.
- A gestão vê também **quais unidades votaram** (não em quê), para cobrar participação.
- Enquete encerrada fica guardada com o resultado e não pode ser alterada nem apagada.

---

## 4. Rastreabilidade

| Requisito | Histórias |
|---|---|
| RF-01, RF-02 | H-10 |
| RF-03 | H-01, H-02 |
| RF-04 | H-01, H-04 |
| RF-05 | H-03 |
| RF-06 | H-07 |
| RF-07 | H-04, H-07, H-08 |
| RF-08 | H-06 |
| RF-09 | H-09 |
| RF-10, RF-12 | H-12, H-14 |
| RF-11 | H-05, H-13 |
| RF-13 | H-14 |
| RF-14 | H-15 |
| RF-15 | H-16 |
| RF-20 a RF-25 | H-20, H-21, H-22 |
| RF-30 a RF-33 | H-17, H-18, H-19 |
| RNF-14 | H-11 |

Todos os requisitos da E1 têm pelo menos uma história.
