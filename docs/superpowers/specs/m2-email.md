# Spec · M2 · Épico B · E-mail e "esqueci a senha"

| | |
|---|---|
| **Marco** | M2 · Notificações (`docs/07-roadmap.md`, seção do M2) |
| **Histórias** | H-04 (esqueci a senha), H-13 (a parte do e-mail) |
| **Base** | contrato `m2-contrato.md` (seções 4.3, 5, 6 e 9), ADR-0006, ADR-0008, ADR-0010, `duvidas-m2.md`, protótipo (`#esqueci`, `#esqueci-ok`) |
| **Criado em** | 06/10/2026 |
| **Plano** | `docs/superpowers/plans/m2-email.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m2-email.md` |

> **Revisão independente (código e UX):** o que mudou depois da primeira versão (assunto do
> aviso, textos das telas e do e-mail, `remetente` e `assunto` na resposta do pedido, cota do
> Gmail na mensagem, trava da unidade, reserva devolvida) está em `duvidas-m2-email.md`, item
> 16, e vale sobre o texto abaixo.

## 1. Objetivo

Ligar o canal de e-mail que o contrato deixou marcado: a cópia do aviso por e-mail para as
unidades do destino que têm e-mail, e o "esqueci a senha" de ponta a ponta (pedido, e-mail com o
link, tela do link e senha nova). Sem migração nova e sem mexer nos arquivos comuns, salvo os
dois testes de encaixe registrados nas dúvidas (itens 1 e 2).

Tudo funciona sem a conta do Gmail: sem `PORTAL_SMTP_*` e `PORTAL_URL_BASE`, o canal fica
desligado (os envios ficam `desligado`, o pedido de link registra `motivo = "desligado"`), e
**nenhum teste fala com o Gmail**: o `smtplib.SMTP_SSL` é trocado por um SMTP falso que guarda
as mensagens.

## 2. API

### 2.1 Envio SMTP (`app/servicos/email.py`)

- **Conexão:** `smtplib.SMTP_SSL(host, porta, timeout=20, context=ssl.create_default_context())`
  na porta 465 (padrão do Gmail); em outra porta, `smtplib.SMTP` + `starttls` (o contrato
  admite a 587). Login com a senha de app. **Uma conexão por lote**: a cópia de um aviso abre
  uma conexão e manda todas as mensagens por ela; o "esqueci a senha" abre uma para o e-mail
  dele. No fim, `quit()` (erro ao fechar é ignorado).
- **Uma mensagem por unidade**, com um só endereço no `To` (nunca vários destinatários no
  mesmo e-mail: um morador veria o e-mail do outro).
- **Cabeçalhos:** `From: "Portal Capibaribe Prime" <conta do Portal>`, `To`, `Subject`,
  `Date`, `Message-ID` (domínio da conta), `Auto-Submitted: auto-generated` (RFC 3834: respostas
  automáticas de férias não voltam para o Portal). Sem `Reply-To`. Assunto numa linha só
  (quebras e espaços repetidos viram um espaço): não há como injetar cabeçalho pelo título.
- **Corpo:** `multipart/alternative` com texto puro e HTML simples, em UTF-8.

### 2.2 Cópia do aviso (`ENVIADOR`, H-13)

`ligado()` = `config_email() is not None`. `enviar(db, aviso, resultado)`:

1. `destinos = destinos_email(db, aviso)`; `resultado.destinos = len(destinos)`;
2. `n = resultado.reservar(len(destinos))` **antes de abrir a conexão**; `pulados += len - n`;
   com `n = 0`, não conecta;
3. abre a conexão e manda os `n` primeiros, um por um:
   - antes de cada um, `resultado.tempo_esgotado()` → para; o que faltou vira `pulados`;
   - destinatário recusado (`SMTPRecipientsRefused`) ou mensagem recusada (`SMTPDataError`) →
     `falhas += 1` e segue;
   - qualquer outro erro (conexão caiu, remetente recusado, que é como o Gmail avisa cota
     estourada) **levanta**: a peça comum marca o canal `interrompido` com as contagens até ali
     e loga só o tipo do erro;
   - `resultado.salvar()` a cada `SALVAR_A_CADA` tentativas.
