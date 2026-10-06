# Registros de decisão (ADRs)

Cada arquivo registra uma decisão de arquitetura: o contexto, o que foi decidido, as
consequências e o que foi descartado. Decisão nova não edita a antiga: cria outra ADR que a
substitui.

| ADR | Decisão |
|---|---|
| [0001](0001-stack.md) | Stack: React + TypeScript no front, FastAPI + PostgreSQL na API |
| [0002](0002-hospedagem-vercel.md) | Hospedagem na Vercel (plano Hobby), front e API no mesmo projeto |
| [0003](0003-banco-neon.md) | Banco no Neon (PostgreSQL gerenciado, plano Free) |
| [0004](0004-arquivos-r2.md) | Arquivos no Cloudflare R2, bucket privado com URLs assinadas |
| [0005](0005-login-por-unidade.md) | Login por unidade com senha própria e sessão em cookie |
| [0006](0006-notificacoes.md) | Notificações por Web Push, com e-mail pelo Gmail como reserva |
| [0007](0007-backup.md) | Backup diário próprio, fora do Neon |
| [0008](0008-sem-dominio-proprio.md) | Sem domínio próprio: endereço gratuito da Vercel |
| [0009](0009-backup-bucket-papel-e-chave.md) | Backup em bucket próprio, papel só de leitura e chave de restauração no Actions (complementa 0007 e 0004) |
