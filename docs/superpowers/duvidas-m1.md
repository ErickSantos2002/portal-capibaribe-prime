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

## 8. Trocar a senha não desconecta os outros aparelhos
- **Decisão:** `PUT /api/minha-unidade/senha` mantém as outras sessões.
- **Por quê:** a conta é da família; trocar a senha no celular de um não deveria tirar o outro.
  Para tirar alguém, existe "desconectar aparelho". **[Erick]** confirmar.

## 9. Painel e histórico só para o admin
- **Dúvida:** a tabela de permissões (requisitos, seção 2) diz que a Comissão vê os contatos das
  unidades; H-07 e H-11 são "Como Erick" e o protótipo mostra "Unidades" só para o admin.
- **Decisão:** todas as rotas `/api/admin/*` com `exige_admin`.
- **Por quê:** é o mais restritivo (LGPD) e bate com o protótipo e o histórico ("só o
  administrador vê"). Abrir o painel para a Comissão depois é trocar uma dependência.
  **[Erick]** confirmar.

## 10. Papel só para unidade já ativada; só `comissao` e `admin` no M1
- **Decisão:** `PUT …/papeis/{papel}` responde 409 se a unidade não entrou ainda; `papel` aceita
  `comissao` e `admin` (síndico e conselho entram com a E2).
- **Por quê:** mesmo motivo do item 7, e não adivinhar a E2.

## 11. Rotas que não estão nos documentos
- **Decisão:** além das histórias, o contrato tem `GET /api/avisos/alcance` (a contagem da
  prévia de H-12 não pode ser 64 × blocos fixo, porque blocos e unidades são editáveis),
  `GET /api/avisos/nao-lidos` (número na aba, como no protótipo) e `PUT /api/avisos/{id}/fixado`
  (sem desafixar, o topo do mural só cresceria).
- **Por quê:** sem elas, as telas do protótipo não fecham.

## 12. Abrir o aviso marca como lido (no próprio `GET`)
- **Decisão:** `GET /api/avisos/{id}` grava a leitura (`on conflict do nothing`).
- **Por quê:** H-16 diz "conta como leu quando abre o aviso"; uma rota separada seria uma
  chamada a mais que a tela poderia esquecer. O `GET` só insere uma linha idempotente.

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

## 18. Último admin: trava no trigger
- **Decisão:** `pg_advisory_xact_lock` antes de contar os admins; testado com duas conexões
  retirando um admin cada uma ao mesmo tempo (uma passa, a outra é recusada).
- **Por quê:** sem a trava, as duas transações veriam "ainda tem outro admin" e o Portal ficaria
  sem nenhum.

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
  branch e a variável quando quiser prévias com banco.

## 24. Apoio para os testes dos épicos
- **Decisão:** fixtures `predio` (prédio inteiro, 1101 admin, 2304 Comissão, 1203 comum
  ativadas com senha `senha-<login>`, 4203 não ativada) e `logar(login)` (cliente já com sessão
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