4. Não faz commit (contrato, seção 5).

**Conteúdo** (assunto: o título; "Urgente: " na frente se urgente):

| Parte | Texto puro | HTML |
|---|---|---|
| Cabeçalho | — | faixa verde (mata) com "Portal Capibaribe Prime" |
| Categoria e destino | "Urgente · para o Bloco 1" | rótulo da categoria (cor da categoria, sempre com o nome) e "Para o Bloco 1" / "Para todos os blocos" |
| Título | o título | `<h1>` |
| Texto | o texto do aviso **como foi escrito** (as marcas `##`, `-`, `1.`, `>` e `**` são legíveis em texto puro) | o Markdown restrito do Portal convertido (2.4) |
| Link | "Abrir no Portal: <url_base>/avisos/<id>" | botão "Abrir no Portal" + o endereço escrito embaixo |
| Rodapé | "Você recebe porque cadastrou este e-mail no Portal Capibaribe Prime. Para não receber mais, desmarque “Receber os avisos por e-mail” em Minha unidade, no Portal: <url_base>/minha-unidade. O e-mail continua valendo para o “Esqueci minha senha”." | o mesmo, em letra menor, com "Minha unidade" em link no lugar do endereço |

**Ajustes do M2 (1.3.0):** parar de receber passou a ser a opção "Receber os avisos por e-mail"
de Minha unidade (resposta do Erick à dúvida 7 do contrato). O e-mail continua cadastrado e o
"esqueci a senha" continua funcionando, então saiu o alerta "Sem e-mail, o “esqueci a senha”
também deixa de funcionar." que a 1.2.0 tinha (item 3 de `duvidas-m2-email.md`). Os destinos
pulam quem desligou (`destinos_email`).

### 2.3 E-mail de recuperação (H-04)

Assunto "Portal Capibaribe Prime: criar senha nova". Texto: "Pediram um link para criar senha
nova no Portal Capibaribe Prime para o Bloco N, apartamento NNN.", o link
(`url_base + "/redefinir-senha#token=<token>"`), "O link vale por 1 hora e só uma vez." e "Se
não foi você, apague este e-mail; sua senha continua a mesma.". No HTML, o mesmo com o botão
"Criar senha nova". O token aparece só no corpo do e-mail; nunca em log.

### 2.4 Markdown restrito → HTML (`html_do_texto`)

Porte fiel de `web/src/avisos/formatacao.ts` e `partesDaLinha` (`formatos.ts`): `## ` vira
`<h2>`, `- ` lista, `1. ` lista numerada (com `start`), `> ` caixa de destaque, `**…**` negrito,
`http(s)://` link, linha em branco separa parágrafos, quebra simples vira `<br>`. **Todo texto
passa por `html.escape`** antes de virar HTML; só as marcas acima geram tags, sempre fixas, com
estilo inline (cliente de e-mail ignora `<style>` com frequência). Link só `http`/`https`, com
o endereço escapado também no `href`. Mudou o front, mude aqui (o teste de paridade usa os
mesmos exemplos do `formatacao.test.ts`).

### 2.5 Esqueci a senha (`app/servicos/recuperacao.py`)

`processar_pedido(login, fabrica=None)` exatamente como a seção 4.3 do contrato: unidade ativa
pelo login (não existe → nada, nem histórico); sem `ativada_em` ou sem e-mail → `sem_email`;
`config_email()` nula → `desligado`; `reservar_email_recuperacao(db)` falso → `cota`; INSERT do
token num *savepoint* (`token_recuperacao_limite_hora`/`_dia` → `limite`; o `_sem_email` do
banco também vira `sem_email`, se a unidade mudar entre a leitura e o INSERT); histórico
`recuperacao_pedida` se não houver um na última hora; commit; e só então o e-mail. Nada levanta
para fora; erro vira `log.error` com o tipo, sem login, e-mail ou token.

