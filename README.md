# Portal Capibaribe Prime

Sistema web do condomínio **Capibaribe Prime Residence** (Recife/PE, 320 unidades, em obra até
2028). Concentra num lugar só o que hoje se perde no grupo de WhatsApp: **avisos oficiais,
enquetes e documentos** na fase de obra; reservas, chamados e encomendas depois da entrega.

**Protótipo navegável:** https://capibaribe-prototipo.vercel.app
(dados fictícios; já está em teste com os futuros vizinhos, e as opiniões voltam pro protótipo)

## Em que pé está

| Etapa | Situação |
|---|---|
| Visão, requisitos, histórias, modelo de dados, arquitetura | Feito (`docs/01` a `05`) |
| Protótipo de alta fidelidade | Feito e publicado (`prototipo/`, `docs/06`) |
| Teste com moradores | Em andamento |
| Roadmap | Feito (`docs/07`): 6 marcos na E1, primeiro uso real no M1 |
| Código do app | M1 (acesso e mural) no ar e anunciado no grupo em 06/10/2026: https://portal-capibaribe-prime.vercel.app, com backup diário · próximo: M2 (notificações) |

## Como foi pensado

- **Quem manda no desenho é a pessoa menos acostumada com tecnologia.** A persona de teste é a
  Dona Socorro, 62 anos: fonte Atkinson Hyperlegible, alvos de toque grandes, textos na voz do
  morador ("Bloco e apartamento", nunca "login").
- **Uma conta por unidade**, não por pessoa: é como o condomínio já funciona (um voto por
  apartamento) e dispensa aprovação de cadastro.
- **Custo zero de verdade**, sem depender de ninguém: Vercel Hobby, Neon Free, Cloudflare R2.
  Cada escolha está justificada, com o que foi descartado, em [`docs/adr/`](docs/adr/README.md).
- **LGPD desde o modelo de dados:** só nome, celular, e-mail e unidade. Sem CPF, contrato ou renda.

## Stack

React + TypeScript (Vite) · FastAPI + SQLAlchemy 2 + Alembic (Python 3.12) · PostgreSQL 17.

## Estrutura

```
web/               front-end React (Vite)
api/               FastAPI: app/ (rotas, serviços, modelos, comandos), migracoes/, testes/
docs/              visão, requisitos, histórias, modelo de dados, arquitetura, protótipo, roadmap
docs/adr/          registros de decisão de arquitetura
prototipo/         protótipo em HTML único, publicado na Vercel
scripts/dev/       teste do protótipo, imagem de prévia, logo e ícones do Portal
scripts/backup/    backup diário do banco (dump, cifra, R2, retenção) e restauração
vercel.json        front + API no mesmo projeto: /api/* vai para a FastAPI, o resto para o front
```

## Rodar localmente

