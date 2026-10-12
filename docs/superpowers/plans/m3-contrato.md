# M3 Onda 1 · Contrato · Plano de implementação

> **Para agentes:** executar tarefa por tarefa, com TDD (`superpowers:test-driven-development`).
> Passos em checkbox (`- [ ]`). Execução nesta onda: o próprio agente do contrato, em sequência.

**Objetivo:** base do M3 pronta para três épicos em paralelo (A · documentos, B · anexos nos
avisos, C · proteção dos arquivos): migração 0007, camada de armazenamento (interface, R2 e
falsa), envio de arquivo com conferência do conteúdo no servidor, contrato da API (spec +
esquemas + tipos TS + rotas 501), configuração, CSP, verificações do backup e pontos de encaixe
no front que ainda não mudam nada para o morador. Decisão nova: ADR-0011.

**Arquitetura:** a API ganha `app/servicos/armazenamento.py` (interface `Armazenamento`,
`ArmazenamentoS3`, `ArmazenamentoFalso`, dependência `obter_armazenamento`),
`app/servicos/arquivos.py` (assinatura do conteúdo, pedir, confirmar, link),
`app/servicos/visibilidade.py` (quem vê qual nível de documento) e a rota comum
`app/rotas/arquivos.py`; um roteador para o épico A (`rotas/documentos.py`) e a rota do link
do anexo dentro de `rotas/avisos.py` (épico B). O front ganha `web/src/arquivos/` (comum,
pronto) e `web/src/documentos/` (épico A, encaixes vazios).

**Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2, Alembic, psycopg 3, `boto3` (novo; o mesmo
do `scripts/backup/s3.py`), pytest, `moto` (novo, só nos testes) · React 19, TypeScript, Vite
8, Vitest · Postgres 17.

**Spec:** `docs/superpowers/specs/m3-contrato.md`

## Restrições globais

- Python 3.12 via `uv run --frozen`; nunca o python3 do sistema.
- Textos, comentários e commits em PT-BR com acentuação; commit termina com o `Co-Authored-By`.
- Nenhum dado pessoal no repo; unidade de exemplo é sempre fictícia (1101, 1203, 2304...).
- Nenhuma chave real (R2, B2) no repo; o `gitleaks` roda no pre-commit.
- Banco de teste desta cópia: container próprio `portal-pg-m3-contrato` (porta 55473),
  `PORTAL_TESTE_BANCO=portal_teste_m3_contrato`; removido no fim.
- Sem push, sem merge, sem Vercel/Neon/R2. Versão do `web/package.json` e `novidades.ts`
  intactos.
- Nenhum teste fala com o R2 de verdade (falso em memória, ou `moto`).
- Commit pequeno a cada passo verde, com a suíte inteira (pytest, ruff, vitest, eslint, tsc) e
  `pre-commit run --all-files` antes.

## Foco de revisão

1. Um `.exe` renomeado para `.pdf` → 422 `arquivo_recusado`, o envio some do bucket, a linha
   some do banco, o histórico registra sem o nome. Teste na Tarefa 4.
2. A camada de armazenamento não consegue apagar nem sobrescrever nada em `arquivos/`. Teste
   na Tarefa 3.
3. Arquivo confirmado não muda nem é apagado pelo `app`; documento, versão e anexo não são
   apagados; anexo não entra numa versão já publicada. Teste na Tarefa 1.
4. Sem as variáveis de arquivos, o Portal funciona igual (503 só nas rotas de arquivo); a
   chave nunca aponta para o bucket de backups. Teste na Tarefa 2.
5. Toda rota nova de gestão recusa a unidade comum; as rotas de documento sem sessão só
   enxergam o nível `publico`. Teste na Tarefa 5.

---

### Tarefa 1: Migração 0007 e modelos