`conferir(db, token) -> UnidadeRef`: token pelo SHA-256, não usado, `expira_em > now()`,
`criado_em >= unidade.senha_trocada_em`, unidade ativa e ativada. Senão 410 `link_invalido`
("Este link venceu ou já foi usado. Peça outro em "Esqueci minha senha"."). Não gasta o link.

`redefinir(db, dados, user_agent) -> (Eu, token_de_sessao)`: token `for update`, mesma
conferência, **`usado_em` marcado primeiro** (o banco recusa usado ou vencido: vira o mesmo
410), depois `trocar_senha_e_sessao` (desconecta todos os aparelhos, a inscrição de push vai
junto), `tentativas.esquecer_login`, histórico `senha_redefinida` (da própria unidade) e o `Eu`.
A rota faz o commit e grava o cookie.

## 3. Front (`web/src/recuperacao/`)

- `<LinkEsqueci />` (na tela de entrar): link "Esqueci minha senha" para `/esqueci-a-senha`.
- **`/esqueci-a-senha`** (`EsqueciASenha.tsx`, só sem sessão, como `/entrar`): título "Esqueci
  minha senha" com seta de voltar para `/entrar`; a frase do protótipo; bloco em 5 botões e
  apartamento, **o mesmo formato e as mesmas regras da tela de entrar** (`montarLogin`,
  `limparApartamento`, colar `1203` marca o bloco); "Enviar link". Erros de formulário antes de
  mandar: sem bloco, sem apartamento, apartamento impossível ("Esse apartamento não existe.
  Confira o bloco e o número da porta.", do protótipo). Depois do 202, a caixa de status com a
  mensagem da API (H-04, sempre a mesma), o parágrafo para quem não tem e-mail (grupo do
  WhatsApp, a administração volta a senha para a inicial) e "Voltar para a entrada". Antes de
  pedir, a mesma dica para quem não tem e-mail aparece embaixo do botão (dúvidas, item 11).
- **`/redefinir-senha`** (`RedefinirSenha.tsx`, pública): lê `#token=` uma vez, apaga o `#` da
  barra (`history.replaceState`) e chama `conferir`. Estados: conferindo; link inválido (caixa
  com a mensagem da API, botão "Pedir outro link" → `/esqueci-a-senha`, e "Voltar para a
  entrada"); sem token no endereço (mesma tela de inválido); sem conexão (mensagem e "Tentar de
  novo"); válido → placa da unidade, "Criar senha nova para o Bloco N, apartamento NNN", senha
  nova e repetida com `Campo` e `validarSenhaNova` / `AJUDA_DA_SENHA` (as mesmas regras e
  mensagens do primeiro acesso), "Salvar senha nova". Sucesso: `definir(eu)` e mural com o
  recado "Senha nova criada. Os outros aparelhos foram desconectados.". 410 ao salvar (o link
  venceu no meio) leva à tela de inválido.
- Se o link abre num aparelho já conectado, a tela funciona igual (rota pública) e, ao salvar,
  a sessão deste aparelho passa a ser a nova.
- CSS próprio em `web/src/recuperacao/recuperacao.css`, só com tokens da casca.

## 4. Testes

API (`api/testes/test_email*.py`, `test_recuperacao*.py`): SMTP falso; uma conexão por lote;
cota e `pulados`; tempo esgotado; recusa de um destinatário segue; queda interrompe; `salvar` a
cada 25; cabeçalhos e uma pessoa por mensagem; HTML escapado (`<script>`, `<img onerror>`,
`javascript:`, aspas em link); paridade com o Markdown do front; pedido para cada motivo;
histórico uma vez por hora; nada de token em log; resposta e tempo iguais com e sem e-mail;
conferir/redefinir com token vencido, usado, de senha já trocada, inexistente e de unidade
resetada; redefinir entra, desconecta os outros e mata os outros links; fluxo completo pelo
link do e-mail.

Front (Vitest): link na entrada; pedido com o login montado e mensagem sempre igual; erros de
formulário; tela do link (válido, inválido, sem token, apaga o `#`), regras da senha, sucesso
com recado e sessão.
