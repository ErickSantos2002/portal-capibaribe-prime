# Dúvidas e decisões do M2 · Onda 1 (contrato)

Decisões tomadas sem perguntar a ninguém durante a onda do contrato do M2. Cada item: a dúvida,
o que foi decidido e por quê. **[Erick]** marca o que só o Erick pode confirmar (regra do
condomínio, custo ou preferência dele); o resto é decisão técnica que pode ser revista na
revisão do marco.

Os agentes dos épicos registram as próprias dúvidas em `duvidas-m2-push.md` (épico A) e
`duvidas-m2-email.md` (épico B).

## 1. Sem `PORTAL_VAPID_PUBLICA`: a chave pública sai da privada
- **Dúvida:** o pedido citava `VAPID_PUBLICA` e `VAPID_PRIVADA` como variáveis.
- **Decisão:** só `PORTAL_VAPID_PRIVADA` (e `PORTAL_VAPID_CONTATO`); a API calcula a pública.
  Nomes com o prefixo `PORTAL_`, como `PORTAL_DIAGNOSTICO_SEGREDO`.
- **Por quê:** duas variáveis que precisam combinar são um jeito de errar a configuração (o
  navegador inscreveria com uma chave e o envio assinaria com outra, e nada chegaria, sem erro
  nenhum). O comando `gerar_chaves_vapid` imprime a pública só para conferência.

## 2. Envio depois da resposta: `wait_until` + caixa de saída, no máximo uma vez
- **Dúvida:** `BackgroundTasks` do FastAPI sobrevive depois da resposta na Vercel?
- **Decisão:** `vercel.functions.wait_until` na Vercel e `BackgroundTasks` fora dela, com o
  pedido de notificar gravado no banco junto com o aviso. Detalhes e alternativas na
  [ADR-0010](../adr/0010-envio-em-segundo-plano.md).
- **Por quê:** a documentação da Vercel não garante o `BackgroundTasks` (no modo sem Fluid, o
  código do runtime segura a resposta até ele terminar); o `wait_until` é o caminho oficial do
  SDK Python e o runtime o drena depois de enviar a resposta. A caixa de saída faz o envio que
  se perdeu sair na próxima publicação.
- **Garantia escolhida:** no máximo uma vez por aviso e canal. Se a função morrer no meio, o
  resto não é reenviado (`interrompido`), porque repetir para quem já recebeu incomoda mais.
  Revisar se as contagens mostrarem perda.

## 3. Service worker escrito à mão, sem `vite-plugin-pwa`
- **Dúvida:** `05-arquitetura.md` (seção 2) cita o `vite-plugin-pwa`.
- **Decisão:** `web/public/sw.js` e `web/public/manifest.webmanifest` escritos à mão pelo épico
  A, sem cache de páginas. Nenhuma dependência nova no front.
- **Por quê:** o plugin existe para pré-cache (funcionar sem internet), que o M2 não pede. O
  Chrome não exige mais tratamento de `fetch` para instalar, e o push só precisa dos eventos
  `push` e `notificationclick`. Pré-cache num app que muda de versão toda semana arrisca mostrar
  tela velha ao morador. Atualizar a arquitetura no fechamento do marco (item 16).

## 4. Quem publica não recebe a própria notificação **[Erick]**
- **Dúvida:** H-13 diz "as unidades do destino recebem"; a unidade que publicou também é do
  destino.
- **Decisão:** a unidade que publicou fica de fora do push e do e-mail (ela já conta como quem
  leu, desde o M1).
- **Por quê:** a Comissão receberia o aviso que acabou de escrever. Efeito colateral: o outro
  celular da mesma casa (o cônjuge de quem publicou) também não recebe. Se o Erick preferir que
  receba, é uma linha em `_unidades_do_destino` (`app/servicos/notificacoes.py`).

## 5. Cota do Gmail: 450 por 24 horas, 50 guardados para o "esqueci a senha" **[Erick]**
- **Dúvida:** a ADR-0006 fala em ~500 envios por dia; cada aviso para todos pode ir a até 320
  unidades.