Precisa de Docker, [uv](https://docs.astral.sh/uv/) e Node. O Python (3.12) vem do uv.

```sh
# 1. Postgres de desenvolvimento (só em 127.0.0.1)
docker run -d --name portal-pg-m0 -e POSTGRES_PASSWORD=teste -p 127.0.0.1:55432:5432 postgres:17

# 2. Testes da API: criam sozinhos os papéis dono e app e um banco descartável
cd api && uv run pytest

# 3. Banco de desenvolvimento: papéis, migração (como dono), carga e dados fictícios (como app)
docker exec portal-pg-m0 psql -U postgres -c "create database portal_dev owner dono"
cp .env.example .env
uv run --env-file .env alembic upgrade head
uv run --env-file .env python -m app.comandos.carga_inicial
uv run --env-file .env python -m app.comandos.dados_ficticios   # inclui um admin fictício

# 4. API em http://127.0.0.1:8000/api/saude
uv run --env-file .env uvicorn app.main:app --reload

# 5. Front em http://localhost:5173 (o Vite repassa /api para a API)
cd ../web && npm ci && npm run dev
```

Os papéis `dono` e `app` só existem no Postgres local depois que os testes rodaram uma vez
(passo 2). As variáveis estão explicadas em `api/.env.example`.

Notificações e e-mail (M2) ficam **desligados** sem as variáveis `PORTAL_VAPID_*`,
`PORTAL_SMTP_*` e `PORTAL_URL_BASE`, e o resto do Portal funciona igual. Um par de chaves VAPID
novo: `uv run python -m app.comandos.gerar_chaves_vapid` (nunca grave a saída no repositório).
Como o envio roda depois da resposta: [ADR-0010](docs/adr/0010-envio-em-segundo-plano.md).

Arquivos (M3: documentos e anexos) ficam **desligados** sem as variáveis abaixo: as rotas que
enviam ou abrem arquivo respondem 503 `arquivos_desligados` e o resto do Portal funciona igual.

| Variável | Para quê |
|---|---|
| `PORTAL_ARQUIVOS_ENDPOINT` | `https://<conta>.r2.cloudflarestorage.com` (com `/<bucket>` no fim também vale; em desenvolvimento, um S3 falso local em `http://127.0.0.1:<porta>`) |
| `PORTAL_ARQUIVOS_BUCKET` | o bucket **de arquivos** (`portal-capibaribe-arquivos`); nome com `backup` desliga os arquivos |
| `PORTAL_ARQUIVOS_CHAVE_ID`, `PORTAL_ARQUIVOS_CHAVE_SECRETA` | a chave S3 **própria** da API, "Object Read & Write" só desse bucket |
| `PORTAL_ARQUIVOS_REGIAO` | opcional; padrão `auto` (o único que o R2 aceita) |

Nunca os `R2_*` do backup (outra chave, outro bucket, [ADR-0009](docs/adr/0009-backup-bucket-papel-e-chave.md)).
A prévia da Vercel fica sem elas. Como o bucket é preparado (CORS, trava em `arquivos/`, ciclo
de vida em `envios/`) e a cópia no Backblaze B2: `docs/superpowers/duvidas-m3.md` e
[ADR-0011](docs/adr/0011-arquivos-protegidos-contra-perda.md). Um S3 falso para desenvolver:
`uv run --with 'moto[server]' moto_server -p 9000` (exemplo comentado em `api/.env.example`).

## Versões

A versão do Portal mora num lugar só, o `version` de `web/package.json`; o Vite a injeta no app
(`__VERSAO__`) e ela aparece no botão "Versão X.Y.Z", que abre a janela "O que mudou".

- **Correção** sobe o último número: 1.1.0 → 1.1.1.
- **Novidade** sobe o do meio: 1.1.0 → 1.2.0. **Marco novo** (M2, M3…) também sobe o do meio.
- Toda mudança que o morador vê ganha item em `web/src/sobre/novidades.ts` **no mesmo commit**,
  escrito na voz do morador (sem termo técnico). O teste confere que a primeira entrada é a
  versão do `package.json`, que as versões estão em ordem e que nenhuma data está no futuro.
- Logo e ícones: `scripts/dev/gerar-icones.py` refaz tudo a partir do logo original (que fica
  fora do repositório).

## Backup

Todo dia às 03:00 (Recife), o workflow `Backup` (`.github/workflows/backup.yml`) faz o
`pg_dump` da produção com o papel `backup` (só leitura), cifra com `age` e envia ao bucket
privado `portal-capibaribe-backups`: `diarios/AAAA-MM-DD.dump.age` e, no dia 1,
`mensais/AAAA-MM.dump.age`. Guarda 30 diários + 12 mensais. No dia 2 de cada mês ele restaura o
backup num Postgres temporário e confere tudo; se algo falhar, o GitHub manda e-mail.
Decisões: [ADR-0007](docs/adr/0007-backup.md) e [ADR-0009](docs/adr/0009-backup-bucket-papel-e-chave.md).

- **Disparar à mão:** `gh workflow run backup.yml -f restaurar=true` (backup + restauração de
  teste) ou `gh workflow run backup.yml` (só backup).
- **Testar o ciclo inteiro localmente** (Postgres do passo 1 de "Rodar localmente", dois S3
  falsos, nada de R2, B2 nem Neon): `scripts/backup/testes/testar-ciclo.sh`. Precisa de Docker,
  `uv` e `age`; sem `pg_dump` 17 no PATH, usa o da imagem `postgres:17`. Cobre também a cópia,
  a conferência e a restauração dos arquivos.

### Arquivos (cópia cifrada no Backblaze B2)

Os documentos e anexos moram no bucket `portal-capibaribe-arquivos` (R2), em `arquivos/<chave>`,
travados contra apagar e sobrescrever. O mesmo workflow, logo depois do `pg_dump`, copia para
um bucket privado do **Backblaze B2** cada arquivo que ainda não está lá, cifrado com `age`
(as mesmas chaves públicas de `scripts/backup/destinatarios.age`), como
`arquivos/<chave>.age` (`scripts/backup/copiar-arquivos.sh`). A cópia só acrescenta: nunca
apaga, nunca sobrescreve, e a chave do B2 nem tem permissão de apagar. No dia 2, a restauração
de teste confere que todo arquivo confirmado no banco restaurado tem cópia e decifra um deles
ao acaso (`scripts/backup/conferir-arquivos.sh`). Decisão: [ADR-0011](docs/adr/0011-arquivos-protegidos-contra-perda.md).

- **Segredos:** `ARQUIVOS_R2_*` (chave só de leitura do bucket de arquivos) e `COPIA_S3_*` (o
  B2), com os nomes da seção C de `docs/superpowers/duvidas-m3.md`. Sem eles, o passo só
  avisa (aviso amarelo no resumo do run) e o backup do banco segue normal. Com arquivos
  confirmados no banco e sem eles, a conferência do dia 2 reprova.
- **Onde ver:** no resumo de cada run do `Backup`, a seção "Cópia dos arquivos" diz quantos
  foram copiados agora e quantos já estavam lá.

### Restaurar num desastre (passo a passo)

O script nunca escreve por cima de um banco em uso: restaura num banco **novo e vazio**, confere,
e só então a aplicação passa a usá-lo.

1. **Ferramentas:** cliente do Postgres **17** (`pg_restore`, `psql`), `age` e `uv`. Em outra
   versão, aponte `PG_BIN` para a pasta do 17.
2. **Chave privada:** a cópia offline do dono, num arquivo com permissão 600
   (`chmod 600 chave.age`). O segredo `BACKUP_AGE_KEY` do GitHub não pode ser lido de volta.
3. **O backup:** baixe o `.dump.age` pelo painel da Cloudflare (R2 → `portal-capibaribe-backups`
   → `diarios/`), ou deixe o script baixar, com as variáveis `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`,
   `R2_SECRET_ACCESS_KEY` e `R2_BUCKET` de uma chave do bucket de backups.
4. **Banco vazio:** no Neon, crie o banco `portal_restaurado` com dono `dono` (os papéis `dono`
   e `app` já existem no projeto). Use a URL **direta** do `dono` (host sem `-pooler`).
5. **Restaurar e conferir** (da raiz do repositório):
   ```sh
   head="$(uv run --directory api --frozen alembic heads | awk '{print $1}')"
   BACKUP_AGE_KEY_FILE=chave.age scripts/backup/restaurar.sh \
     --destino "postgresql://dono:...@<host-direto>/portal_restaurado?sslmode=require" \
     --arquivo 2026-10-05.dump.age --head "$head"
   ```
   Sem `--arquivo`, baixa o diário mais novo (ou `--objeto diarios/AAAA-MM-DD.dump.age`). Se a
   produção estava numa migração mais velha que a `main`, a conferência acusa; rode sem `--head`
   e aplique as migrações depois (`alembic upgrade head`, como `dono`).
   O script termina com "restauração ok" e a contagem de linhas por tabela; qualquer outra
   saída é falha, e nada foi gravado pela metade (o `pg_restore` roda numa transação só).
6. **Apontar a aplicação:** na Vercel, troque o nome do banco em `DATABASE_URL` (e no
   `DATABASE_URL_DONO` de onde as migrações rodam) para `portal_restaurado` e faça um redeploy. Confira
   `/api/saude` e um login. O banco antigo fica guardado até a causa do desastre ser entendida.
7. **Papel de backup:** rode `scripts/backup/criar-papel-backup.sql` no banco novo e atualize o
   segredo `BACKUP_DATABASE_URL` (o backup das 03:00 passa a ler o banco novo).

### Restaurar os arquivos num desastre (passo a passo)

Para quando o bucket de arquivos (ou a conta da Cloudflare) se perdeu. Os arquivos voltam da
cópia no B2 para um bucket **novo**, decifrados, com os mesmos nomes (`arquivos/<chave>`); não
precisa do banco. Se o banco também se perdeu, restaure-o primeiro (acima): é ele que diz quais
arquivos cada documento usa, e os nomes batem.

1. **Ferramentas:** `age` e `uv` (o script baixa o resto na primeira vez).
2. **Chave privada:** a mesma cópia offline do backup do banco, num arquivo 600 (`chave.age`).
3. **Bucket novo no R2:** como no passo A.1 de `docs/superpowers/duvidas-m3.md` (privado,
   Standard), com outro nome (ex.: `portal-capibaribe-arquivos-2`; nunca com "backup" no nome:
   o script recusa). Crie uma chave **Object Read & Write só desse bucket** (passo A.2): ela
   serve para restaurar e depois para a API.
4. **Chave de leitura do B2:** o valor do segredo `COPIA_S3_*` do GitHub não pode ser lido de
   volta; crie no site do B2 (Application Keys → Add a New Application Key) uma chave **Read
   Only** só do bucket da cópia.
5. **Restaurar** (da raiz do repositório, no fish; `read -s` pergunta sem mostrar nem gravar
   no histórico):
   ```sh
   set -x COPIA_S3_ENDPOINT https://s3.<região>.backblazeb2.com
   set -x COPIA_S3_BUCKET <bucket da cópia>
   read -s -x COPIA_S3_ACCESS_KEY_ID
   read -s -x COPIA_S3_SECRET_ACCESS_KEY
   set -x DESTINO_S3_ENDPOINT https://<ACCOUNT_ID>.r2.cloudflarestorage.com
   set -x DESTINO_S3_BUCKET portal-capibaribe-arquivos-2
   read -s -x DESTINO_S3_ACCESS_KEY_ID
   read -s -x DESTINO_S3_SECRET_ACCESS_KEY
   BACKUP_AGE_KEY_FILE=chave.age scripts/backup/restaurar-arquivos.sh
   ```
   O fim diz `restaurados agora: N · já no destino: M · ...`. Se algum falhou (rede, por
   exemplo), rode de novo: ele pula o que já voltou. Pronto quando sai sem `ERRO`. Um aviso de
   "sem assinatura conhecida" quer dizer um objeto que não é PDF nem foto; ele volta como
   `application/octet-stream`.
6. **Configurar o bucket novo** como o antigo: CORS, ciclo de vida de `envios/` e a trava de
   `arquivos/` (passos A.4 a A.6). A trava pode vir antes ou depois da restauração: ela não
   impede gravar objeto novo, só apagar e sobrescrever.
7. **Apontar a API:** na Vercel (Production), troque `PORTAL_ARQUIVOS_ENDPOINT`,
   `PORTAL_ARQUIVOS_BUCKET`, `PORTAL_ARQUIVOS_CHAVE_ID` e `PORTAL_ARQUIVOS_CHAVE_SECRETA` para o
   bucket e a chave do passo 3, e faça um redeploy. Confira nos logs que **não** aparece
   "arquivos desligados" e abra um documento no Portal.
8. **Backup:** troque os segredos `ARQUIVOS_R2_*` do GitHub para o bucket novo, com uma chave
   **só de leitura** dele (passo A.3). A cópia continua de onde estava: os nomes são os mesmos,
   então nada é copiado de novo.
9. **Limpar:** `set -e` nas variáveis do passo 5 (ou feche o terminal) e apague a chave Read
   Only do B2 do passo 4.

Se quem se perdeu foi o **B2**, nada precisa voltar: crie outro bucket e chave (passos B.2 e
B.3), troque os segredos `COPIA_S3_*`, e o próximo backup copia tudo de novo.

## O primeiro administrador (produção)

A carga inicial não dá papel nenhum: uma conta de administrador com a senha inicial, que todo
mundo conhece, seria tomada por quem conhece o padrão. A sequência é:

1. deploy (migrações aplicadas e carga feita);
2. o administrador faz o **primeiro acesso** na unidade dele, pelo Portal;
3. de `api/`, com a URL do usuário `app`:
   `uv run python -m app.comandos.promover_admin <login>` (recusa unidade que ainda não fez o
   primeiro acesso; rodar de novo não muda nada; fica registrado no histórico).

A unidade real só aparece na linha de comando, nunca no repositório. Detalhes em
`docs/superpowers/specs/m1-contrato.md`, seção 2.5.

Várias cópias de trabalho ao mesmo tempo (um agente por épico): cada uma usa o próprio banco de
teste, com `PORTAL_TESTE_BANCO=portal_teste_<nome> uv run pytest`. Um `portal_dev` criado antes
da migração 0002 (celulares com máscara) precisa ser recriado.

A API em outra porta: `PORTAL_API_URL=http://127.0.0.1:8120 npm run dev` (ou `npm run preview`)
faz o Vite repassar o `/api` para ela.

Testes do front: `npm test` em `web/` roda os testes de componente (Vitest) e, depois do
`npm run build`, os de configuração (cabeçalhos e `vercel.json`).

Antes do primeiro commit: `pre-commit install` e `npm ci --prefix web` (o pre-commit roda ruff,
eslint e tsc).

Autor: Erick Santos Dantas