**Arquivos:** `api/migracoes/versions/0007_documentos_e_anexos.py`,
`api/app/modelos/{arquivos,documentos}.py`, `api/app/modelos/__init__.py`,
`api/testes/conftest.py` (TABELAS), `api/testes/test_migracoes.py`,
`api/testes/test_m3_banco.py`, `api/testes/test_permissoes.py`,
`scripts/backup/verificacoes.sql`.

- [x] Testes falhando: tabelas novas existem após upgrade e somem no downgrade para 0006 sem
  deixar função; funções de trigger com `search_path` fixo; arquivo: chave hexadecimal única,
  nome sem barra nem controle, só os 4 tipos, 10 MB no aviso e 20 MB no documento, datas do
  banco, confirmado não muda nem é apagado, pendente pode ser corrigido e apagado, 50 por dia
  por unidade (contando os recusados do histórico); documento: categorias, níveis, data na faixa, completo no commit (versão 1),
  arquivado não volta, aviso automático só de documento visível às unidades; versão em
  sequência, arquivo confirmado e de finalidade documento, único, não arquivado; anexo:
  confirmado, de finalidade aviso, até 5, mesmo aviso pode repetir na correção, outro aviso
  não, só na transação da versão; `app` não apaga documento, versão nem anexo, não muda
  título/acesso; as verificações do backup conhecem as tabelas novas;
  `test_modelos_iguais_ao_banco_migrado` e o teste de CHECKs continuam verdes.
- [x] Implementar a migração (SQL à mão) e os modelos `Arquivo`, `Documento`,
  `DocumentoVersao`, `AvisoAnexo` (+ constantes de tipos, limites, categorias e níveis).
- [x] Commit.

### Tarefa 2: Configuração e dependências

**Arquivos:** `api/app/configuracao.py` (`ConfigArquivos`, `config_arquivos`),
`api/.env.example`, `api/pyproject.toml` e `api/uv.lock` (+ `boto3`; `moto` no grupo dev),
`api/testes/test_m3_configuracao.py`.

- [x] Testes falhando: sem variáveis, desligado sem aviso; pela metade, desligado com aviso que
  não mostra a chave; endpoint só `https://` ou máquina local; bucket com "backup" no nome
  desliga; nome de bucket fora do padrão S3 desliga; segredo fora do `repr`; região padrão
  `auto`.
- [x] Implementar; commit.

### Tarefa 3: Camada de armazenamento

**Arquivos:** `api/app/servicos/armazenamento.py`, `api/testes/test_m3_armazenamento.py`,
`api/testes/conftest.py` (fixture `armazenamento`).

**Produz:** `UrlAssinada`, `Armazenamento` (Protocol), `ArmazenamentoS3`,
`ArmazenamentoFalso` (`receber`, `objetos`), `obter_armazenamento`, `VALIDADE_ENVIO`,
`VALIDADE_LEITURA`, `nome_para_baixar`.

- [x] Testes falhando (contra o `moto` e contra o falso, os mesmos casos): URL de envio é PUT
  em `envios/<chave>` com o Content-Type e o Content-Length assinados e 10 minutos; URL de leitura é GET em
  `arquivos/<chave>`, 5 minutos, com tipo e `Content-Disposition` forçados (inline/attachment,
  nome UTF-8 e reserva ASCII, extensão acrescentada); tamanho e ETag do envio (None se não
  chegou); início do envio com Range e If-Match; publicar copia com o tipo novo, só com o
  mesmo ETag, e é idempotente (mesmo ETag já publicado); publicar por cima de `arquivos/` com
  outro conteúdo falha (trava); erros do boto3 viram `FalhaNoArmazenamento`; descartar só mexe em `envios/`; chave fora do
  formato é recusada antes de qualquer chamada; `obter_armazenamento` devolve `None` sem
  configuração.
- [x] Implementar; commit.

### Tarefa 4: Envio de arquivo (rotas comuns prontas)

