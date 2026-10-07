# Spec · M2 · Épico A · Push e PWA

| | |
|---|---|
| **Marco** | M2 · Notificações (`docs/07-roadmap.md`) |
| **Histórias** | H-05 (instalar e ativar notificações), H-13 (a parte push: ser avisado) |
| **Base** | [contrato do M2](m2-contrato.md) (seções 4.2, 5, 7, 8 e 9), ADR-0006, ADR-0010, `duvidas-m2.md`, protótipo (`#instalar` e Minha unidade) |
| **Criado em** | 06/10/2026 |
| **Plano** | `docs/superpowers/plans/m2-push.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m2-push.md` |

## 1. Objetivo

Quem mora recebe no celular a notificação de cada aviso novo do seu bloco, com o título, e o
toque abre o aviso. Para isso o Portal vira um aplicativo instalável (PWA), oferece **uma vez**,
depois do primeiro acesso, "Instalar na tela inicial" e "Ativar notificações", e deixa ativar e
desativar a qualquer hora em Minha unidade. Recusar não atrapalha nada: o mural continua sendo
o registro oficial.

Fica de fora: banco (a migração 0005 já está em produção; nenhuma migração nova), versão e
novidades (o coordenador faz a 1.2.0 no merge), e-mail (épico B).

## 2. API

### 2.1 Rotas (`app/rotas/push.py`, contrato 4.2)

| Rota | Faz |
|---|---|
| `GET /api/notificacoes` | `disponivel` = há VAPID válido; `chave_publica` = a pública calculada da privada (nula se desligado); `este_aparelho` = a sessão da requisição tem inscrição |
| `PUT /api/notificacoes/este-aparelho` | sem VAPID: 503 `notificacoes_desligadas`. Senão, guarda a inscrição **na sessão da requisição**: apaga a inscrição antiga desta sessão se o endpoint mudou, e insere com `on conflict (endpoint) do update set sessao_id, chaves` (o endpoint que estava em outra sessão passa para esta). Restrição `inscricao_push_limite` → 409 `limite_de_aparelhos`. 204 |
| `DELETE /api/notificacoes/este-aparelho` | apaga a inscrição da sessão da requisição; 204 mesmo sem inscrição |

- O `app` não tem UPDATE em `endpoint` (contrato 2.4): trocar o endpoint é apagar e inserir,
  e passar um endpoint para esta sessão é UPDATE de `sessao_id`, que é permitido.
- Sessão encerrada no meio (restrição `inscricao_push_sessao_encerrada`): 401 `sem_sessao`,
  como qualquer sessão que caiu.

### 2.2 Envio (`app/servicos/push.py`, contrato 4.2 e 5)

`EnviadorPush.ligado()` = `config_push() is not None`. `enviar(db, aviso, resultado)`:

1. `destinos = destinos_push(db, aviso)`; `resultado.destinos = len(destinos)`.
2. Corpo único para todos (`PushAviso`: `aviso_id`, `titulo`, `categoria`, `url =
   aviso.caminho`), em JSON compacto. **Sem dado pessoal**: nada de unidade, autor ou texto do
   aviso (o texto pode ser longo e ficaria na tela bloqueada).
3. Cabeçalhos: `TTL` 3 dias (259.200 s), `Urgency: high` se `categoria == "urgente"` (senão
   `normal`), `Topic: aviso-<id>` (uma notificação substitui a outra do mesmo aviso no serviço
   de push, se o aparelho estava desligado).
4. Em lotes de `SALVAR_A_CADA` destinos, num `ThreadPoolExecutor` de até 10 threads, cada
   thread chama `pywebpush.webpush(...)` com `timeout=10` e um `Vapid` lido uma vez, e devolve
   só o código: `entregue`, `removida` (404/410) ou `falha` (outro status, erro de rede, tempo
   esgotado). **`vapid_claims` é um dicionário novo por chamada**: o `webpush` grava nele o
   `aud` do primeiro endpoint, e reaproveitar o mesmo dicionário assinaria o Apple com o `aud`
   do Google.
5. Na thread principal, depois de cada lote: conta, apaga as inscrições removidas (`delete …
   where sessao_id in (…) and endpoint = …`, para não apagar uma inscrição que trocou de
   endpoint no meio) e `resultado.salvar()`. Antes de cada lote, `resultado.tempo_esgotado()`:
   se sim, o resto vira `pulados` e para.
