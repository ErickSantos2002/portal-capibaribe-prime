# Dúvidas e decisões do M1 · Portão · Backup diário com restauração testada (issue #16)

Decisões tomadas sem perguntar a ninguém. As quatro grandes (bucket próprio, papel `backup`,
chave privada no Actions, horário e retenção) vieram do coordenador e estão na
[ADR-0009](../adr/0009-backup-bucket-papel-e-chave.md). Aqui fica o resto, revisável na revisão
do marco. **[Erick]** marca o que só o Erick pode confirmar.

## 1. A restauração de teste usa o backup que acabou de ser feito
- **Decisão:** o job de restauração roda depois do de backup, no mesmo run, e restaura
  exatamente o objeto que ele enviou (`--objeto`), não "o mais novo do bucket".
- **Por quê:** prova o backup daquele dia de ponta a ponta. Se o backup falhar, não há
  restauração naquele run (o e-mail da falha do backup já avisa).

## 2. Dia 2 é contado no fuso de Recife
- **Decisão:** a data do arquivo e o "dia 2" saem de `TZ=America/Recife`. O cron é 06:00 UTC =
  03:00 em Recife, então o dia é o mesmo nos dois fusos; a escolha só importa se o horário mudar.
- O agendamento do GitHub pode atrasar alguns minutos (ou mais, em horário de pico); não muda o
  dia.

## 3. Migração do backup comparada com o head da `main`, lido na hora
- **Decisão:** o head vem de `alembic heads` no checkout do run; nada de "0002" fixo. A lista de
  tabelas esperadas em `verificacoes.sql` é um **mínimo** (até a 0002): migração nova que cria
  tabela pode acrescentar a dela, mas não precisa para o teste passar.
- **Consequência:** se a `main` tiver migração ainda não aplicada no Neon, a restauração do dia 2
  reprova. Isso é um aviso útil (produção atrás do código), não um falso alarme. **[Erick]** as
  migrações de produção continuam à mão: aplicar logo depois do merge evita esse e-mail.

## 4. Restauração numa transação só, num banco obrigatoriamente vazio
- **Decisão:** `pg_restore --single-transaction --exit-on-error`, e o script recusa destino com
  qualquer tabela em `public`.
- **Por quê:** num desastre, ou volta tudo ou nada; e nunca se escreve por cima de um banco em
  uso por engano.

## 5. Dump conferido antes de cifrar e enviar
- **Decisão:** depois do `pg_dump`, o `pg_restore --list` precisa ler o arquivo e achar os dados
  da tabela `unidade`. Senão o run falha antes de enviar, e o backup bom de ontem continua sendo
  o mais novo. O envio confere o tamanho no bucket.

## 6. Retenção pelo nome, e só no padrão
- **Decisão:** a ordem vem do nome (`AAAA-MM-DD`), não da data de modificação; chave fora de
  `diarios/AAAA-MM-DD.dump.age` e `mensais/AAAA-MM.dump.age` nunca é apagada. Reenviar um backup
  antigo à mão não o faz "o mais novo".
- O mensal é uma cópia do diário do dia 1 (mesmo arquivo, duas chaves). Custa o dobro em um dia
  por mês; em troca a retenção dos dois tipos é independente.

## 7. Trava de tabela temporária reaplicada na restauração
- **Dúvida:** a migração 0001 tira `TEMPORARY` do banco para todos. Isso é permissão **do banco**,
  e o `pg_dump` não leva.
- **Decisão:** `restaurar.sh` reaplica o `revoke temporary` e `verificacoes.sql` confere.

## 8. Restauração de teste com `dono` e `app` sem login, mais `neon_superuser`
- **Decisão:** no Postgres descartável do Actions, os papéis do dump nascem `nologin` (ninguém
  entra com eles ali). Cria-se também `neon_superuser`, porque o Neon pode citá-lo em permissões
  do banco; sem ele, o `pg_restore` pararia por um papel que não existe.
- **Não testado contra o Neon:** os testes locais usam um banco criado pela migração, sem nada do
  Neon. O primeiro run de verdade (`restaurar=true`) é quem confirma. Se faltar algum outro papel
  do Neon, o erro do `pg_restore` diz qual, e é uma linha a mais nesse passo.

## 9. Cliente do Postgres 17 pelo repositório oficial PGDG
- **Decisão:** `scripts/backup/instalar-ferramentas.sh` instala `postgresql-client-17` pelo
  script oficial do pacote `postgresql-common`, e o `age` do Ubuntu. O runner é fixado em
  `ubuntu-24.04` (não `latest`) para o `apt` não mudar por baixo.
- **Alternativa descartada:** rodar o `pg_dump` dentro de `docker run postgres:17`: funciona (é o
  que o teste local faz quando a máquina tem outra versão), mas esconde a URL num argumento de
  container.

## 10. Testes locais: um script de ciclo, não pytest
- **Decisão:** `scripts/backup/testes/testar-ciclo.sh` (bash) cria `portal_m1_backup` no Postgres
  local (migração + carga + dados fictícios), o papel `backup` pelo SQL do repositório, sobe um S3
  falso (`moto` via `uv run --with`) e roda os scripts de verdade. 19 verificações, inclusive as
  que **têm de falhar**: 319 unidades, migração diferente, chave errada, banco não vazio, dump com
  senha errada (e aí nada chega ao bucket), papel `backup` tentando escrever.
- **Não entra no CI:** o CI não tem `age` nem a imagem de teste do backup, e o workflow mensal já
  é a prova contínua. **[Erick]** se quiser, dá para virar um job do CI depois.

## 11. Retenção com datas simuladas
- **Decisão:** `fazer-backup.sh` aceita `BACKUP_DATA=AAAA-MM-DD`. O teste semeia 34 diários e
  13 mensais antigos, faz o backup de 01/10 (que vira o 35º diário e o 14º mensal) e confere que
  sobram 30 e 12, os mais novos.

## 12. O que fica para o coordenador antes do primeiro run real
Ver a resposta do agente / o PR: rodar o SQL do papel `backup` como `dono`, definir a senha com
`\password backup`, criar os segredos `BACKUP_DATABASE_URL` e `BACKUP_AGE_KEY`, e disparar o
workflow com `restaurar=true`.
