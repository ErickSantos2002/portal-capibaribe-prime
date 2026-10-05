# Dúvidas e decisões do M1 · Onda 1 (contrato)

Decisões tomadas sem perguntar a ninguém durante a onda do contrato. Cada item: a dúvida, o que
foi decidido e por quê. **[Erick]** marca o que só o Erick pode confirmar (regra do condomínio
ou preferência dele); o resto é decisão técnica que pode ser revista na revisão do marco.

Os agentes dos épicos registram as próprias dúvidas em `duvidas-m1-acesso.md`,
`duvidas-m1-administracao.md` e `duvidas-m1-avisos.md` (um arquivo por épico, para não dar
conflito).

## 1. `SameSite=Lax`, não `Strict`
- **Dúvida:** o pedido era "SameSite adequado". `Strict` é mais forte.
- **Decisão:** `Lax`, como manda a ADR-0005, mais o cabeçalho `X-Portal: 1` em toda alteração.
- **Por quê:** a ADR já decidiu e a defesa contra CSRF é o cabeçalho, não o `SameSite`. `Strict`
  funcionaria para o app (a página não precisa do cookie, só as chamadas `/api`, que são do
  mesmo site), mas trocar exigiria rever a ADR por um ganho pequeno.

## 2. Cookie `__Host-sessao`
- **Decisão:** nome com o prefixo `__Host-` (exige `Secure`, `Path=/` e nenhum `Domain`).
- **Por quê:** impede que um subdomínio ou uma resposta sem `Secure` sobrescreva a sessão. Foi
  conferido no Chrome: em `http://localhost` (contexto seguro) o cookie funciona, então o
  desenvolvimento local não muda. Os testes usam `https://testserver`, porque o cliente HTTP do
  teste não devolve cookie `Secure` por `http://`.

## 3. Coluna nova `aviso.publicado_como`
- **Dúvida:** H-12 pede "Publicado pela Comissão", mas o modelo de dados não diz como saber com
  que papel o aviso foi assinado.
- **Decisão:** coluna `publicado_como` (enum `papel`), gravada na publicação: `comissao` se a
  unidade tem esse papel, senão `admin`, `sindico`, `conselho`. A tela mostra "Comissão",
  "Administração do Portal", "Síndico" ou "Conselho".
- **Por quê:** o papel da unidade muda (H-09, RN-06); deduzir na hora de mostrar faria um aviso
  antigo da Comissão virar "Administração" quando o papel fosse retirado. Atualizar o
  `04-modelo-de-dados.md` ao fechar o marco.

## 4. Tema começa no claro
- **Dúvida:** a página do M0 seguia o tema do aparelho (`prefers-color-scheme`); o protótipo
  começa no claro.
- **Decisão:** igual ao protótipo: claro até a pessoa tocar no botão sol/lua; a escolha fica no
  `localStorage` (`portal-tema`). `public/tema.js` aplica a escolha antes do React, sem script
  embutido (a CSP proíbe).
- **Por quê:** o protótipo registrou que o escuro automático confundiu quem testava.

## 5. Sessão restrita e renovação
- **Decisão:** sem coluna nova em `sessao`. "Restrita" é `unidade.precisa_trocar_senha`, lida a
  cada requisição; a validade é `ultimo_uso_em` + 180 dias, regravado no máximo de hora em hora
  (e o cookie junto).
- **Por quê:** concluir o primeiro acesso libera a mesma sessão na hora, sem trocar token; e
  gravar no banco a cada requisição gastaria Neon à toa.

## 6. Celular só com dígitos e regras de contato no banco
- **Decisão:** o banco exige celular com 10 ou 11 dígitos, nome de 1 a 100 sem espaços nas
  pontas, e-mail minúsculo com `@`, e responsável + celular obrigatórios depois de ativar. Os
  dados fictícios passaram a gravar `8190000xxxx`.