- **Decisão:** janela móvel de 24 horas com no máximo 450 e-mails (margem de 50), dos quais 50
  só para links de recuperação. O que não cabe na cota vira `pulados` no envio, sem erro; o push
  vai sempre.
- **Por quê:** estourar o limite do Gmail bloqueia a conta por até um dia, e aí nem o "esqueci
  a senha" funciona. Hoje há 23 unidades ativadas e poucas com e-mail; a conta só aperta com
  muitas unidades com e-mail **e** dois avisos para todos no mesmo dia. Se apertar, as saídas
  são as da ADR-0006 (domínio + serviço de e-mail transacional).

## 6. Correção de aviso não notifica de novo **[Erick]**
- **Dúvida:** H-13 fala de publicação; H-15 (corrigir) não fala de notificação.
- **Decisão:** só a publicação notifica. A tabela já impede notificar duas vezes o mesmo aviso
  pelo mesmo canal.
- **Por quê:** correção costuma ser vírgula ou horário; notificar de novo treina o morador a
  ignorar. O mural já mostra "Corrigido" para quem leu a versão anterior (U1 do M1). Se um dia
  quiser notificar correção importante, entra uma coluna `versao` na chave do envio.

## 7. Cópia por e-mail para toda unidade com e-mail, sem opção de desligar **[Erick]**
- **Dúvida:** o primeiro acesso diz "Com e-mail, você recupera a senha sozinho e recebe os
  avisos também por lá." Não há opção de receber só a recuperação.
- **Decisão:** quem cadastrou e-mail recebe as cópias; o rodapé do e-mail diz como parar
  (apagar o e-mail em Minha unidade, o que também desliga o "esqueci a senha").
- **Por quê:** é o que a tela do M1 já prometeu. Uma opção "só para recuperar a senha" é uma
  coluna nova e uma tela nova; fica para quando alguém pedir.

## 8. Limites contra abuso
- **Decisão:** no banco, até 10 aparelhos com notificação por unidade e até 3 links de
  recuperação por hora e 6 por dia por unidade; na aplicação, a cota do Gmail (item 5). O
  pedido de recuperação **não tem limite por IP**.
- **Por quê:** os limites por unidade protegem a caixa de cada morador e a função (cada
  inscrição é um POST a cada aviso). Por IP, o pior caso é alguém pedir links para muitos
  apartamentos e gastar a cota do dia: 320 × 3 já passa da cota, mas a reserva de 50 e o limite
  por unidade seguram o estrago em um dia. **[Erick]**: se acontecer, a saída é uma segunda
  regra no firewall da Vercel para `/api/acesso/recuperacao` (hoje a única regra grátis está no
  login, ADR-0005).

## 9. Rota de envios sem tela
- **Decisão:** `GET /api/avisos/{id}/envios` (gestão) existe e é testada, mas nenhuma tela usa
  no M2.
- **Por quê:** o portão do M2 precisa conferir "chegou no Bloco 1 e não no Bloco 2"; a rota dá
  isso sem abrir o banco. Uma linha "Notificação enviada a N aparelhos" na tela de leitura é
  candidata a melhoria depois.

## 10. Criar senha nova pelo link já entra e desconecta os outros aparelhos
- **Decisão:** `redefinir` faz como "trocar a senha" do M1: encerra todas as sessões (e as
  inscrições de push vão junto), abre uma sessão nova para quem redefiniu e devolve `Eu`.
- **Por quê:** quem pede o link quase sempre é quem perdeu o acesso; deixar entrado poupa um
  passo da Dona Socorro. Derrubar os outros aparelhos é o que a troca de senha já faz, e é o
  certo se a senha vazou. O outro celular da casa precisa entrar de novo e reativar as
  notificações.

## 11. O token do link vai depois do `#`
- **Decisão:** `…/redefinir-senha#token=…`; a tela lê, apaga da barra e manda no corpo do POST.
- **Por quê:** a parte depois do `#` não sai do navegador: não aparece em log de acesso da
  Vercel nem no `Referer`. Também por isso `conferir` é POST, e não GET com o token na URL.

