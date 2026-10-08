# Spec · M2 Onda 1 · Contrato

| | |
|---|---|
| **Marco** | M2 · Notificações (`docs/07-roadmap.md`, seção do M2) |
| **Base** | `03-historias.md` (H-04, H-05, H-13), `04-modelo-de-dados.md` (`inscricao_push`, `token_recuperacao`), `05-arquitetura.md` (seções 5 e 6.2), ADR-0002, ADR-0005, ADR-0006, ADR-0008, protótipo (telas `#instalar` e `#esqueci`) |
| **Criado em** | 06/10/2026 |
| **Plano** | `docs/superpowers/plans/m2-contrato.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m2.md` |
| **Decisão nova** | [ADR-0010](../../adr/0010-envio-em-segundo-plano.md) (envio depois da resposta) |

## 1. Objetivo

Deixar a base do M2 pronta para que **dois agentes trabalhem em paralelo**, sem tocar nos
mesmos arquivos nem criar migrações conflitantes:

| Épico | Histórias | Entrega |
|---|---|---|
| **A · Push e PWA** | H-05 instalar e ativar, H-13 (push) | manifest, service worker, oferta única "Instalar" / "Ativar notificações" depois do primeiro acesso, passo a passo do iPhone, ativar e desativar em Minha unidade, inscrição por aparelho, envio Web Push ao publicar, inscrição expirada removida, toque abre o aviso |
| **B · E-mail** | H-04 esqueci a senha, H-13 (e-mail) | SMTP do Gmail, "esqueci a senha" (link de 1 hora, uso único, tela que não revela se há e-mail), cópia do aviso por e-mail para as unidades do destino que têm e-mail |

Esta onda **não implementa as histórias** e **não muda nada que o morador vê** (a versão do
`web/package.json` e o `novidades.ts` ficam como estão). Entrega: a migração 0005, o contrato da
API (este documento + esquemas Pydantic + tipos TypeScript + rotas que respondem 501), a peça
comum "notificar a publicação" com a decisão de como o envio roda sem atrasar a publicação, a
configuração por variável de ambiente e os pontos de encaixe no front.

## 2. Banco · migração 0005

Mesmo padrão da 0002 a 0004: SQL escrito à mão, roda como `dono`, permissões ao papel `app`
(nome trocável por `-x papel_app=`), funções de trigger com `set search_path = pg_catalog,
public, pg_temp` e nomes qualificados, `upgrade → downgrade → upgrade` testado (e o downgrade
não deixa função para trás). Arquivo: `api/migracoes/versions/0005_notificacoes_e_recuperacao.py`;
modelos em `api/app/modelos/notificacoes.py`.

### 2.1 `inscricao_push` (H-05)

| Coluna | Regra |
|---|---|
| `sessao_id` | PK e FK `sessao` (`on delete cascade`): **uma por aparelho**, como no modelo de dados |
| `endpoint` | único; `https://`, até 2.048 caracteres |
| `chave_p256dh` | base64url de 65 bytes (`^[A-Za-z0-9_-]{87}=?$`) |
| `chave_auth` | base64url de 16 bytes (`^[A-Za-z0-9_-]{22}(==)?$`) |
| `criada_em` | carimbada pelo banco |

- **Some com a sessão:** trigger em `sessao` apaga a inscrição quando `encerrada_em` é
  preenchido (sair, desconectar, trocar a senha, reset, apagar dados). Inscrever numa sessão
  encerrada falha (`inscricao_push_sessao_encerrada`). O trigger lê a sessão com `for share`:
  encerrar e inscrever ao mesmo tempo nunca deixam inscrição viva numa sessão encerrada
  (revisão do contrato, achado 4; testado nas duas ordens).
- **No máximo 10 por unidade** (`inscricao_push_limite`), contando só as sessões **que ainda
  valem** pela regra de `buscar_sessao` (não encerradas, usadas nos últimos 180 dias, abertas
  depois da última troca de senha): são as que o morador vê em Minha unidade e consegue
  desconectar para liberar a vaga (achado 5). O trigger trava a unidade (`for no key update`):
  duas inscrições ao mesmo tempo contam uma com a outra. Dez cobre a família toda; mais que
  isso é sinal de abuso (cada inscrição é um POST que a função faz a cada aviso).
- Sessão que venceu por 180 dias sem uso, ou aberta antes da última troca de senha, não é
  apagada, mas **não recebe** (`destinos_push` aplica as mesmas regras de `buscar_sessao`).

### 2.2 `token_recuperacao` (H-04)

| Coluna | Regra |
|---|---|
| `id` | PK |
| `unidade_id` | FK `unidade` |
| `token_hash` | único; SHA-256 em hexadecimal (o token só existe no link do e-mail) |
| `criado_em` | carimbado pelo banco |
| `expira_em` | **calculado pelo banco**: criação + 1 hora (o valor da aplicação é ignorado) |
| `usado_em` | nulo = não usado; carimbado pelo banco ao usar |

