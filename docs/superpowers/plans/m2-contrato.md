# M2 Onda 1 · Contrato · Plano de implementação

> **Para agentes:** executar tarefa por tarefa, com TDD (`superpowers:test-driven-development`).
> Passos em checkbox (`- [ ]`). Execução nesta onda: o próprio agente do contrato, em sequência.

**Objetivo:** base do M2 pronta para dois épicos em paralelo (A · push e PWA, B · e-mail):
migração 0005, configuração por variável de ambiente, peça comum "notificar a publicação" com o
envio depois da resposta, contrato da API (spec + esquemas + tipos TS + rotas 501) e pontos de
encaixe no front que ainda não mudam nada para o morador.

**Arquitetura:** a API ganha `app/configuracao.py`, `app/servicos/segundo_plano.py` e
`app/servicos/notificacoes.py` (comuns), um arquivo por canal (`servicos/push.py` do épico A,
`servicos/email.py` do épico B, os dois desligados), um roteador por épico
(`rotas/push.py`, `rotas/recuperacao.py`) e a rota comum `rotas/envios.py`. O front ganha
`web/src/notificacoes/` e `web/src/recuperacao/`, ligados às telas do M1 por funções e
componentes que hoje não fazem nada.

**Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2, Alembic, psycopg 3, `pywebpush`, `vercel`
(SDK Python, `wait_until`), pytest · React 19, TypeScript, Vite 8, Vitest · Postgres 17.

**Spec:** `docs/superpowers/specs/m2-contrato.md`

## Restrições globais

- Python 3.12 via `uv run --frozen`; nunca o python3 do sistema.
- Textos, comentários e commits em PT-BR com acentuação; commit termina com o `Co-Authored-By`.
- Nenhum dado pessoal no repo; unidade de exemplo é sempre fictícia (1101, 1203, 2304...).
- Nenhuma chave real (VAPID, senha de app) no repo; o `gitleaks` roda no pre-commit.
- Banco de teste desta cópia: `PORTAL_TESTE_BANCO=portal_teste_m2_contrato` (container
  `portal-pg-m0`).
- Sem push, sem merge, sem Vercel/Neon. Versão do `web/package.json` e `novidades.ts` intactos.
- Nenhum teste fala com o Gmail ou com um serviço de push de verdade.

## Foco de revisão

1. Sem as variáveis de ambiente, publicar aviso continua igual ao M1 → envios `desligado`, nada
   quebra. Teste na Tarefa 3.
2. Duas execuções de `processar` para o mesmo aviso → o canal é chamado uma vez só. Teste na
   Tarefa 3.
3. Aviso para o Bloco 1 → nenhum aparelho nem e-mail do Bloco 2; os dois celulares do casal
   recebem. Teste na Tarefa 3.
4. Endpoint de push apontando para um endereço qualquer (`https://intranet.local/...`,
   `https://evil.com/?fcm.googleapis.com`, com usuário ou porta) → 422. Teste na Tarefa 4.
5. Token de recuperação usado depois de a senha mudar, depois de 1 hora, ou duas vezes → o banco
   recusa. Teste na Tarefa 1.

---

### Tarefa 1: Migração 0005 e modelos

**Arquivos:** `api/migracoes/versions/0005_notificacoes_e_recuperacao.py`,
`api/app/modelos/notificacoes.py`, `api/app/modelos/__init__.py`, `api/testes/conftest.py`
(TABELAS), `api/testes/test_migracoes.py`, `api/testes/test_m2_banco.py`.

- [x] Testes falhando: tabelas novas existem após upgrade e somem no downgrade para 0004 sem
  deixar função; funções de trigger com `search_path` fixo; inscrição carimba a data, uma por
  sessão, endpoint único, só formato Web Push, some quando a sessão é encerrada, recusada em
  sessão encerrada, no máximo 10 por unidade; `app` troca a sessão da inscrição e apaga, não
  muda endpoint nem data; token vale 1 hora contada pelo banco, só hash, só unidade ativada com
  e-mail, 3 por hora, 6 por dia, uso carimba a data e é único, vencido recusado, senha trocada
  depois do pedido recusa, usar e depois trocar a senha na mesma transação funciona, `app` não
  muda hash nem validade, `app` apaga token; envio único por aviso e canal, nasce pendente,
  situação só anda para a frente, contagens coerentes, `app` não apaga envio;
  `test_modelos_iguais_ao_banco_migrado` e o teste de CHECKs continuam verdes.
- [x] Implementar a migração (SQL à mão) e os modelos `InscricaoPush`, `TokenRecuperacao`,
  `NotificacaoEnvio` (+ enums `Canal`, `SituacaoEnvio`).
- [x] Commit.

### Tarefa 2: Configuração e chaves VAPID

**Arquivos:** `api/app/configuracao.py`, `api/app/comandos/gerar_chaves_vapid.py`,
`api/.env.example`, `api/pyproject.toml` e `api/uv.lock` (+ `pywebpush`, `vercel`),
`api/testes/test_m2_configuracao.py`.

**Produz:** `config_push() -> ConfigPush | None` (`chave_privada`, `chave_publica`, `contato`),
`config_email() -> ConfigEmail | None` (`usuario`, `senha_app`, `host`, `porta`, `url_base`,
`remetente_nome`), `url_base() -> str | None`, `limpar_cache()`; `gerar()`, `publica_de()`,
`main()` do comando.