**Arquivos:** `api/app/servicos/arquivos.py`, `api/app/esquemas/arquivos.py`,
`api/app/rotas/arquivos.py`, `api/app/main.py`, `api/app/servicos/historico.py`
(`arquivo_recusado` e as ações de documento), `api/app/servicos/visibilidade.py`,
`api/testes/test_m3_arquivos.py`, `api/testes/test_contrato.py`, `web/src/arquivos/tipos.ts`,
`web/src/administracao/frases.ts` (+ teste).

**Produz:** `tipo_pelo_conteudo`, `pedir_envio`, `confirmar_envio`, `arquivo_utilizavel`,
`link_do_arquivo`, `niveis_que_ve`; `POST /api/arquivos`, `POST /api/arquivos/{id}/confirmar`.

- [x] Testes falhando: assinaturas dos 4 tipos e recusa do resto (MZ, ZIP, HTML, SVG, vazio,
  curto); pedir cria pendente e devolve PUT com Content-Type, 503 sem armazenamento, 422 para
  tipo, tamanho e nome, unidade comum 403, sem X-Portal 403; confirmar publica e devolve o
  tamanho real; `.exe` como `.pdf` → 422, envio e linha apagados, histórico sem nome; maior que o
  limite de verdade → 422 e apagado; PNG declarado JPEG → aceito como PNG; não chegou → 409 e
  continua pendente; de outra unidade → 404; confirmar de novo → mesmo resultado; pendente
  velho é apagado no pedido seguinte; 51º do dia → 409; `arquivo_utilizavel` e `niveis_que_ve`.
- [x] Implementar; commit.

### Tarefa 5: Contrato das rotas dos épicos (501) e campos novos dos avisos

**Arquivos:** `api/app/esquemas/documentos.py`, `api/app/rotas/documentos.py`,
`api/app/esquemas/avisos.py` (anexos, `quantidade_anexos`, `documento`, `DocumentoDoAviso`),
`api/app/servicos/avisos.py` (`gravar_publicacao`, campos novos, `documento` do aviso),
`api/app/rotas/avisos.py` (link do anexo; 501 com anexos), `api/app/seguranca/dependencias.py`
(`SessaoOpcional`), `api/app/main.py`, `api/testes/test_m3_rotas.py`,
`api/testes/test_m3_em_construcao.py`, `api/testes/test_avisos_permissoes.py`,
`api/testes/test_cache.py`, `api/testes/test_contrato.py`, `web/src/documentos/tipos.ts`,
`web/src/avisos/tipos.ts` (+ objetos de teste do front que montam avisos).

- [x] Testes falhando: rotas do M3 declaradas; gestão recusa comum, restrita e sem sessão;
  leitura recusa restrita e sem sessão; públicas não exigem sessão; CSRF; validação dos corpos
  (título, categoria, data, acesso, avisar com gestão); 501 em cada rota do épico; aviso com
  anexos → 501, sem anexos igual ao M1; aviso aberto traz `anexos: []`,
  `quantidade_anexos: 0` e o `documento` que o gerou só para quem pode ver e se não arquivado;
  `gravar_publicacao` não faz commit; contrato TS igual.
- [x] Implementar; commit.

### Tarefa 6: Front comum, encaixes e CSP

**Arquivos:** `web/src/arquivos/{api,limites,comprimir,enviar}.ts` (+ `arquivos.test.ts`),
`web/src/documentos/{api.ts,rotas.tsx,menu.ts,LinkDocumentosPublicos.tsx,DocumentoDoAviso.tsx}`,
`web/src/rotas.tsx`, `web/src/casca/menu.ts`, `web/src/acesso/Entrar.tsx`,
`web/src/avisos/AvisoAberto.tsx`, `web/src/m3contrato.test.ts`, `vercel.json`,
`web/testes/cabecalhos.test.ts`.