## 12. Só serviços de push conhecidos (contra SSRF)
- **Decisão:** o endpoint da inscrição precisa ser de `fcm.googleapis.com`,
  `*.push.services.mozilla.com`, `*.push.apple.com` ou `*.notify.windows.com`, em `https`, sem
  porta nem usuário.
- **Por quê:** a função faz um POST para cada endpoint a cada aviso; aceitar qualquer endereço
  deixaria uma conta comum fazer a Vercel chamar endereços escolhidos por ela. Risco aceito: um
  navegador com outro serviço de push fica sem notificação até entrar na lista (o e-mail e o
  mural continuam). Os quatro cobrem Chrome, Samsung Internet, Opera, Edge, Firefox e Safari.

## 13. Aviso arquivado antes do envio, ou envio esquecido por mais de 24 horas
- **Decisão:** os dois viram `interrompido`, sem mandar nada.
- **Por quê:** notificar um aviso que saiu do mural leva o morador a uma tela de "não
  encontrado"; notificação de aviso de ontem não ajuda ninguém.

## 14. O histórico registra o pedido de recuperação, inclusive quando não manda
- **Decisão:** `recuperacao_pedida` é ação do Portal (quem pede não entrou), com `enviado` e o
  `motivo` (`sem_email`, `limite`, `cota`, `desligado`); só para unidade que existe. A tela do
  histórico já escreve a frase ("não mandou link de senha nova ao Bloco 1, 203: sem e-mail
  cadastrado").
- **Por quê:** a resposta ao morador não pode revelar se há e-mail, mas a administração precisa
  saber que alguém do 203 tentou e não conseguiu, para procurar a família no grupo. O motivo
  não é dado pessoal (não diz qual é o e-mail).

## 15. O título do aviso aparece na tela bloqueada
- **Decisão:** a notificação mostra o título do aviso (H-13: "notificação com o título").
- **Por quê:** avisos da Comissão não são sigilosos e o título é o que faz a pessoa abrir.
  Fica registrado porque qualquer um que pegue o celular vê o título.

## 16. Documentos a atualizar no fechamento do M2 (coordenador)
- `04-modelo-de-dados.md`: `inscricao_push` ganhou `criada_em`, o limite de 10 e o formato das
  chaves; `token_recuperacao` ganhou `criado_em` e os limites; tabela nova `notificacao_envio`;
  inventário LGPD sem mudança (só contagens).
- `05-arquitetura.md`: seção 2 (sem `vite-plugin-pwa`, item 3) e seção 6.2 (envio depois da
  resposta, ADR-0010).
- README: variáveis novas e o comando `gerar_chaves_vapid` (já em `api/.env.example`).

## 17. Dependência nova `vercel` (SDK Python oficial)
- **Dúvida:** o pacote traz muita coisa (sandbox, filas, workflow) para usar uma função.
- **Decisão:** usar o `vercel` mesmo, importado só dentro de `segundo_plano.agendar`.
- **Por quê:** é o caminho documentado para o `wait_until`; ler o contexto interno do runtime
  direto (`vercel.cache.context`) quebraria em silêncio numa atualização. O tamanho da função
  continua longe do limite.

## 18. Conta Gmail, senha de app e chaves VAPID de produção **[Erick]**
- **Situação:** nada disso existe ainda; o contrato funciona sem (canais desligados).
- **Para ligar:** (1) criar a conta Gmail do Portal com verificação em duas etapas e gerar a
  senha de app; (2) `uv run python -m app.comandos.gerar_chaves_vapid` duas vezes (produção e
  prévia); (3) na Vercel, `PORTAL_VAPID_PRIVADA`, `PORTAL_VAPID_CONTATO`
  (`mailto:<conta do Portal>`), `PORTAL_SMTP_USUARIO`, `PORTAL_SMTP_SENHA_APP` e
  `PORTAL_URL_BASE=https://portal-capibaribe-prime.vercel.app` como variáveis sensíveis de
  Production; na prévia, só o VAPID da prévia (sem SMTP); (4) migração 0005 no Neon (produção e
  `previa`). Tudo isso é com o coordenador, depois dos épicos.
