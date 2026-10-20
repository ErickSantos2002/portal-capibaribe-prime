# Classificados entre vizinhos · Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: use superpowers:executing-plans para executar este plano tarefa por tarefa, com TDD (superpowers:test-driven-development). Os passos usam caixas (`- [ ]`) para acompanhar.

**Objetivo:** as unidades anunciam algo para vender, trocar ou doar, com até 4 fotos; quem se interessa chama o dono no WhatsApp; o anúncio vence em 30 dias e some sozinho; as fotos são apagadas de verdade; a gestão só modera quando alguém avisa.

**Arquitetura:** a migração 0011, escrita à mão, cria quatro tabelas com as regras no banco (situação, vencimento, limites, até 4 fotos, escondido travado), no padrão da 0007 a 0010. A API tem dois roteadores com o prefixo `/api/classificados` (morador e gestão), serviços separados e a tradução dos erros do banco. As fotos têm tabela e envio próprios (`anuncio_foto`), reaproveitando a camada de armazenamento do M3 com uma pasta nova, `classificados/`, sem trava (ADR-0012). A faxina diária roda pelo Vercel Cron. O front ganha a pasta `web/src/classificados/` e entra no menu com uma entrada em `casca/menu.ts`.

**Tecnologias:** PostgreSQL 17, Alembic (migração à mão), SQLAlchemy 2, FastAPI, Pydantic 2, pytest. React 19, react-router 8, vitest e Testing Library. Conferência visual com playwright-core e o Chrome do sistema, **sempre headless**.

**Spec:** `docs/superpowers/specs/2026-10-20-classificados-design.md` (commit 20ca725). Quando os dois divergem, vale o spec, e a divergência vai para `docs/superpowers/duvidas-classificados.md`.

## Restrições globais

- **NUNCA abrir janela visível de navegador**, nem o MCP do Playwright. Só o Chrome headless do `scripts/dev/conferir-letra.mjs`.
- **Sem push, merge, deploy nem Neon, R2 real, Vercel ou GitHub remoto.** A 0011 vai para o Neon pelo coordenador **antes** do push.
- Branch **`classificados/construcao`**, numa worktree. Commits pequenos, em português, terminando com `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`. O pre-commit roda sempre (**nunca `--no-verify`**).
- Python **sempre** com `uv run --frozen`, de dentro de `api/`.
- **Postgres de teste próprio:** container `portal-pg-classificados` na porta **55490**.
  ```sh
  docker start portal-pg-classificados || docker run -d --name portal-pg-classificados -e POSTGRES_PASSWORD=teste -p 127.0.0.1:55490:5432 postgres:17
  cd api && PORTAL_TESTE_ADMIN_URL=postgresql://postgres:teste@127.0.0.1:55490/postgres \
    PORTAL_TESTE_BANCO=portal_teste_classificados uv run --frozen pytest -q
  ```
- **Ambiente de conferência:** nome `classificados-conf`, portas 55491 (Postgres), **8190** (API) e **5190** (web): `scripts/dev/ambiente-conferencia.sh subir classificados-conf 55491 8190 5190` (o 55490 é do banco de teste).
- Front: `cd web && npx vitest run <arquivo>`. Para fechar: `npm test && npm run lint && npx tsc -b`.
- Valores do spec, sem mudar: título 3–80; descrição até 1000; motivo do aviso até 300; preço só na venda, de 0 a R$ 100.000 (10.000.000 centavos); até 4 fotos (JPEG, PNG, WEBP); vence em 30 dias; renovar só a menos de 7 dias de vencer (ou vencido); **5 anúncios novos por unidade por dia** e **10 abertos**; 1 aviso aberto por unidade e anúncio, 10 avisos por unidade a cada 24 h; faxina de vencido há 30 dias e encerrado há 7; versão **1.9.0**.
- Categorias iniciais, nesta ordem: Móveis · Eletrodomésticos · Eletrônicos · Material de obra e acabamento · Decoração · Utilidades domésticas · Infantil · Outros.
- Textos na voz do morador. O nome do responsável **nunca** aparece; o anúncio mostra só a placa.
- CSS segue a regra do M5 (rem, sem media query de tamanho; o guarda é `web/testes/letra.test.ts`).
- Só dados fictícios (RNF-16). O repo é público: a unidade do admin fictício é 1101.

