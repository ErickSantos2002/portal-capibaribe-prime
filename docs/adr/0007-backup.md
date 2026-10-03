# ADR-0007 · Backup diário próprio, fora do Neon

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 02/10/2026 |

## Contexto
O Neon grátis só permite restaurar até 6 horas atrás. Um erro descoberto no dia seguinte não
teria volta. RNF-21 pede backup automático com teste de restauração.

## Decisão
Um workflow do GitHub Actions roda **todo dia às 03:00 (Recife)**: `pg_dump` da produção,
compactado e criptografado (`age`, chave pública no repositório, chave privada só com o autor),
enviado ao R2 em `backups/`. Retenção: 30 diários + 12 mensais. **Uma vez por mês** o mesmo
workflow restaura o backup mais recente num banco temporário e roda verificações de contagem;
se falhar, o GitHub avisa por e-mail.

## Consequências
- Backup testado de verdade, não só gerado.
- Os dados pessoais saem do Neon, então o backup é criptografado antes de sair do Actions.
- GitHub Actions é grátis para repositório público; se o repositório for privado, a cota
  gratuita de minutos é mais do que suficiente para um job diário curto.

## Alternativas consideradas
- **Confiar só no Neon:** 6 horas é pouco.
- **Backup no Google Drive:** mais uma credencial para gerenciar; o R2 já está no projeto.
