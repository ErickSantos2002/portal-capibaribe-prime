#!/usr/bin/env bash
# Instala no runner do GitHub (Ubuntu) o cliente do Postgres 17 e o age.
#
# O Ubuntu traz o Postgres da própria versão (16 no 24.04), e um pg_dump mais velho que o
# servidor (Neon, 17) recusa o dump. O caminho oficial para outra versão é o repositório PGDG,
# configurado pelo script que vem no pacote postgresql-common.
# Ferramentas instaladas em /usr/lib/postgresql/17/bin (o workflow passa esse PG_BIN).
set -euo pipefail

sudo apt-get update -qq
sudo apt-get install -y -qq postgresql-common age >/dev/null
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y >/dev/null
sudo apt-get install -y -qq postgresql-client-17 >/dev/null

/usr/lib/postgresql/17/bin/pg_dump --version
age --version