6. Nada de commit em `db` (quem chama commita); nenhum log com endpoint ou chave (o endpoint
   identifica o aparelho); erro de um destino conta como falha e segue.

## 3. Front

### 3.1 Arquivos (só os do épico A, contrato 9)

| Arquivo | O quê |
|---|---|
| `web/public/manifest.webmanifest` | `id` e `scope` `/`, `start_url` `/avisos`, `display: standalone`, `theme_color` `#1f5e3b` (verde-mata), `background_color` `#f4f6f2` (papel), `lang` `pt-BR`, ícones 192 e 512 |
| `web/public/sw.js` | `install` → `skipWaiting`; `activate` → `clients.claim`; `push` → `showNotification(titulo)` com ícone, `tag aviso-<id>` e `data.url`; `notificationclick` → foca uma janela do Portal e navega para o aviso, ou abre uma nova; `pushsubscriptionchange` → inscreve de novo e manda para a API. **Sem `fetch` e sem cache** (seção 3.4) |
| `web/index.html` | `<link rel="manifest">` e `apple-mobile-web-app-title` |
| `web/src/notificacoes/aparelho.ts` | o que este aparelho sabe fazer: suporte a push, permissão, iPhone/iPad, Safari, instalado, Android, pedido de instalação guardado |
| `web/src/notificacoes/inscricao.ts` | ativar (pedir permissão **dentro do toque**, inscrever, mandar para a API), desativar, sincronizar ao abrir o Portal |
| `web/src/notificacoes/ganchos.ts` | `registrarServiceWorker()` (registra `/sw.js` com `updateViaCache: 'none'`, guarda o `beforeinstallprompt`, sincroniza a inscrição), `destinoDepoisDoPrimeiroAcesso()` (`/receber-avisos` na primeira vez deste aparelho, depois `/avisos`) |
| `web/src/notificacoes/useNotificacoes.ts` | estado da tela (seção 3.3) e as ações |
| `web/src/notificacoes/ReceberAvisos.tsx` | a tela "Receber os avisos" (`/receber-avisos`, com `ExigeUnidade`) |
| `web/src/notificacoes/SecaoNotificacoes.tsx` | a seção "Notificações" de Minha unidade |
| `web/src/notificacoes/notificacoes.css` | estilo próprio (o `estilo.css` é comum) |

### 3.2 Telas

**Receber os avisos** (protótipo `#instalar`), depois do primeiro acesso, uma vez por aparelho
(`localStorage` `portal-oferta-avisos`; sem `localStorage`, aparece e pronto, porque o primeiro
acesso só acontece uma vez por apartamento). Também abre por "Como instalar" em Minha unidade.

- "Quer ser avisado na hora?" / "Dois passos, uma vez só. Dá para fazer depois em Minha
  unidade."
- **Coloque o Portal na tela inicial** · "Ele abre como um aplicativo, direto pelo ícone."
  - Já instalado (aberto pelo ícone): "Pronto: o Portal já está na tela inicial."
  - O navegador ofereceu instalar (`beforeinstallprompt`, Chrome/Edge/Samsung): botão
    **Instalar na tela inicial**.
  - iPhone/iPad: passo a passo (Compartilhar → Adicionar à Tela de Início → abrir pelo ícone
    novo) e "No iPhone, as notificações só chegam se o Portal for aberto pelo ícone." Fora do
    Safari: "Se não achar a opção, abra este endereço no Safari."
  - Android sem o pedido: "No menu ⋮ do navegador, escolha Instalar aplicativo ou Adicionar à
    tela inicial."
  - Computador: o texto do protótipo (Chrome e Edge instalam; Firefox funciona pelo navegador).
- **Ative as notificações** · "Só quando sair aviso oficial do condomínio." Com os estados da
  seção 3.3. Some se o servidor está sem VAPID.
- **Ir para o mural** (botão principal).

**Minha unidade · Notificações** (antes de "Aparelhos conectados"): a situação deste aparelho
numa frase, o botão de ativar ou desativar, e o link "Como instalar o Portal na tela inicial".
Sem VAPID no servidor, mostra só o link. Desativar nos outros aparelhos continua sendo
"Desconectar" (a inscrição vai junto).

