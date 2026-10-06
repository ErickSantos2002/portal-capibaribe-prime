# ADR-0009 · Backup em bucket próprio, papel só de leitura e chave de restauração no Actions

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 06/10/2026 |
| **Complementa** | [ADR-0007](0007-backup.md) (backup diário) e [ADR-0004](0004-arquivos-r2.md) (R2) |

## Contexto
A ADR-0007 decidiu o backup diário com `pg_dump`, `age`, R2, retenção de 30 diários + 12
mensais e restauração mensal de teste. Na hora de montar (portão do M1, issue #16), quatro
pontos ficaram em aberto ou precisaram mudar:

1. A ADR-0004 dizia que o **mesmo bucket** dos arquivos guardaria os backups, numa pasta.
2. A ADR-0007 não dizia **com qual papel** o Actions conecta no banco.
3. A ADR-0007 dizia "chave privada **só com o autor**", mas a restauração mensal roda no
   Actions, sem ninguém do lado, e precisa decifrar.
4. Horário, nome dos arquivos e dia da restauração de teste não estavam fixados.

## Decisão

### 1. Bucket próprio para os backups
Os backups vão para o bucket **privado e dedicado** `portal-capibaribe-backups` (R2, classe
Standard), **não** para o bucket de arquivos do M3. A chave S3 do backup só enxerga esse bucket
(leitura e escrita de objetos; listar outros buckets dá AccessDenied). Isso substitui a frase
"o mesmo R2 guarda os backups, numa pasta separada" da ADR-0004.

Nomes: `diarios/AAAA-MM-DD.dump.age` todo dia e, no dia 1, também `mensais/AAAA-MM.dump.age`.
A retenção ordena pelo **nome** (não pela data de modificação) e nunca apaga chave fora desse
padrão.

### 2. Papel `backup`, só de leitura
O `pg_dump` conecta com um papel `backup` que só lê: membro de `pg_read_all_data`, sem escrita,
sem criar nada, com `default_transaction_read_only = on` e no máximo 2 conexões. É criado por
SQL pelo `dono` (`scripts/backup/criar-papel-backup.sql`, sem senha no arquivo). A conexão é a
**direta** do Neon (host sem `-pooler`): o `pg_dump` precisa de uma sessão inteira, que o
pooler em modo transação não garante. Segredo: `BACKUP_DATABASE_URL`.

A URL do `dono` **nunca** vai para o Actions.

### 3. A chave privada do `age` também fica num segredo do Actions
A restauração mensal precisa decifrar, então a chave privada vai para o segredo
`BACKUP_AGE_KEY`, usado **só** pelo job de restauração. O dono guarda também uma cópia
**offline** (fora do GitHub e fora do R2).

O objetivo da ADR-0007 continua valendo: **quem vazar o bucket não lê o backup**. A chave e os
backups ficam em provedores diferentes (GitHub × Cloudflare); para ler um backup é preciso
comprometer os dois. O que muda é que "só o autor decifra" vira "o autor e o workflow de
restauração decifram". A troca vale a pena: uma restauração testada todo mês sem depender de
alguém lembrar é exatamente o que a RNF-21 pede, e uma restauração manual que ninguém roda não
prova nada.

### 4. Horário e restauração de teste
- **Backup:** todo dia às 03:00 em Recife (cron `0 6 * * *`, UTC).
- **Restauração de teste:** no **dia 2** de cada mês (o dia seguinte ao mensal), restaura o
  backup que acabou de ser feito num Postgres 17 descartável do próprio Actions e confere: 5
  blocos, 320 unidades, as tabelas do modelo, gatilhos, permissões do papel `app`, a trava de
  tabela temporária e `alembic_version` igual ao head do repositório (lido na hora, nunca fixo).
  Também por `workflow_dispatch` com a entrada `restaurar: true`.
- Falha em qualquer passo ⇒ o GitHub manda e-mail (padrão das Actions).

As ferramentas são as do **Postgres 17** (a versão do Neon), do repositório oficial PGDG: um
`pg_dump` mais velho que o servidor recusa o dump, e um `pg_restore` mais velho não lê o arquivo.

## Consequências
- Menor privilégio dos dois lados: a chave do app (M3) nunca apaga backup; a chave do backup
  nunca lê arquivo de morador; o Actions nunca escreve no banco.
- Uma restauração por mês de verdade, num banco vazio, com verificações que falham alto
  (no teste local, um backup com 319 unidades reprova).
- Se a produção estiver atrás do repositório (migração mesclada e ainda não aplicada no Neon),
  a restauração de teste **reprova** pela migração. É de propósito: é um aviso de que a produção
  não está no código da `main`.
- O backup ainda cobre **só o banco**. Os arquivos do R2 (M3) precisam de decisão própria
  (roadmap, M3).
- Mais segredos para cuidar: `BACKUP_DATABASE_URL` e `BACKUP_AGE_KEY`, além dos `R2_*`.
- O GitHub desliga workflows agendados de repositório público depois de 60 dias sem atividade
  no repositório; o e-mail de aviso chega antes. Reativar é um clique em *Actions*.

## Alternativas consideradas
- **Pasta no bucket dos arquivos (ADR-0004):** uma chave só, mas a chave do app poderia apagar
  backup, e a do backup leria documentos de morador.
- **Dump com a conexão do `dono`:** mais simples, mas um segredo vazado do Actions daria escrita
  e `DROP` na produção.
- **Chave privada só offline, restauração mensal à mão:** fiel à ADR-0007, mas depende de
  disciplina todo mês; na prática, deixa de acontecer.
- **Neon branch/snapshot como backup:** fica no mesmo provedor que pode falhar ou mudar o plano
  grátis; não protege contra perda da conta.