## Decisões deste plano (o spec deixou com o builder)

1. **Foto em tabela própria (`anuncio_foto`), não no `arquivo`.** O `arquivo` confirmado é para sempre (trigger da 0007, cópia diária, conferência do dia 2, que exige cópia de todo confirmado). Pôr a foto lá pediria três exceções (trigger, `conferir-arquivos.sh` e a finalidade); a tabela própria não pede nenhuma, e o `arquivo` continua com a regra simples "publicado = para sempre". Justificado na ADR-0012.
2. **O envio da foto** segue o do M3 (pedir → PUT em `envios/` → confirmar), com rotas próprias (`POST /api/classificados/fotos` e `…/{id}/confirmar`) abertas a qualquer unidade logada (o `/api/arquivos` é só da gestão). A conferência do conteúdo reaproveita `tipo_pelo_conteudo`, e só imagem passa. A foto confirmada é copiada para `classificados/<chave>`.
3. **Armazenamento:** a camada ganha `publicar_foto`, `url_da_foto` e **um** apagar, `apagar_classificado(caminho)`, que só aceita `classificados/<32 hexadecimais>` (teste recusa `arquivos/`, `envios/` e caminho torto). O falso dos testes imita.
4. **Estados da foto:** pendente → pronta (confirmada, sem anúncio) → no anúncio (com `ordem`) → descartada (`descartada_em`). Recusar, tirar na edição, encerrar e vencer (pela faxina), "apagar meus dados" e reset **descartam**; depois do commit, `varrer_fotos` apaga o objeto e, se a foto foi enviada há mais de 24 h (ou é "apagar meus dados"/reset), a linha. A linha descartada mais nova fica até a faxina só para contar no limite de **40 fotos enviadas por unidade a cada 24 h** (sem isso, mandar e tirar não teria fim). O banco proíbe apagar anúncio com foto presa (chave estrangeira sem cascata): nenhuma foto fica órfã no bucket.
5. **Busca em Python** (`normalizar` das indicações) sobre título, descrição e categoria; nada de colunas `*_busca`. São no máximo 3.200 anúncios abertos, sem paginação.
6. **Vencido:** só renovar ou encerrar (o banco recusa editar e reservar). Escondido: só encerrar. Encerrado: nada muda (anuncia de novo). Renovar é carimbar `renovado_em`; o banco calcula `vence_em` e confere a janela de 7 dias.
7. **Para quem não é o dono nem a gestão**, vencido, encerrado e escondido dão 404 `anuncio_indisponivel` ("Este anúncio não está mais disponível."), igual a um que não existe.
8. **Faxina:** **Vercel Cron**, `GET /api/classificados/faxina` às 07:00 UTC (04:00 de Recife), protegida por `Authorization: Bearer $CRON_SECRET` (sem a variável: 503, e nada roda). Escolhida em vez do workflow do GitHub porque o cron mora no mesmo projeto e no mesmo `vercel.json`, sem um segredo a mais no GitHub nem uma URL de produção no repositório; a Vercel manda o cabeçalho sozinha. Falhar só atrasa: a lista já filtra o vencido pela data, e a próxima rodada faz tudo. Cada rodada que apaga algo vai para o histórico (`classificados_faxina`, só contagens).
9. **Aviso repetido** da mesma unidade é idempotente; o e-mail do primeiro aviso vai para a administração, com a cota do Gmail reservada no histórico (`classificado_aviso_email`), como nas indicações.
10. **Categoria nova** entra antes de "Outros", como nas indicações; a tela fica em `/classificados/categorias` (só `Admin`), com o link no painel.

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `api/migracoes/versions/0011_classificados.py` | tabelas, carga, triggers, grants |
| `api/app/modelos/classificados.py` | modelos e constantes |
| `api/app/esquemas/classificados.py` | entrada e saída; espelho em `web/src/classificados/tipos.ts` |
| `api/app/servicos/armazenamento.py` | pasta `classificados/`: publicar, ler, apagar |
| `api/app/servicos/classificados_fotos.py` | envio, confirmação, descartar e varrer as fotos |
| `api/app/servicos/classificados.py` | ler, anunciar, editar, reservar, renovar, encerrar, avisar, apagar da unidade |
| `api/app/servicos/classificados_gestao.py` | esconder, resolver, categorias, faxina |
| `api/app/servicos/classificados_banco.py` | `RESTRICOES` e `traduzir` |
| `api/app/servicos/classificados_email.py` | e-mail do primeiro aviso |
| `api/app/rotas/classificados.py`, `classificados_gestao.py` | rotas |
| `api/testes/apoio_classificados.py`, `test_classificados_*.py` | testes |
| `web/src/classificados/*` | telas, api, tipos, formatos, menu, rotas, css, testes |
| `docs/adr/0012-fotos-descartaveis-dos-classificados.md` | a decisão das fotos |