### 3.3 Estados das notificações neste aparelho

| Estado | Quando | O que aparece |
|---|---|---|
| `carregando` | lendo a API | "Conferindo as notificações deste aparelho…" |
| `desligado` | `disponivel` falso | nada (a oferta some) |
| `precisa_instalar` | iPhone/iPad fora do ícone instalado | "No iPhone, primeiro coloque o Portal na tela inicial e abra por lá. Depois ative aqui." |
| `ios_antigo` | iPhone instalado sem `PushManager` | "Este iPhone precisa do iOS 16.4 ou mais novo para receber notificações. Atualize em Ajustes › Geral › Atualização de Software." |
| `sem_suporte` | sem service worker, `PushManager` ou `Notification` | "Este navegador não recebe notificações. No Android, use o Chrome. Os avisos continuam no mural." |
| `bloqueada` | `Notification.permission === 'denied'` | "As notificações estão bloqueadas neste aparelho." + como liberar (iPhone, Android instalado, navegador) |
| `inativa` | o resto | botão **Ativar notificações** |
| `ativa` | permissão dada, inscrição no navegador e na API | "Ligadas neste aparelho." + **Desativar neste aparelho** |

Ao ativar: o pedido de permissão sai **do toque** (exigência do iPhone); recusar no pedido →
`bloqueada` se o navegador gravou "negar", `inativa` com "Tudo bem. Dá para ativar depois." se
só fechou. Erro da API (409 limite, 503 desligado, sem conexão): a mensagem da API numa
`CaixaDeErro`, e a inscrição local é desfeita para não ficar meio ligada.

**Sincronização** (mural, Minha unidade e oferta): se a permissão já foi dada, o navegador
tem inscrição e foi esta unidade que ativou neste navegador, confere `GET /api/notificacoes`;
se a sessão desta vez não tem inscrição (entrou de novo, trocou a senha) ou a chave do
servidor mudou, inscreve de novo sem perguntar nada. Sair do Portal desfaz a inscrição do
navegador.

**Faixa no mural** (revisão): "Falta um passo: ative as notificações para saber dos avisos na
hora." com "Ativar" e "Agora não" (30 dias), só no estado `inativa`.

### 3.4 Cache

O service worker **não trata `fetch`** e não guarda nada em cache: toda tela vem da rede, como
hoje. O Portal muda de versão com frequência; um cache de páginas pode prender o morador numa
versão velha (contrato 4.2, dúvida 3 do M2). O registro usa `updateViaCache: 'none'`, para o
navegador buscar o `sw.js` novo sem passar pelo cache HTTP, e o `skipWaiting` + `clients.claim`
fazem a versão nova do service worker valer na hora (não há cache para ficar incoerente).

## 4. Testes

- API (`api/testes/test_push_rotas.py`, `test_push_envio.py`): estado com e sem VAPID; inscrever
  guarda na sessão certa, troca o endpoint, move o endpoint de outra sessão, 409 no 11º
  aparelho, 503 sem VAPID; remover idempotente; envio com `webpush` falso: corpo, TTL,
  cabeçalhos, `aud` por endpoint, 201 entregue, 404/410 apagam, 500 e exceção de rede contam
  falha, tempo esgotado vira `pulados`, progresso salvo, nenhum commit, sem dado no log.
- Front (Vitest): `aparelho.ts` (detecções), `inscricao.ts` (permissão no toque, chave, erro
  desfaz), `ganchos.ts`, `ReceberAvisos` e `SecaoNotificacoes` por estado, `sw.js` carregado
  num `self` falso (corpo, toque só abre `/avisos/<n>`).
- Config (`web/testes/pwa.test.ts`, depois do build): `/sw.js` sai como JavaScript (não o
  `index.html`), sem `fetch`; manifest válido; `index.html` com o `<link rel="manifest">`.
- Conferência visual com o Playwright (390 px e computador), prints em
  `docs/superpowers/prints/m2-push/`.

**Só o aparelho de verdade prova** (portão do M2): a entrega pelo FCM e pelo serviço da Apple, o
pedido de permissão do iPhone instalado, a notificação na tela bloqueada e o toque abrindo o
aviso com o app fechado.
