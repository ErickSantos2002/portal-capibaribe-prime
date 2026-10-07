# Dúvidas e decisões do M2 · Épico A (push e PWA)

Decisões tomadas sem perguntar a ninguém durante o épico A. Cada item: a dúvida, o que foi
decidido e por quê. **[Erick]** marca o que só o Erick pode confirmar (regra do condomínio,
custo ou preferência dele); **[coordenador]** marca o que mexe em arquivo comum e precisa de
atenção no merge.

## 1. Dois testes comuns mudaram (era inevitável) **[coordenador]**
- **Dúvida:** o contrato (seção 9) não lista `web/src/m2contrato.test.ts` nem
  `web/src/acesso/PrimeiroAcesso.test.tsx` entre os arquivos do épico A, mas os dois afirmavam o
  comportamento que o épico A existe para mudar (o primeiro acesso levar ao mural; nenhuma rota
  de notificações).
- **Decisão:** mudança mínima. No `m2contrato.test.ts`, o teste "pontos de encaixe" virou dois:
  o do épico A (oferta em `/receber-avisos`, rota declarada) e o do épico B (`rotasRecuperacao`
  vazio, intacto). No `PrimeiroAcesso.test.tsx`, o teste "concluído" espera `/receber-avisos` e
  espera a tela chegar antes de ler o recado (a navegação vem numa transição).
- **No merge:** o épico B também vai mexer no `it` do épico B do `m2contrato.test.ts`. Conflito
  pequeno e previsível: ficar com a versão do A para o primeiro `it` e a do B para o segundo.

## 2. Oferta "uma vez por aparelho" e o segundo celular da casa (resolvido na revisão)
- **Dúvida:** H-05 diz "depois do primeiro acesso, o Portal oferece uma vez". O primeiro acesso
  acontece uma vez por **apartamento**; o celular do cônjuge e o iPhone que acabou de instalar
  (o app instalado não divide o login com o Safari) nunca passam por ele.
- **Decisão:** a oferta continua depois do primeiro acesso, e o mural ganhou a faixa "Falta um
  passo" (item 13), que alcança os dois casos.

## 3. Botão "Ativar notificações" leve, e "Ir para o mural" cheio
- **Decisão:** como no protótipo (`#instalar`): o botão cheio da oferta é "Ir para o mural";
  "Instalar" e "Ativar notificações" são leves. Em Minha unidade, leve também, como os outros
  botões da tela.
- **Por quê:** recusar não pode parecer errado (H-05), e dois botões cheios na mesma tela
  disputavam a atenção (conferido no print).