- [x] Testes falhando: limites e tipos iguais aos da API; dimensões reduzidas a 1920 px no lado
  maior, sem aumentar; decisão de comprimir (só imagem; resultado maior → original); nome com
  a extensão nova; `enviarArquivo` recusa na tela tipo e tamanho, pede, faz o PUT sem
  `X-Portal` e sem cookie com o Content-Type devolvido, confirma, e transforma falha do PUT em
  `arquivo_nao_chegou`; funções de API dos documentos e dos anexos chamam a rota certa; os
  encaixes não mostram nada (menu sem Documentos, entrada sem link, aviso sem botão); a CSP
  libera o R2 só em `connect-src` e `img-src` (e `blob:` na imagem).
- [x] Implementar; commit.

### Tarefa 7: Documentos e dúvidas

**Arquivos:** `docs/04-modelo-de-dados.md`, `docs/05-arquitetura.md`, `docs/07-roadmap.md`,
`README.md`, `docs/superpowers/duvidas-m3.md`.

- [x] Modelo de dados com as colunas e regras novas; arquitetura (fluxo 6.2 com as rotas de
  arquivo, CSP, backup dos arquivos, ADR-0011); roadmap (estado do M3); README (variáveis);
  dúvidas com os itens **[Erick]** e o passo a passo do R2 e do B2.
- [x] Suíte inteira e `pre-commit run --all-files`; commit.

---

## Estado (12/10/2026, onda do contrato concluída)

Tarefas 1 a 7 feitas e commitadas na branch `m3/contrato` (sem push, sem merge). A suíte
inteira roda verde no último commit; contagens no relatório do agente e no `git log`.

Na retomada de 12/10:
- A suíte inteira acusou um teste antigo que não conhecia o campo `quantidade_anexos` da Tarefa
  5 (`test_avisos_mural.py::test_item_do_mural`); corrigido em commit próprio.
- Tarefa 6 em três commits: envio comum (`web/src/arquivos/`, com os limites conferidos contra
  a API no `test_contrato.py`), funções de API dos documentos e do link do anexo
  (`avisos/api.ts`, `linkDoAnexo`) e encaixes do épico A ligados mas vazios, e a CSP.
- Tarefa 7: docs 04/05/07, README e `docs/superpowers/duvidas-m3.md` (12 itens e o passo a
  passo do Erick para R2, B2, GitHub e Vercel). A spec perdeu o campo `metodo` do
  `EnvioAutorizado`, que o código nunca teve (dúvida 11).

Correções da revisão do contrato (12/10, duas revisões independentes, um commit por achado,
cada um com teste de regressão que falhava antes):
- URL de envio assina o `Content-Length` (o falso recusa PUT de outro tamanho).
- Publicação presa ao ETag do HEAD (`If-Match` na leitura, `CopySourceIfMatch` na cópia);
  conteúdo trocado no meio ou tamanho diferente do declarado → 409, pendente (dúvida 13). A
  interface trocou `tamanho_do_envio` por `envio_recebido` (tamanho + ETag).
- Publicar é idempotente (mesmo ETag já publicado conta como publicado), apagar o envio é
  faxina depois do commit, e erros do boto3 viram `FalhaNoArmazenamento` (503
  `armazenamento_indisponivel`) ou 409, nunca 500.
- O limite de 50 por dia conta os `arquivo_recusado` do histórico (trigger da própria 0007, que
  ainda não foi aplicada em lugar nenhum: não está na `main` nem no Neon).
- Endpoint do R2 com `/<bucket>` no fim é aceito (dúvida 14).
- Front: foto pequena acima do limite do destino é regravada (fundo branco no JPEG); PUT com
  tempo limite (`prazoDoEnvio`).
- Docs: dúvida 8 (CSP) virou **[Erick]**; passo a passo do Erick revisado contra a
  documentação oficial (envio de teste movido para depois do deploy, tetos do B2, segredos do
  GitHub só depois do épico C, clipboard); ADR-0011 diz que a chave do B2 ainda esconde
  arquivo (recuperável).

Próximo passo (coordenador): respostas do Erick aos itens **[Erick]** de `duvidas-m3.md` (3, 5,
8, 9 e o passo a passo) e a onda dos três épicos, cada um na própria worktree a partir desta
branch, com o próprio banco de teste.