---

### Tarefa 1: Migração 0011, modelos e regras do banco
- [ ] Testes de banco que falham (`test_classificados_banco.py`), tentando burlar direto como `app`: categorias na ordem; tipo fora da lista; preço na doação e na troca; preço acima do teto; datas carimbadas pelo banco (`publicado_em`, `vence_em` = +30 dias); unidade inativa não anuncia, não envia foto, não avisa; 6º anúncio do dia; 11º aberto; 5ª foto; foto de outra unidade; encerrado que volta; encerrar sem motivo; vencido não edita nem reserva; renovar fora da janela; escondido só encerra; `vence_em` não muda à mão; apagar anúncio com foto presa é recusado; 41ª foto do dia (descartadas contam); segundo aviso aberto; 11º aviso do dia; `app` não apaga categoria.
- [ ] `test_migracoes.py`: downgrade da 0011 volta à 0010; funções com `search_path` fixo. `test_modelos.py`, `test_m2_backup.py` (`verificacoes.sql`), `conftest.TABELAS` e o `banco_limpo` recarregando as categorias.
- [ ] Escrever migração, modelos e apoio. Rodar: PASS. Commit `feat(api): migração 0011, tabelas e regras dos classificados`.

### Tarefa 2: Esquemas, espelho TS, tradução de erros, ações do histórico
- [ ] `test_classificados_esquemas.py` (título NFC e 3–80, descrição até 1000 com `\n`, preço só na venda, contato com nono dígito, até 4 fotos sem repetir, motivo do encerramento na lista) e `test_classificados_erros_do_banco.py` (toda regra, restrição e índice único das quatro tabelas em `RESTRICOES`, todos 4xx). `test_contrato.py` ganha `classificados`.
- [ ] Commit `feat(api): esquemas dos classificados, espelho no front e tradução dos erros do banco`.

### Tarefa 3: Armazenamento da pasta `classificados/` e envio das fotos
- [ ] `test_classificados_fotos.py`: `apagar_classificado` recusa `arquivos/…`, `envios/…` e caminho torto (S3 e falso); envio → confirmação publica em `classificados/` e nunca em `arquivos/`; PDF e lixo recusados (descartada, conta no limite); tamanho acima de 10 MB recusado; foto de outra unidade 404; arquivos desligados 503; `varrer_fotos` apaga o objeto e a linha (velha) e não derruba nada se o bucket falhar.
- [ ] Commit `feat(api): fotos dos classificados numa pasta própria, sem trava`.