## 4. Notificação de exemplo logo depois de ativar
- **Decisão:** ao ativar, o Portal mostra uma notificação local ("Notificações ligadas · É
  assim que os avisos do condomínio vão chegar."), sem passar pelo servidor.
- **Por quê:** a Dona Socorro vê na hora que deu certo e como o aviso vai aparecer. Não prova a
  entrega pelo serviço de push (isso é o portão, item 9). Se incomodar, é uma linha
  (`mostrarExemplo` em `useNotificacoes.ts`).

## 5. O texto da notificação
- **Decisão:** título = título do aviso; corpo = "Aviso novo no Portal. Toque para ler." (ou
  "Aviso urgente no Portal. Toque para ler." na categoria urgente). O corpo do push (o que vai
  pelo serviço do Google ou da Apple, cifrado) leva só `aviso_id`, `titulo`, `categoria` e `url`:
  nada do texto do aviso, de quem publicou ou da unidade.
- **Por quê:** o texto pode ser longo e ficaria na tela bloqueada; o título já é o que faz abrir
  (dúvida 15 do M2).

## 6. Sem cache no service worker
- **Decisão:** o `sw.js` não trata `fetch` e não usa a Cache API; registro com
  `updateViaCache: 'none'`, e `skipWaiting` + `clients.claim` para a versão nova valer na hora.
- **Por quê:** contrato 4.2 e dúvida 3 do M2. Sem cache não há o que ficar velho; o Portal
  continua precisando de internet, como hoje. O teste `web/testes/pwa.test.ts` falha se alguém
  puser `fetch` ou `caches.` no `sw.js`.

## 7. Reinscrição sozinha (sem perguntar), só para a unidade que ativou
- **Decisão:** ao abrir o mural (ou Minha unidade, ou a oferta), se a permissão já foi dada, o
  navegador tem inscrição **e foi esta unidade que ativou neste navegador** (`localStorage`
  `portal-push-unidade`), o Portal confere a API e, se a sessão desta vez não tem inscrição
  (entrou de novo, trocou a senha) ou a chave mudou, inscreve de novo. O
  `pushsubscriptionchange` do service worker faz o mesmo quando o navegador troca a inscrição.
- **Revisão:** antes, a unidade B que entrasse no navegador onde a A ativou herdava as
  notificações. Agora sair do Portal desfaz a inscrição do navegador (`SessaoProvider`, mudança
  mínima num arquivo comum **[coordenador]**) e só a unidade dona é reinscrita. Sem
  `localStorage`, ninguém é reinscrito sozinho (o seguro).
- **Por quê:** trocar a senha encerra as sessões e leva as inscrições junto (contrato 2.1); sem
  isso, o celular do casal pararia de receber em silêncio depois de uma troca de senha. Quem
  desativou não é reinscrito: "Desativar" desfaz a inscrição do navegador também. Custo: um
  `GET /api/notificacoes` por abertura, só para quem ativou.

## 8. Endpoint que o serviço disse morto: apagado pela sessão **e** pelo endpoint
- **Decisão:** 404/410 apaga `where sessao_id = … and endpoint = …`.
- **Por quê:** se o aparelho reativou no meio do envio (endpoint novo na mesma sessão), apagar
  só pela sessão levaria a inscrição nova junto. Tem teste.

## 9. O que só o aparelho de verdade prova (portão do M2) **[Erick]**
Testado aqui: a API com o `webpush` trocado por um falso (corpo, cabeçalhos, `aud` do VAPID por
serviço, 201/404/410/500/rede, prazo, progresso), o front com um aparelho falso (permissão,
inscrição, estados), o `sw.js` num `self` falso, e no navegador headless o fluxo de ativar com
uma inscrição falsa gravada na API local (print 3). **Não dá para provar aqui:**
1. a entrega de verdade pelo FCM (Android) e pelo serviço da Apple (iPhone), com as chaves VAPID
   de produção;
2. o pedido de permissão no iPhone instalado (iOS 16.4+), e que fora do ícone ele não aparece;
3. a notificação na tela bloqueada, com o título, e o toque abrindo o aviso **com o app
   fechado** (`openWindow`) e **com o app aberto em outra tela** (`navigate`);
4. o botão "Instalar na tela inicial" do Chrome no Android (o `beforeinstallprompt` só vem com
   HTTPS e critérios do navegador) e o nome "Capibaribe" embaixo do ícone;
5. que a Vercel serve `/sw.js` como JavaScript (e não o `index.html` do rewrite) e o
   `manifest.webmanifest` como `application/manifest+json` (contrato, seção 8);
6. o caminho "liberar notificações bloqueadas" nos textos de cada aparelho (os nomes dos menus
   mudam entre versões do Android e do iOS).
Roteiro sugerido: dois Androids e um iPhone da mesma unidade, aviso para o Bloco 1 e outro
para o Bloco 2, conferir `/api/avisos/{id}/envios`.

## 10. `short_name` "Capibaribe" **[Erick]**
- **Decisão:** o nome embaixo do ícone é "Capibaribe" (o Android corta nomes longos; "Portal
  Capibaribe Prime" vira "Portal Capib…"). Também na meta `apple-mobile-web-app-title`.
- **Alternativa:** "Portal Prime" ou "Capibaribe Prime" (16 letras, pode cortar).

## 11. Ícones sem versão "maskable"
- **Decisão:** os ícones 192 e 512 entram como `purpose: "any"`.
- **Por quê:** a espiral encosta nas bordas; como "maskable", o Android cortaria a arte no
  círculo. Um ícone com margem própria para máscara é melhoria futura (gerar em
  `scripts/dev/gerar-icones.py`).

## 12. Nada de banco, versão ou novidades
- Nenhuma migração nova (a 0005 já tinha tudo), nenhuma mudança em `web/package.json` ou
  `novidades.ts` (o coordenador faz a 1.2.0 no merge).

## 13. Faixa "Falta um passo" no mural (revisão de UX) **[coordenador]**
- **Decisão:** componente `FaixaNotificacoes`, encaixado no topo do mural (`Mural.tsx`, uma
  linha, arquivo comum). Aparece só quando dá para ativar de verdade: push ligado no servidor,
  aparelho que recebe (no iPhone, aberto pelo ícone), permissão não negada e este aparelho sem
  inscrição. "Ativar" pede a permissão direto do toque; "Agora não" esconde por **30 dias**
  neste aparelho (`localStorage` `portal-faixa-avisos-ate`).
- **Por quê 30 dias:** o convite tem de voltar um dia (quem disse "agora não" pode mudar de
  ideia, e o mural é onde a pessoa está), mas raramente o bastante para não virar cobrança.
  Também aparece no Android sem instalar (o push funciona no navegador), não só instalado.

## 14. Revisão de código: o que mudou
- **SSRF** (bloqueava): o endpoint é validado pelo mesmo parser do envio (urllib3) e pelo
  `urlsplit`, e só aceita caracteres de URL, sem `\`, espaço, `%`, `@` ou porta no host. O
  envio revalida cada endpoint antes do POST. Host em maiúsculas continua aceito (o teste de
  contrato `maiusculas` já aceitava, e os dois parsers baixam para minúsculas); recusadas as
  variantes de ataque em maiúsculas.
- **Prazo por destino:** conferido antes de cada POST, com tempo limite `(5, 5)`; o pior caso
  passa do prazo comum em ~10 s (240 + 10 < 300).
- **Trava das inscrições mortas:** em vez de commitar por lote (o contrato diz que `enviar` não
  faz commit em `db`), as mortas são apagadas num DELETE só, no fim do envio: a trava dura só
  até o commit de quem chama, logo depois. Fica aberta a transação de leitura do
  `destinos_push` durante o envio (sem trava de linha).
- **Teste com o pywebpush de verdade** em modo curl, em `tmp_path` (o modo curl grava
  `encrypted.data` na pasta atual; o arquivo que tinha ficado em `api/` foi apagado).

## 15. Admin fictício do `dados_ficticios`
- Existe: em local e teste, a **primeira unidade sorteada** e ativada pelo comando vira admin
  (e as duas seguintes, Comissão). Não é a 1101 (essa é a do `conftest.py` dos testes). Na
  conferência visual deste épico, foi a 1-002.