- **Por quê:** um formato só simplifica painel, busca e comparação; RF-04 ("obrigatório após
  ativar") vira garantia do banco.
- **Atenção:** a migração valida as linhas existentes. O banco local `portal_dev` antigo (com
  `(81) 90000-…`) precisa ser recriado. Em produção ninguém ativou ainda; **[Erick]** conferir
  antes de rodar a 0002 no Neon: `select count(*) from unidade where ativada_em is not null`
  deve dar 0.

## 7. "Apagar meus dados" com papel de gestão
- **Dúvida:** H-06 manda a unidade voltar a "não ativada" com `mudar123`. E se ela for da
  Comissão ou o admin?
- **Decisão:** a API recusa (409 `unidade_com_papel_de_gestao`) e pede para a administração
  retirar o papel antes.
- **Por quê:** uma conta de gestão com a senha que todo mundo conhece seria tomada por quem
  conhece o padrão, e publicaria em nome da Comissão. **[Erick]** confirmar.

## 8. Trocar a senha desconecta os outros aparelhos (revisto)
- **Decisão original:** manter as outras sessões (a conta é da família).
- **Revista pelo coordenador, na revisão independente:** trocar a senha **encerra todas as
  outras sessões** e abre uma nova para quem trocou, igual ao primeiro acesso.
- **Por quê:** na conta compartilhada, trocar a senha é justamente o jeito de tirar quem não
  devia estar lá; o incômodo de a família entrar de novo vale menos que isso. O banco garante
  mesmo que a rota esqueça (item 29).

## 9. Painel e histórico só para o admin
- **Dúvida:** a tabela de permissões (requisitos, seção 2) diz que a Comissão vê os contatos das
  unidades; H-07 e H-11 são "Como Erick" e o protótipo mostra "Unidades" só para o admin.
- **Decisão:** todas as rotas `/api/admin/*` com `exige_admin`.
- **Por quê:** é o mais restritivo (LGPD) e bate com o protótipo e o histórico ("só o
  administrador vê"). Abrir o painel para a Comissão depois é trocar uma dependência.
  **[Erick]** confirmar.

## 10. Papel só para unidade já ativada; só `comissao` e `admin` no M1
- **Decisão:** `PUT …/papeis/{papel}` responde 409 se a unidade não entrou ainda; `papel` aceita
  `comissao` e `admin` (síndico e conselho entram com a E2). **Revisão:** a regra também está no
  banco (restrição `papel_em_unidade_ativada`), e unidade com papel em vigor não pode ser
  desativada nem voltar a "não ativada" (`unidade_com_papel`).
- **Por quê:** mesmo motivo do item 7, e não adivinhar a E2.

## 11. Rotas que não estão nos documentos
- **Decisão:** além das histórias, o contrato tem `GET /api/avisos/alcance` (a contagem da
  prévia de H-12 não pode ser 64 × blocos fixo, porque blocos e unidades são editáveis),
  `GET /api/avisos/nao-lidos` (número na aba, como no protótipo) e `PUT /api/avisos/{id}/fixado`
  (sem desafixar, o topo do mural só cresceria).
- **Por quê:** sem elas, as telas do protótipo não fecham.

## 12. Leitura do aviso por `POST /api/avisos/{id}/lido` (revisto)
- **Decisão original:** o próprio `GET /api/avisos/{id}` gravava a leitura.
- **Revista na revisão independente:** `GET` não altera nada; a tela chama
  `POST /api/avisos/{id}/lido` (204, idempotente, a primeira vez conta) ao abrir o aviso.
- **Por quê:** com `SameSite=Lax`, uma navegação vinda de outro site leva o cookie e escaparia
  do `X-Portal`: qualquer site poderia marcar avisos como lidos por quem estivesse logado.

## 13. "Lido por X de Y": Y são as unidades ativas do destino
- **Decisão:** `total` = unidades `ativa = true` dos blocos do destino, inclusive as que ainda
  não entraram no Portal (como o protótipo: "214 de 320").
- **Por quê:** mostra o alcance real do aviso e serve à meta do roadmap ("lido por metade").
  Contar só as ativadas inflaria o percentual.

## 14. Aviso de outro bloco: 404 para a unidade, visível para a gestão
- **Decisão:** a unidade comum recebe 404 (igual a aviso inexistente); a gestão vê todos.
- **Por quê:** não revelar que existe; a gestão precisa corrigir e conferir leitura de qualquer
  aviso.

## 15. Arquivar é para sempre, e arquivado não se corrige
- **Decisão:** o banco recusa `arquivado_em` voltar a nulo; a API recusa corrigir ou fixar
  aviso arquivado (409 `aviso_arquivado`).
- **Por quê:** H-15 não prevê desarquivar; "Avisos arquivados" é o registro do que saiu do
  mural. Se precisar, desarquivar vira regra nova.

## 16. Versões de aviso: o banco confere, a aplicação numera
- **Decisão:** a aplicação manda `versao = max + 1`; um trigger recusa qualquer outro número.
  Duas correções ao mesmo tempo: a segunda falha pela PK (o épico C traduz para 409).
- **Por quê:** gerar a versão no banco complicaria a PK composta no SQLAlchemy; conferir dá a
  mesma garantia.

## 17. Datas carimbadas pelo banco
- **Decisão:** `aviso.publicado_em`, `aviso.arquivado_em`, `aviso_versao.criada_em`,
  `aviso_leitura.lido_em`, `unidade_papel.concedido_em` e `retirado_em` ignoram o valor mandado
  pela aplicação. O `app` só altera `retirado_em`/`retirado_por` em `unidade_papel` e
  `fixado`/`arquivado_em` em `aviso` (GRANT por coluna).
- **Por quê:** fecha a dúvida 20 do M0 (datas como prova) e impede reescrever o que foi
  publicado mesmo com bug na API.

## 18. Último admin: trava no trigger (revisto)
- **Decisão original:** `pg_advisory_xact_lock` antes de contar os admins. A revisão mostrou que
  isso só vale em READ COMMITTED: em REPEATABLE READ, a segunda transação espera a trava mas
  enxerga o retrato antigo e deixa o Portal sem admin.
- **Agora:** `select … for update` nas outras linhas de admin em vigor. READ COMMITTED: a
  segunda espera, relê e é recusada. REPEATABLE READ: erro de serialização. Às vezes as duas se
  travam mutuamente (cada uma já tem a própria linha) e o Postgres desfaz uma delas como
  impasse, depois de ~1 s. Em todos os casos sobra um admin; testado nos dois níveis.

## 19. Formato de erro próprio, mas 404/405 do Starlette intactos
- **Decisão:** erros previstos e de validação viram `{codigo, mensagem}`; rota inexistente
  continua `{"detail": "Not Found"}`.
- **Por quê:** a rota de diagnóstico do M0 precisa continuar idêntica a uma rota que não existe.
  O 422 próprio também evita que a senha digitada volte na resposta (o padrão do FastAPI
  devolve o `input`).

## 20. Rotas `eu` e `sair` no arquivo comum
- **Decisão:** `GET /api/acesso/eu` e `POST /api/acesso/sair` estão em `app/rotas/sessao.py`
  (comum), não no épico A.
- **Por quê:** a casca do front depende delas para escolher rota e menu; os épicos B e C não
  podem esperar o A para testar as telas.

## 21. Bibliotecas novas no front
- **Decisão:** `react-router` 8 (dependência) e `vitest`, `jsdom`, `@testing-library/react`,
  `@testing-library/dom` (só desenvolvimento). Justificativa no spec, seção 5.1.
- **Observação:** a v8 do React Router saiu depois da base de conhecimento do agente; a API foi
  conferida na documentação atual (context7): `react-router-dom` não existe mais e o
  `RouterProvider` vem de `react-router/dom`.

## 22. A casca usa uma função do épico C
- **Decisão:** a aba "Avisos" mostra os não lidos chamando `contarNaoLidos` de
  `web/src/avisos/api.ts`. Enquanto a rota não existe, a chamada falha e a aba fica sem número.
- **Por quê:** o número é da casca (menu), mas a rota é de avisos. O épico C não pode renomear
  essa função (está anotado no arquivo).

## 23. Prévias da Vercel com um branch `previa` do Neon
- **Decisão e motivo:** no spec, seção 6. Os dados fictícios agora aceitam
  `PORTAL_AMBIENTE=previa`. **Nada foi executado** na Vercel nem no Neon. **[Erick]** criar o
  branch e a variável quando quiser prévias com banco, e conferir que a *Deployment
  Protection* está ligada para as prévias (item 28).

## 24. Apoio para os testes dos épicos
- **Decisão:** fixtures `predio` (prédio inteiro, 1101 admin, 2304 Comissão, 1203 comum
  ativadas com senha `senha-<login>`, 4203 não ativada; o admin é dado pela própria fixture,
  depois de ativar, como `promover_admin` faz em produção) e `logar(login)` (cliente já com sessão
  e `X-Portal: 1`), `hasher_rapido` automático e banco de teste por `PORTAL_TESTE_BANCO`.
- **Por quê:** cada épico testa as próprias rotas sem depender da rota de entrar (épico A) e sem
  apagar o banco de teste dos outros agentes.

## 25. Busca sem acento fica com o épico C
- **Decisão:** o contrato exige "fundacao" achar "Fundação", mas não diz como. A extensão
  `unaccent` do Postgres exigiria migração nova; com ~300 avisos, filtrar no Python também
  serve. Fica com o épico C (sem migração nova sem o coordenador).

## 26. Aviso do Chrome sobre `Permissions-Policy`
- **Observação:** o Chrome avisa "Unrecognized feature: 'bluetooth'" no cabeçalho do M0. É só
  aviso (o recurso é ignorado). Não mexi no `vercel.json` nesta onda; dá para tirar `bluetooth`
  da lista numa limpeza futura.

## 27. Limite do texto do aviso
- **Decisão:** título até 120 caracteres (como o `maxlength` do protótipo) e texto até 10.000.
- **Por quê:** o modelo não dá limite; 10.000 cabe em qualquer aviso real e impede abuso.

---

## Revisão independente (05/10/2026)

Itens novos ou mudados depois da revisão. Os itens 8, 10, 12, 18, 23 e 24 acima também foram
atualizados.

## 28. Prévia: proteção da Vercel, e sem papel fictício
- **Dúvida:** a semente fictícia em `previa` criava unidades da Comissão com `mudar123` sem troca
  obrigatória, num endereço da internet.
- **Decisão:** a prévia só existe com a *Deployment Protection* da Vercel ligada (registrado no
  spec, seção 6), e a semente **não dá papel nenhum** em `previa` (em `local` e `teste` dá um
  admin e duas Comissões). Quem revisa faz o primeiro acesso numa unidade não ativada e roda
  `promover_admin`, o mesmo caminho de produção.
- **Por quê:** exigir a troca de senha das unidades fictícias atrapalharia a revisão sem ganho
  (os dados são inventados); o que importava era não ter conta de gestão com senha conhecida.
  **[Erick]** conferir a proteção ao criar as prévias com banco.

## 29. Sessão de antes da troca de senha morre no banco
- **Problema (crítico):** quem entrava com `mudar123` antes do morador guardava um cookie que
  virava sessão completa de 180 dias quando o morador concluía o primeiro acesso.
- **Decisão:** duas camadas.
  1. **Banco:** `unidade.senha_trocada_em` (data do banco, muda sozinha quando o hash muda) e
     `sessao.criada_em` carimbada pelo banco; a sessão só vale se foi criada depois da última
     troca. Vale para primeiro acesso, troca de senha, reset e "apagar meus dados", mesmo que a
     rota do épico esqueça de encerrar as sessões.
  2. **Aplicação:** `trocar_senha_e_sessao()` grava o hash, encerra todas as sessões (ficam
     marcadas como encerradas, somem da lista de aparelhos) e abre uma nova para quem trocou.
- **Por quê:** o coordenador pediu `encerrar_todas(..., exceto=sessão atual)`. Reaproveitar a
  sessão atual depois de trocar a senha manteria o token que já existia antes (o de quem estava
  com `mudar123`); trocar por um token novo fecha também esse caso (fixação de sessão).

## 30. Carga sem admin e comando `promover_admin`
- **Problema (alto):** a carga do M0 dava `admin` à unidade de `PORTAL_ADMIN_UNIDADE`, que
  nasce com `mudar123`: em produção, quem conhecesse o padrão e a unidade do Erick virava admin.
- **Decisão:** a carga não dá papel nenhum; `PORTAL_ADMIN_UNIDADE` foi removida (carga, CI,
  `.env.example`). O admin nasce com `python -m app.comandos.promover_admin <login>` (recusa
  unidade não ativada, idempotente, registra `papel_concedido` com `origem: promover_admin`).
  A 0002 retira o papel que a carga do M0 já deu, com registro no histórico.
- **[Erick]** em produção, depois do deploy do M1: fazer o primeiro acesso na unidade dele e
  rodar `promover_admin` (spec, seção 2.5). Até isso, o Portal fica sem administrador, o que é
  esperado.

## 31. A 0002 foi editada no lugar
- **Decisão:** as correções de banco da revisão entraram na própria `0002`, não numa `0003`.
- **Por quê:** a 0002 ainda não rodou em produção nem no banco das prévias (mesma regra da
  dúvida 19 do M0). A partir do primeiro `upgrade` fora daqui, toda mudança vira migração nova.

## 32. CHECK do modelo comparado pelo próprio Postgres
- **Problema:** o CHECK de e-mail do modelo era diferente do da migração, e o teste de modelos
  não via (o autogenerate do Alembic não compara CHECK).
- **Decisão:** `test_checks_dos_modelos_iguais_aos_da_migracao` cria um banco só com
  `create_all` dos modelos e compara `pg_get_constraintdef` de todos os CHECK com o banco
  migrado. Para isso, os CHECK da 0001 e os do `aviso_versao` ganharam nome no modelo (e os do
  `aviso_versao`, nome explícito na migração).

## 33. Contrato compara tipos, nulo e opcional
- **Decisão:** `test_contrato.py` compara, para cada campo, o tipo básico, se aceita `null` e
  se é opcional. Conferido por mutação (`email: string | null` → `string` e
  `bloco: number` → `string` falham). Achou uma diferença real: `confirmo` era `true` no TS e
  `bool` no Python; o TS passou a `boolean` (a API continua recusando o que não for `true`).
- **Por quê de não gerar do OpenAPI:** geraria um arquivo único de tipos, que os três épicos
  editariam ao mesmo tempo (conflito garantido); a comparação mantém um arquivo por épico.

## 34. "Sair" só esquece a sessão com 204 ou 401
- **Decisão:** se `POST /api/acesso/sair` falhar de outro jeito (sem internet, 500), a casca
  mantém a pessoa logada e a promessa de `sair()` é rejeitada com `ErroDaApi`; a tela do épico
  A mostra `erro.mensagem`.
- **Por quê:** dizer "saiu" com o cookie ainda válido no aparelho (num celular emprestado, por
  exemplo) seria mentir para a pessoa.