### Tarefa 4: Anunciar, ler, editar e o ciclo do dono
- [ ] `test_classificados_rotas.py`: criar com fotos (capa = primeira); lista só com ativos e reservados não vencidos nem escondidos; ordem por publicação ou renovação; filtros tipo, categoria e busca sem acento; `meus` com todos os estados; para outro, vencido/encerrado/escondido 404 com a frase; para o dono e a gestão abre; editar (só o dono, 403 para outro; tira foto → objeto apagado; acrescenta; 5ª → 422); reservar/liberar/renovar/encerrar só o dono; renovar fora da janela 409; encerrado não volta; escondido só encerra; limites viram 429; placa sem o nome do responsável.
- [ ] Commit `feat(api): anunciar, lista, meus anúncios e o ciclo do dono`.

### Tarefa 5: Avisar, gestão, e-mail, categorias
- [ ] `test_classificados_gestao.py` e `test_classificados_email.py`: aviso idempotente; só a gestão esconde e resolve; esconder resolve os avisos e registra; contagem e filtro "com aviso"; e-mail do primeiro aviso para os admins, sem motivo nem placa, na cota; categorias só para o admin, a nova antes de "Outros", repetida 409.
- [ ] Commit `feat(api): moderação dos classificados, e-mail do primeiro aviso e categorias`.

### Tarefa 6: Faxina e "apagar meus dados"/reset
- [ ] `test_classificados_faxina.py`: sem `CRON_SECRET` 503; segredo errado 401; apaga vencido há mais de 30 dias e encerrado há mais de 7 (linha, avisos e objetos), deixa os outros; foto pronta ou pendente esquecida há mais de 1 dia sai; bucket falhando não quebra (a próxima rodada termina); registra `classificados_faxina` só quando apaga. `test_classificados_apagar.py`: "apagar meus dados" e reset apagam anúncios, fotos (objetos no falso) e avisos da unidade.
- [ ] `vercel.json` ganha o `crons`; `web/testes/vercel.test.ts` confere.
- [ ] Commit `feat(api): faxina diária dos classificados e apagar meus dados`.

### Tarefa 7: Front, base: api, tipos, formatos, menu, rotas, lista e meus anúncios
- [ ] `formatos.test.ts` (selo "Vende R$ 350", "Vende · a combinar", "Troca", "Doa"; preço em reais ↔ centavos; "há 3 dias"; mensagem do WhatsApp); `lista.test.tsx` (cartões, filtro de tipo e categoria, busca, vazio, "Meus anúncios", faixa da gestão, menu); `menu.test.ts`.
- [ ] Commit `feat(web): lista dos classificados e o lugar novo no menu`.

### Tarefa 8: Anúncio aberto, fluxo do dono, avisar e a gestão
- [ ] `anuncio.test.tsx` (fotos e visor, WhatsApp com a mensagem pronta, "Ligar" no fixo, reservar, renovar, encerrar com motivo, vencido, escondido, avisar, "Para a gestão").
- [ ] Commit `feat(web): anúncio aberto, o que o dono faz e a gestão`.

### Tarefa 9: Anunciar e editar (fotos)
- [ ] `novo.test.tsx` (sem tipo não publica, preço só em Vender, contato pré-preenchido, fotos até 4 com envio e remoção, editar com as fotos de antes, sair sem publicar).
- [ ] Commit `feat(web): anunciar e editar, com até 4 fotos`.

### Tarefa 10: Categorias, frases do histórico, Privacidade, inventário, ADR, roadmap
- [ ] Commit `docs: ADR-0012` e o resto junto da versão.

### Tarefa 11: Conferência visual headless
- [ ] Telas `classificados`, `classificado`, `novo-classificado`, `meus-classificados` (e `classificado-gestao`) no `conferir-letra.mjs`, com semente; 320/360/412/1280 × 16/24/32 × claro/escuro; corrigir até zero problema novo.
- [ ] Commit `test(conferencia): telas dos classificados`.

### Tarefa 12: Versão 1.9.0, novidades, verificação final
- [ ] `web/package.json` 1.9.0, `novidades.ts`, Privacidade e inventário no mesmo commit da função. Suítes inteiras da API e do web.
- [ ] Commit `feat: classificados entre vizinhos (1.9.0)`.
