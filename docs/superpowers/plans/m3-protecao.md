# M3 · Épico C · Proteção dos arquivos · Plano de implementação

> **Para agentes:** executar tarefa por tarefa, com TDD (`superpowers:test-driven-development`).

**Objetivo:** cópia diária cifrada de `arquivos/` para o B2, conferência mensal e restauração
(ADR-0011, `m3-contrato.md` seção 9). **Spec:** `docs/superpowers/specs/m3-protecao.md`.

**Arquitetura:** um script `uv` (`scripts/backup/arquivos.py`, `boto3` + `age` em subprocesso)
com três comandos, e um invólucro bash para cada um (variáveis, chave privada, resumo do job),
no mesmo estilo de `fazer-backup.sh` e `restaurar.sh`.

## Restrições

- Python só por `uv run --frozen --script` (com `arquivos.py.lock`).
- Edita só `scripts/backup/**`, `.github/workflows/backup.yml`, a seção "Backup" do `README.md`,
  `docs/superpowers/duvidas-m3-protecao.md` e este plano/spec.
- Postgres de teste: container `portal-pg-m3-protecao` (porta 55483), removido no fim.
- Nenhum teste fala com R2/B2; chave `age` gerada no teste; segredos nunca no log.
- Sem push, merge, `gh workflow run`, Vercel, Neon, R2, B2.

## Tarefas

1. [x] Spec e plano.
2. [x] **Copiar.** Teste no `testar-ciclo.sh` (dois `moto`, objetos de 4 tipos, chave fora do
   padrão, `envios/`, sem variáveis, segunda rodada) vermelho → `arquivos.py copiar` +
   `copiar-arquivos.sh` + lock → verde → commit.
3. [x] **Conferir.** Linhas `arquivo` confirmadas e pendentes na origem antes do backup do dia 2;
   teste da conferência (passa, passa com aviso, quatro falhas) vermelho → `arquivos.py
   conferir` + `conferir-arquivos.sh` → verde → commit.
4. [x] **Restaurar.** Teste (bucket novo, mesmos bytes, tipo, idempotência, recusa de `backup`)
   vermelho → `arquivos.py restaurar` + `restaurar-arquivos.sh` → verde → commit.
5. [x] **Workflow.** Passo da cópia no job `backup` (depois do backup do banco) e da conferência
   no job `restauracao`; a restauração roda mesmo se só a cópia falhou. `pre-commit` (actions
   por SHA) → commit.
6. [x] **README e dúvidas.** Seção "Backup" com a cópia e o passo a passo da restauração dos
   arquivos; `duvidas-m3-protecao.md` → commit.