- Só nasce para unidade **ativa, ativada e com e-mail** (`token_recuperacao_sem_email`).
- **Até 3 por unidade por hora** (`token_recuperacao_limite_hora`) e **6 por dia**
  (`token_recuperacao_limite_dia`), contra encher a caixa de alguém e gastar a cota do Gmail.
  O trigger trava a unidade, então pedidos simultâneos contam uns com os outros.
- **Uso único:** usado não volta a nulo nem é usado de novo (`token_recuperacao_usado`).
- **Vencido** (`token_recuperacao_vencido`): passou da hora **ou a senha da unidade mudou
  depois do pedido** (`criado_em < unidade.senha_trocada_em`). Assim, usar um link mata os
  outros links abertos da unidade, e reset ou "apagar meus dados" também. Consequência para o
  épico B: **marcar o token como usado antes de gravar a senha nova**, na mesma transação.

### 2.3 `notificacao_envio` (H-13)

Um registro por aviso e canal: é o que impede mandar duas vezes e o que mede a entrega. **Só
contagens**, nunca endereço, e-mail ou unidade (nada de dado pessoal num registro que nunca é
apagado).

| Coluna | Regra |
|---|---|
| `aviso_id`, `canal` | únicos juntos (`notificacao_envio_unico`); `canal` em `push`, `email` |
| `situacao` | nasce `pendente`; `pendente → enviando / desligado / interrompido`; `enviando → concluido / interrompido`; o resto é final (`notificacao_envio_situacao`) |
| `criado_em`, `iniciado_em`, `concluido_em` | carimbadas pelo banco nas mudanças de situação |
| `destinos`, `entregues`, `falhas`, `removidas`, `pulados`, `reservados` | `>= 0`; `entregues + falhas + pulados <= destinos`; `removidas <= falhas`; no e-mail, `entregues + falhas <= reservados` (`notificacao_envio_reserva`) |

`destinos`: aparelhos (push) ou unidades (e-mail). `entregues`: aceitos pelo serviço de push
(201) ou pelo Gmail; não quer dizer "lido". `removidas`: inscrições que o serviço de push disse
não existir mais (404/410), apagadas. `pulados`: o que não coube na cota do dia ou no prazo da
função. `reservados`: e-mails separados da cota do Gmail **antes** de mandar (seção 5); o banco
não aceita e-mail tentado além da reserva.

### 2.4 Permissões do `app`

| Tabela | SELECT | INSERT | UPDATE | DELETE |
|---|---|---|---|---|
| `inscricao_push` | sim | sim | só `sessao_id`, `chave_p256dh`, `chave_auth` | sim |
| `token_recuperacao` | sim | sim | só `usado_em` | sim (faxina de tokens velhos) |
| `notificacao_envio` | sim | sim | só `situacao` e as contagens (inclusive `reservados`) | **não** |

## 3. Peças comuns da API (prontas e testadas nesta onda)

| Peça | Arquivo | O quê |
|---|---|---|
| Configuração | `app/configuracao.py` | `config_push() -> ConfigPush \| None`, `config_email() -> ConfigEmail \| None`, `url_base()`. Seção 6 |
| Gerar chaves | `app/comandos/gerar_chaves_vapid.py` | `uv run python -m app.comandos.gerar_chaves_vapid` imprime um par novo (nada fica no repositório) |
| Segundo plano | `app/servicos/segundo_plano.py` | `agendar(tarefas, funcao, *args)`: `wait_until` na Vercel, `BackgroundTasks` fora. Seção 5 |
| Notificar | `app/servicos/notificacoes.py` | interface `Enviador`, `Resultado` (com `reservar`, `salvar`, `tempo_esgotado`), `registrar_publicacao`, `agendar`, `processar`, `destinos_push`, `destinos_email`, cota do Gmail (`reservar_cota_email`, `reservar_email_recuperacao`). Seção 5 |
| Envios | `app/rotas/envios.py` | `GET /api/avisos/{id}/envios` (seção 4.4) |
| Histórico | `app/servicos/historico.py` | ações `recuperacao_pedida` e `senha_redefinida` (seção 4.3), `registrado_recentemente(db, acao, entidade=, entidade_id=, janela=)`, e as frases em `web/src/administracao/frases.ts` |
| Pedido de recuperação | `app/rotas/recuperacao.py` (`pedir`) | já pronto: valida o formato, agenda `processar_pedido` e responde 202. Seção 4.3 |
| 501 | `app/erros_api.py` | `em_construcao()`: 501 `em_construcao`, "Esta parte do Portal ainda está sendo feita." |

A publicação já está ligada: `app/servicos/avisos.publicar` chama `registrar_publicacao` antes
do commit, e a rota `POST /api/avisos` chama `notificacoes.agendar`. Com os enviadores ainda
desligados, os dois envios de cada aviso novo ficam `desligado`.