- [x] Testes falhando: sem variáveis, tudo desligado; push ligado deriva a pública (87
  caracteres, igual à do `py_vapid`); pela metade ou inválido fica desligado com aviso no log
  que não mostra a chave; segredos fora do `repr`; e-mail com padrões do Gmail, pela metade
  desligado, porta inválida desliga; `url_base` só `https://` ou máquina local, sem caminho nem
  consulta; o comando gera um par que a configuração aceita e cada execução gera um par novo.
- [x] Implementar; commit.

### Tarefa 3: Notificar a publicação (peça comum)

**Arquivos:** `api/app/servicos/segundo_plano.py`, `api/app/servicos/notificacoes.py`,
`api/app/servicos/push.py` e `api/app/servicos/email.py` (lugares marcados, desligados),
`api/app/servicos/avisos.py` (`registrar_publicacao` antes do commit), `api/app/rotas/avisos.py`
(`agendar` depois de publicar), `api/app/rotas/envios.py`, `api/app/esquemas/comum.py`
(`EnvioDoAviso`, `EnviosDoAviso`), `api/app/main.py`, `web/src/api/tipos.ts`,
`api/testes/test_m2_notificacoes.py`, `api/testes/test_avisos_permissoes.py` (rota nova na lista
de gestão), `api/testes/test_contrato.py` (enums novos).

**Produz:** `agendar(tarefas, funcao, *args)`; `Enviador`, `AvisoParaNotificar`, `Resultado`,
`registrar_publicacao`, `agendar`, `processar`, `carregar_aviso`, `destinos_push`,
`destinos_email`, `emails_nas_ultimas_24h`, `cota_email_avisos`, `cota_email_recuperacao`;
`GET /api/avisos/{id}/envios`.

- [x] Testes falhando: publicar sem configuração deixa os dois envios `desligado`; com canais
  falsos ligados, o envio sai depois da resposta e grava as contagens; processar duas vezes chama
  cada canal uma vez; canal que cai fica `interrompido` com as contagens até ali, o outro segue,
  e o log não leva a mensagem do erro; canal desligado não é chamado; aviso arquivado antes não
  chama ninguém; pendente de outro aviso sai na próxima publicação; faxina interrompe o que está
  `enviando` há 11 minutos e o `pendente` de 25 horas; registrar duas vezes não duplica; push só
  para os aparelhos do bloco de destino (casal recebe nos dois), menos quem publicou, só sessão
  que vale (180 dias, senha trocada depois), unidade desativada não recebe; e-mail só para
  unidade do destino ativada com e-mail; cota de 450 com reserva de 50 (cópias tentadas + tokens);
  fora da Vercel usa `BackgroundTasks`, na Vercel usa `wait_until`; rota de envios para a gestão
  (ordem push, e-mail), 403 para a unidade comum, 404 para aviso inexistente, vazia para aviso
  sem registro.
- [x] Implementar; commit.

### Tarefa 4: Contrato da API dos épicos e encaixes no front

**Arquivos:** `api/app/esquemas/{push,recuperacao}.py`, `api/app/esquemas/acesso.py`
(`validar_login`, `Aparelho.notificacoes`), `api/app/servicos/acesso.py` (preenche
`notificacoes`), `api/app/rotas/{push,recuperacao}.py`, `api/app/erros_api.py`
(`em_construcao`), `api/app/main.py`, `api/app/servicos/historico.py` (ações do M2),
`api/testes/test_m2_rotas.py`, `api/testes/test_contrato.py`, `api/testes/test_minha_unidade.py`,
`web/src/notificacoes/*`, `web/src/recuperacao/*`, `web/src/acesso/{tipos.ts,Entrar.tsx,
PrimeiroAcesso.tsx,MinhaUnidade.tsx}` e os testes com `Aparelho`, `web/src/{main.tsx,rotas.tsx}`,
`web/src/administracao/frases.ts`, `web/src/m2contrato.test.ts`.

- [x] Testes falhando: rotas do M2 declaradas (e só elas); push exige sessão completa (401 e
  403 `primeiro_acesso_pendente`), CSRF e responde 501; endpoint só de serviços conhecidos
  (http, intranet, domínio parecido, consulta, usuário, porta, tamanho) e chaves no padrão;
  aceita Chrome, Firefox, Safari e Edge; aparelho em Minha unidade diz se recebe notificação;
  recuperação sem sessão chega na rota, exige `X-Portal`, valida login, token e senhas com as
  mensagens do primeiro acesso, sem devolver a senha; ações do M2 passam pelo filtro do
  histórico; `test_contrato` confere os tipos TS novos. Front: funções de API com rota, método,
  corpo e `X-Portal`; token no corpo; frases do histórico; encaixes sem efeito.
- [x] Implementar; `npm run lint`, `typecheck`, `test`; commit.

### Tarefa 5: CSP, ADR, dúvidas e verificação final

**Arquivos:** `web/testes/cabecalhos.test.ts`, `docs/adr/0010-envio-em-segundo-plano.md`,
`docs/adr/README.md`, `docs/superpowers/duvidas-m2.md`, este plano e o spec.

- [x] Teste da CSP: `worker-src` e `manifest-src` efetivos (cadeia de recuo da CSP 3) incluem
  `'self'`; nenhum endereço de terceiros. `vercel.json` sem mudança.
- [x] ADR-0010 (envio depois da resposta) e dúvidas registradas.
- [x] Suíte completa da API (com a migração do zero), ruff, lint/typecheck/test/build do front;
  migração 0005 `upgrade → downgrade → upgrade`; commit.