## 4. Contrato da API

Convenções do M1 (spec do M1, seção 4): JSON em `snake_case`, datas ISO 8601 em UTC, erros
`{ "codigo", "mensagem" }`, toda alteração exige `X-Portal: 1`. Esquemas Pydantic e espelhos
TypeScript conferidos pelo `api/testes/test_contrato.py`:

| Python | TypeScript | Dono |
|---|---|---|
| `app/esquemas/push.py` | `web/src/notificacoes/tipos.ts` | épico A |
| `app/esquemas/recuperacao.py` | `web/src/recuperacao/tipos.ts` | épico B |
| `app/esquemas/comum.py` (`EnvioDoAviso`, `EnviosDoAviso`, `Canal`, `SituacaoEnvio`) | `web/src/api/tipos.ts` | comum |

Nesta onda as rotas dos épicos respondem **501 `em_construcao`** (menos o pedido de
recuperação, já pronto), mas sessão, permissão, CSRF e validação do corpo já são os de verdade.
O que vale antes e depois dos épicos está em `api/testes/test_m2_rotas.py` (a lista de serviços
de push testada direto no validador; a rota pública testada como "não recusa por falta de
sessão"). Os testes de 501 ficam à parte, em `api/testes/test_m2_em_construcao.py`: o épico
troca o corpo da função e apaga a própria seção de lá.

### 4.1 Funções de API no front

`web/src/notificacoes/api.ts`: `lerEstadoDasNotificacoes()`, `inscreverEsteAparelho(dados)`,
`removerEsteAparelho()`. `web/src/recuperacao/api.ts`: `pedirRecuperacao(login)`,
`conferirLink(token)`, `redefinirSenha(dados)`. O token vai sempre **no corpo**, nunca na URL.

### 4.2 Épico A · Push (`app/rotas/push.py`)

| Rota | Quem | Corpo | Resposta | Erros |
|---|---|---|---|---|
| `GET /api/notificacoes` | `unidade_logada` | — | 200 `EstadoNotificacoes` | 401, 403 |
| `PUT /api/notificacoes/este-aparelho` | `unidade_logada` | `InscricaoPush` | 204 | 503 `notificacoes_desligadas`, 409 `limite_de_aparelhos`, 422 |
| `DELETE /api/notificacoes/este-aparelho` | `unidade_logada` | — | 204 (idempotente) | 401, 403 |

- `EstadoNotificacoes`: `disponivel` (o servidor tem VAPID; falso esconde a oferta),
  `chave_publica` (o `applicationServerKey`, ou nulo), `este_aparelho` (a sessão deste aparelho
  tem inscrição).
- `InscricaoPush`: `endpoint`, `p256dh`, `auth` (o `PushSubscription.toJSON()` achatado).
  **O endpoint só vale se for de um serviço de push conhecido** (`fcm.googleapis.com`,
  `*.push.services.mozilla.com`, `*.push.apple.com`, `*.notify.windows.com`), em `https`, sem
  porta nem usuário: a função faz um POST para esse endereço a cada aviso, e sem a lista uma
  conta qualquer faria a Vercel chamar endereços escolhidos por ela (SSRF). Mensagens:
  "Este navegador mandou um endereço de notificação que o Portal não reconhece." e "Este
  navegador mandou uma chave de notificação fora do padrão.".
- Inscrever: a inscrição é **da sessão deste aparelho**. Se o mesmo endpoint já estiver em
  outra sessão (o navegador entrou de novo, ou outra unidade usou este navegador), ele passa
  para esta. Se esta sessão já tinha outro endpoint, troca. 10 aparelhos inscritos: 409
  "Este apartamento já tem 10 aparelhos com notificação. Desative em algum deles." (restrição
  `inscricao_push_limite`). Sem VAPID: 503 "As notificações ainda não estão ligadas no Portal.".
- Desativar em outro aparelho = desconectar o aparelho em Minha unidade (já existe;
  a inscrição some junto). `Aparelho` (Minha unidade) ganhou `notificacoes: bool`, já
  preenchido nesta onda.
- `PushAviso` (corpo da notificação, JSON cifrado pelo Web Push, lido pelo service worker):
  `aviso_id`, `titulo`, `categoria`, `url` (`/avisos/<id>`). Cabe com folga nos 4 KB do padrão.
- Envio (`app/servicos/push.py`, `ENVIADOR`): para `destinos_push(db, aviso)`, em paralelo
  (`ThreadPoolExecutor`, `pywebpush.webpush` com VAPID de `config_push()`, tempo limite de
  10 s), TTL de 3 dias, `Urgency: high` na categoria `urgente` (`normal` nas outras), `Topic:
  aviso-<id>`. 404 ou 410: apaga a inscrição (`removidas`, que também conta em `falhas`). Outro
  erro: `falhas`, e segue. **A sessão do banco não é segura entre threads:** as threads só
  mandam; apagar as inscrições mortas e contar é na thread principal, com
  `resultado.salvar()` a cada `SALVAR_A_CADA` e parada em `resultado.tempo_esgotado()` (o resto
  é `pulados`). O push não usa `reservar`.
- Service worker (`web/public/sw.js`): `push` mostra a notificação com `titulo` (ícone
  `/icon-192.png`, `tag` `aviso-<id>`, `data.url`); `notificationclick` foca uma janela do
  Portal já aberta e navega para `url`, ou abre uma nova, **só para caminhos do próprio Portal
  que começam com `/avisos/`**; sem cache de páginas (o Portal muda de versão com frequência e
  cache velho confundiria). Manifest (`web/public/manifest.webmanifest`): nome "Portal
  Capibaribe Prime", `start_url` `/avisos`, `display: standalone`, `theme_color` `#1f5e3b`,
  ícones 192 e 512 (já existem em `web/public/`).
- Tela (H-05, protótipo `#instalar`): depois do primeiro acesso, **uma vez por aparelho**,
  "Receber os avisos" com "Instalar" e "Ativar notificações"; passo a passo para Android e
  iPhone; "No iPhone, as notificações só chegam se o Portal for aberto pelo ícone." Pedir
  permissão **só depois de um toque** (exigência do iPhone). Recusar não atrapalha nada; o
  mesmo fica em Minha unidade.

### 4.3 Épico B · Esqueci a senha (`app/rotas/recuperacao.py`)

**Sem sessão** (quem esqueceu a senha não entrou), mas **com `X-Portal: 1`**: sem ele, outro
site faria o navegador do morador pedir links (encher a caixa dele, gastar a cota do Gmail) ou
mandar um formulário de troca de senha.

| Rota | Corpo | Resposta | Erros |
|---|---|---|---|
| `POST /api/acesso/recuperacao` | `PedirRecuperacao` | 202 `RecuperacaoPedida` | 403 `requisicao_recusada`, 422 |
| `POST /api/acesso/recuperacao/conferir` | `LinkDeRecuperacao` | 200 `LinkValido` | 410 `link_invalido`, 422 |
| `POST /api/acesso/recuperacao/redefinir` | `RedefinirSenha` | 200 `Eu` + cookie novo | 410 `link_invalido`, 422 |

- `PedirRecuperacao`: `login` (mesma regra e mensagem do `Entrar`; `validar_login` saiu de
  `app/esquemas/acesso.py` para ser usado aqui).
- **A resposta é sempre a mesma** para qualquer login válido (H-04): 202 com `mensagem` "Se
  houver e-mail cadastrado, enviamos um link. Se não chegou, fale com a administração."
  (`MSG_PEDIDO`). Login que não existe, unidade sem e-mail, limite estourado, cota do dia
  esgotada ou e-mail desligado: mesma resposta.
- **O pedido inteiro roda depois da resposta** (revisão do contrato, achado 3; já pronto nesta
  onda): a rota `pedir` **não abre o banco**, só valida o formato do login, agenda
  `app.servicos.recuperacao.processar_pedido(login)` (`segundo_plano.agendar`) e responde. Se a
  consulta da unidade, a cota, o token e o histórico ficassem na requisição, o tempo de resposta
  revelaria quem tem e-mail. O teste `test_pedido_responde_igual_e_deixa_tudo_para_depois`
  quebra o banco na requisição: o épico B não pode pôr `Banco` em `pedir`.
- `processar_pedido` (épico B, em `app/servicos/recuperacao.py`, abre a própria sessão):
  1. unidade ativa, ativada e com e-mail pelo login (senão `motivo = "sem_email"`);
  2. `config_email()` ligada (senão `"desligado"`);
  3. `reservar_email_recuperacao(db)`: pega a trava da cota na transação e diz se cabe
     (senão `"cota"`);
  4. INSERT do token (`secrets.token_urlsafe(32)`, o banco guarda `sha256`); as restrições de
     3/hora e 6/dia viram `"limite"`;
  5. histórico `recuperacao_pedida`, ação do sistema (`unidade_id` nulo, entidade `unidade`),
     `{"enviado": bool, "motivo": null | "sem_email" | "limite" | "cota" | "desligado"}`, **só
     para unidade que existe e no máximo uma vez por unidade por hora**
     (`historico.registrado_recentemente(..., janela=1 hora)`): um script contra os 320 logins
     não enche o banco (Neon Free);
  6. commit (solta a trava da cota) e só então o e-mail.
  O token em texto só existe na memória até o e-mail sair; **nunca** em log, histórico ou banco.
  Nada levanta para fora; erro vira log sem dado pessoal.
- Link do e-mail: `config_email().url_base + "/redefinir-senha#token=<token>"`. O token vai
  **depois do `#`**: o navegador não o manda para o servidor, então ele não fica em log de
  acesso nem em `Referer`. A tela lê o `#`, apaga-o da barra (`history.replaceState`) e chama
  `conferir`. **O endereço nunca vem do cabeçalho `Host`** (quem pede escolheria para onde o
  link aponta).
- E-mail de recuperação: assunto "Portal Capibaribe Prime: criar senha nova"; texto puro, com
  "Bloco N, apartamento NNN", o link, "vale por 1 hora e só uma vez" e "Se não foi você, apague
  este e-mail; sua senha continua a mesma.".
- `conferir` (não gasta o link): token desconhecido, usado, vencido ou de senha já trocada → 410
  `link_invalido` "Este link venceu ou já foi usado. Peça outro em \"Esqueci minha senha\".";
  válido → `LinkValido` (`unidade: UnidadeRef`, para a tela mostrar a placa).
- `redefinir`: trava o token (`for update`), confere como acima, **marca `usado_em` primeiro**,
  depois `trocar_senha_e_sessao` (desconecta todos os aparelhos, a inscrição de push vai junto,
  e abre uma sessão nova para quem redefiniu), `tentativas.esquecer_login(login)`, histórico
  `senha_redefinida`, commit e `gravar_cookie`. Responde `Eu`: a pessoa já entra. Senha: mesmas
  regras e mensagens do primeiro acesso (`SenhaNova`, `SenhaRepetida`).
- Cópia do aviso (`app/servicos/email.py`, `ENVIADOR`): para `destinos_email(db, aviso)`,
  **uma mensagem por unidade** (nunca vários endereços no mesmo e-mail). **Antes de mandar**,
  `n = resultado.reservar(len(destinos))` (a reserva da cota, seção 5); só os `n` primeiros
  são tentados, o resto é `pulados`. Uma conexão SMTP por envio, com tempo limite;
  `resultado.salvar()` a cada `SALVAR_A_CADA`; em `resultado.tempo_esgotado()`, para e conta o
  resto como `pulados`; recusa de um destinatário conta como falha e segue; queda da conexão
  interrompe o canal.
  Assunto "Aviso do Portal: <título>"; texto puro com o texto do aviso, o link
  `url_base + aviso.caminho` e o rodapé "Você recebe porque cadastrou este e-mail no Portal
  Capibaribe Prime. Para não receber mais, desmarque “Receber os avisos por e-mail” em Minha
  unidade." (ajustes do M2, 1.3.0; até a 1.2.0 mandava apagar o e-mail). Remetente
  "Portal Capibaribe Prime <conta do Portal>".
- Telas (protótipo `#esqueci`): "Esqueci minha senha" (`/esqueci-a-senha`, só sem sessão):
  bloco e apartamento, "Mandar link", e a caixa com a mensagem de H-04 mais "Sem e-mail
  cadastrado, fale com a administração do Portal no grupo do WhatsApp. Ela volta sua senha para
  a inicial.". "Criar senha nova" (`/redefinir-senha`, pública): placa da unidade, senha nova e
  repetida; ao terminar, mural com o recado "Senha nova criada. Os outros aparelhos foram
  desconectados.".

### 4.4 Comum · Como foi a notificação (`app/rotas/envios.py`)

| Rota | Quem | Resposta | Erros |
|---|---|---|---|
| `GET /api/avisos/{id}/envios` | `exige_gestao` | 200 `EnviosDoAviso` | 404 `aviso_nao_encontrado`, 401, 403 |

`EnviosDoAviso`: `itens: EnvioDoAviso[]`, na ordem push, e-mail; vazio para aviso publicado
antes do M2. `EnvioDoAviso`: `canal`, `situacao`, `destinos`, `entregues`, `falhas`,
`removidas`, `pulados`, `criado_em`, `concluido_em`. Nenhuma tela usa ainda (dúvida 9); serve
para conferir o portão do M2 e para uma tela futura ("chegou a N aparelhos").

### 4.5 Ajustes do M2 · "Receber os avisos por e-mail" (`app/rotas/acesso.py`, 1.3.0)

| Rota | Quem | Corpo | Resposta | Erros |
|---|---|---|---|---|
| `PUT /api/minha-unidade/avisos-por-email` | `UnidadeLogada` + `X-Portal: 1` | `AvisosPorEmail` `{ "receber": bool }` (booleano estrito) | 200 `MinhaUnidade` | 422, 401, 403 |

`MinhaUnidade` (GET e respostas de Minha unidade) ganhou `receber_avisos_email: bool`. Desligar
não apaga o e-mail; "Apagar meus dados" volta a opção para ligada. Plano:
`docs/superpowers/plans/m2-ajustes.md`.

## 5. Notificar a publicação, sem atrasar a publicação

Decisão completa e alternativas: [ADR-0010](../../adr/0010-envio-em-segundo-plano.md). Resumo:

1. **Caixa de saída:** `registrar_publicacao(db, aviso_id)` grava `pendente` por canal na
   transação da publicação.
2. **Depois da resposta:** `notificacoes.agendar(tarefas, aviso_id)` →
   `segundo_plano.agendar`: na Vercel, `vercel.functions.wait_until(asyncio.to_thread(...))`
   (SDK oficial; o runtime Python drena isso **depois de enviar a resposta**, dentro da duração
   máxima da função, 300 s no Hobby com Fluid compute); fora da Vercel, `BackgroundTasks`. O
   `BackgroundTasks` sozinho não é contrato documentado da Vercel (ADR-0010).
3. **`processar(aviso_id)`:** faxina (`enviando` há mais de 10 min e `pendente` há mais de
   24 h viram `interrompido`); depois, para este aviso e para os `pendente` que sobraram de
   outros, reivindica cada canal com `UPDATE … where situacao = 'pendente'` (**só um processo
   ganha: no máximo uma vez**). **Os canais de um aviso rodam em paralelo** (uma thread e uma
   sessão de banco por canal): o e-mail, lento, não atrasa o push, e o push não come o tempo do
   e-mail. **Prazo comum** `TEMPO_MAXIMO = 240 s` (a função tem 300 s; sobra para gravar o fim):
   o enviador para em `resultado.tempo_esgotado()` e conta o resto como `pulados` (que aparecem
   em `/envios`). Aviso arquivado antes do envio: `interrompido`. Canal desligado: `desligado`.
   Exceção no enviador: `interrompido`, com as contagens até ali, e no log só o tipo do erro
   (`RuntimeError`, `SMTPServerDisconnected`…), nunca a mensagem (a de um erro de SMTP pode
   trazer o e-mail de alguém).
4. **Quem recebe** (regra comum, `destinos_push` e `destinos_email`): unidades **ativas** do
   destino (todos, ou os blocos de `aviso_bloco`), **inclusive a unidade que publicou** e os
   outros aparelhos dela (ajustes do M2, 1.3.0: resposta do Erick à dúvida 4; até a 1.2.0 ela
   ficava de fora). Push: só sessões que valem (não encerradas, usadas nos
   últimos 180 dias, abertas depois da última troca de senha) de unidades com o primeiro acesso
   feito; os dois celulares do casal são duas sessões e os dois recebem (H-05). E-mail: unidades
   já ativadas com e-mail e com "Receber os avisos por e-mail" ligada (coluna
   `unidade.receber_avisos_email`, migração 0006), uma vez cada. A recuperação de senha não
   olha essa opção.
5. **Cota do Gmail** (~500 destinatários por dia na conta grátis): `LIMITE_EMAILS_24H = 450`
   numa janela móvel de 24 h; `RESERVA_RECUPERACAO = 50` fica só para o "esqueci a senha"
   (`cota_email_avisos` e `cota_email_recuperacao`). Hoje são ~320 unidades no máximo: um aviso
   para todos cabe; o segundo no mesmo dia pode ter `pulados` (dúvida 5). **A cota é
   reservada antes de mandar** (revisão do contrato, achado 2):
   - `resultado.reservar(n)` → `reservar_cota_email`: numa transação própria, com a trava
     `pg_advisory_xact_lock(TRAVA_COTA_EMAIL)`, separa `min(n, cota livre)` e grava em
     `notificacao_envio.reservados` **na hora**. A cota mede as reservas (não o que já saiu):
     uma função que morre no meio de 320 e-mails continua contando os 320, e dois avisos
     próximos não leem a mesma sobra.
   - O banco recusa e-mail tentado além da reserva (`notificacao_envio_reserva`).
   - Envio que termina devolve a sobra (`reservados` cai para `entregues + falhas`);
     envio interrompido fica com a reserva inteira (não se sabe quantos saíram).
   - O "esqueci a senha" pega a mesma trava (`reservar_email_recuperacao(db)`) na transação em
     que cria o token; o token conta na cota.
   - `resultado.salvar()` grava as contagens aos poucos (transação própria), para `/envios`
     mostrar o progresso e nada sumir se a função morrer.

Interface que cada épico implementa no próprio arquivo (`app/servicos/push.py` e
`app/servicos/email.py`, um `ENVIADOR` em cada):

```python
class Enviador(Protocol):
    canal: Canal
    def ligado(self) -> bool: ...          # config_push() / config_email() is not None
    def enviar(self, db: Session, aviso: AvisoParaNotificar, resultado: Resultado) -> None: ...
```

`AvisoParaNotificar`: `aviso_id`, `titulo`, `texto`, `categoria` (da versão em vigor),
`publicado_por`, `para_todos`, `blocos` (números) e a propriedade `caminho` (`/avisos/<id>`).
`Resultado`: as contagens (`destinos`, `entregues`, `falhas`, `removidas`, `pulados`,
`reservados`), atualizadas pelo enviador enquanto trabalha, e os métodos `reservar(n) -> int`
(só o e-mail; chamar **antes** de mandar), `salvar()` (a cada `SALVAR_A_CADA = 25` destinos) e
`tempo_esgotado()`. `enviar` **não faz commit em `db`** (a reserva e o progresso vão por
`resultado`, cada um na própria transação; o resto, como apagar inscrição morta, é commitado
por quem chama no fim). Roda numa thread própria. Testar com SMTP falso (`smtplib.SMTP_SSL` trocado por um objeto que
guarda as mensagens) e push falso (`pywebpush.webpush` trocado): **nenhum teste fala com o Gmail
ou com um serviço de push de verdade**.

## 6. Configuração (variáveis de ambiente)

| Variável | Para quê | Sem ela |
|---|---|---|
| `PORTAL_VAPID_PRIVADA` | chave privada VAPID, 32 bytes em base64url (`python -m app.comandos.gerar_chaves_vapid`) | push desligado |
| `PORTAL_VAPID_CONTATO` | `mailto:<conta do Portal>` (ou `https://`), exigido pelos serviços de push | push desligado |
| `PORTAL_SMTP_USUARIO` | a conta Gmail do Portal | e-mail desligado |
| `PORTAL_SMTP_SENHA_APP` | a senha de app dessa conta | e-mail desligado |
| `PORTAL_SMTP_HOST`, `PORTAL_SMTP_PORTA` | opcionais: `smtp.gmail.com`, 465 (TLS direto) | padrão |
| `PORTAL_URL_BASE` | endereço dos links do e-mail (`https://…`, ou `http://localhost`/`127.0.0.1` em desenvolvimento), sem caminho | e-mail desligado |

- **Sem configuração, nada quebra:** canal ausente, pela metade ou com valor inválido fica
  desligado, com um aviso no log que nunca mostra o valor. O M2 pode ir ao ar antes de a conta
  do Gmail existir; publicar continua igual ao M1 (envios `desligado`).
- **A chave pública não é variável:** sai da privada (`config_push().chave_publica`), então as
  duas nunca ficam trocadas. Trocar o par depois obriga todo aparelho a ativar de novo.
- Segredos com `field(repr=False)`; nenhuma chave real no repositório (o `gitleaks` confere).
  Prévia e produção usam pares VAPID diferentes; a prévia fica sem SMTP (não manda e-mail para
  ninguém de verdade).
- Exemplo comentado em `api/.env.example`.

## 7. Front

| Pasta / arquivo | Dono | Nesta onda |
|---|---|---|
| `web/src/notificacoes/` (`tipos.ts`, `api.ts`, `rotas.tsx`, `ganchos.ts`, `SecaoNotificacoes.tsx`) | épico A | tipos, funções de API, `rotasNotificacoes = []`, encaixes que não fazem nada |
| `web/src/recuperacao/` (`tipos.ts`, `api.ts`, `rotas.tsx`, `LinkEsqueci.tsx`) | épico B | tipos, funções de API, `rotasRecuperacao = []`, `LinkEsqueci` com o mesmo texto do M1 |
| `web/public/sw.js`, `web/public/manifest.webmanifest` e a linha `<link rel="manifest">` do `web/index.html` | épico A | não existem ainda |

Pontos de encaixe já ligados nas telas comuns e do M1 (o épico troca só o corpo, do lado dele):

| Onde | Chama | Épico |
|---|---|---|
| `web/src/main.tsx` | `registrarServiceWorker()` de `notificacoes/ganchos.ts` (hoje não faz nada) | A |
| `web/src/acesso/PrimeiroAcesso.tsx` | `destinoDepoisDoPrimeiroAcesso()` (hoje `/avisos`; o épico A devolve a tela "Receber os avisos", uma vez por aparelho) | A |
| `web/src/acesso/MinhaUnidade.tsx` | `<SecaoNotificacoes />` antes de "Aparelhos conectados" (hoje `null`) | A |
| `web/src/acesso/Entrar.tsx` | `<LinkEsqueci />` (hoje o texto do M1; o épico B troca por um link para `/esqueci-a-senha`) | B |
| `web/src/rotas.tsx` | `...rotasNotificacoes`, `...rotasRecuperacao` | A, B |
| `web/src/administracao/frases.ts` | frases de `recuperacao_pedida` e `senha_redefinida` (prontas) | comum |

Teste dos encaixes e das funções de API: `web/src/m2contrato.test.ts`.

## 8. CSP (`vercel.json`)

**Nenhuma mudança.** A CSP atual é `default-src 'self'; frame-ancestors 'none'; base-uri 'self';
form-action 'self'; object-src 'none'`. Pela CSP 3:

- `worker-src` recua para `child-src`, `script-src` e `default-src`: o `/sw.js` do próprio
  Portal vale (`'self'`).
- `manifest-src` recua para `default-src`: o `/manifest.webmanifest` vale.
- O Web Push não passa pela CSP: quem fala com o serviço de push (Google, Apple, Mozilla) é o
  navegador, não a página; o `pushManager.subscribe` e a entrega não são `fetch` da página.
- O toque na notificação abre uma página do próprio Portal.

Acrescentar `worker-src 'self'; manifest-src 'self'` não mudaria nada, então fica de fora (o
mínimo necessário é zero). O teste `web/testes/cabecalhos.test.ts` segue a cadeia de recuo e
falha se alguém endurecer uma diretiva dela sem pensar no service worker. Os arquivos de
`web/public/` saem como estáticos antes do `rewrite` para o `index.html` (a Vercel serve o que
existe no sistema de arquivos primeiro); conferir no portão que `/sw.js` responde JavaScript, e
não o `index.html`.

## 9. Posse dos arquivos

**Épico A · Push e PWA** edita só: `api/app/rotas/push.py`, `api/app/esquemas/push.py`,
`api/app/servicos/push.py`, `api/testes/test_push*.py` (novos), `web/src/notificacoes/**`,
`web/public/sw.js` e `web/public/manifest.webmanifest` (novos), a linha do manifest em
`web/index.html` (e as metas de PWA do iPhone, se precisar), o teste dela em
`web/testes/pwa.test.ts` (novo), `docs/superpowers/duvidas-m2-push.md` (novo). Nos testes
comuns, só: apagar a seção "épico A" de `api/testes/test_m2_em_construcao.py` e tirar
`/api/notificacoes` de `EM_CONSTRUCAO` em `api/testes/test_cache.py`.

**Épico B · E-mail** edita só: `api/app/rotas/recuperacao.py` (sem pôr `Banco` em `pedir`),
`api/app/esquemas/recuperacao.py`, `api/app/servicos/recuperacao.py`,
`api/app/servicos/email.py`, `api/testes/test_recuperacao*.py` e `api/testes/test_email*.py`
(novos), `web/src/recuperacao/**`, `docs/superpowers/duvidas-m2-email.md` (novo). Nos testes
comuns, só: apagar a seção "épico B" de `api/testes/test_m2_em_construcao.py`.

**Comuns — nenhum épico edita** (se precisar, avisa o coordenador e explica no arquivo de
dúvidas do épico): `api/migracoes/**` (**nenhuma migração nova no M2 sem o coordenador**),
`api/app/modelos/**`, `api/app/configuracao.py`, `api/app/comandos/**`,
`api/app/servicos/{notificacoes,segundo_plano,historico,avisos,acesso,tentativas}.py`,
`api/app/seguranca/**`, `api/app/esquemas/{comum,acesso,avisos}.py`,
`api/app/rotas/{avisos,envios,acesso,sessao}.py`, `api/app/main.py`, `api/app/erros_api.py`,
`api/testes/{conftest,apoio}.py` e os testes já existentes (inclusive `test_m2_rotas.py`,
`test_m2_banco.py`, `test_m2_notificacoes.py`, `test_m2_configuracao.py`, `test_m2_backup.py`;
as únicas exceções são as dos parágrafos acima), `scripts/backup/**`, `api/pyproject.toml`,
`api/uv.lock` (as dependências do M2, `pywebpush` e `vercel`, já estão), `api/.env.example`,
`web/src/{main.tsx,rotas.tsx,estilo.css}`, `web/src/{api,casca,acesso,avisos,administracao}/**`,
`web/package*.json`, `web/vite.config.ts`, `vercel.json`, `.github/**`, `docs/0*.md`,
`docs/adr/**`, este spec. A versão do `web/package.json` e o `web/src/sobre/novidades.ts`
mudam só no fechamento do marco (coordenador). Um épico **pode** criar um CSS próprio
(`web/src/<pasta do épico>/<nome>.css`).

Usar sem editar: `trocar_senha_e_sessao`, `gravar_cookie` (`app/seguranca/sessoes.py`),
`esquecer_login` (`app/servicos/tentativas.py`), `registrar` e `registrado_recentemente`
(histórico), `destinos_*`, `cota_*`, `reservar_email_recuperacao`, `SALVAR_A_CADA`,
`AvisoParaNotificar`, `Resultado` (`app/servicos/notificacoes.py`), `config_*`
(`app/configuracao.py`), `agendar` (`app/servicos/segundo_plano.py`), `Placa`, `Tela`,
`useSessao`, `useRecado` (casca), `Campo`, `CaixaDeErro`, `campos.ts` (`web/src/acesso/`).

Mudança no contrato (campo novo, rota nova) dentro do próprio épico é permitida nos arquivos do
épico, desde que `test_contrato.py` continue verde e a mudança fique registrada no arquivo de
dúvidas do épico. Banco de teste próprio: `PORTAL_TESTE_BANCO=portal_teste_m2_push` e
`portal_teste_m2_email`.

## 10. Fica de fora desta onda

Implementação das histórias; criar a conta Gmail, a senha de app e as chaves VAPID de produção;
variáveis na Vercel; migração no Neon (produção e `previa`); teste num iPhone de verdade (portão
do M2); qualquer execução na Vercel ou no Neon.
