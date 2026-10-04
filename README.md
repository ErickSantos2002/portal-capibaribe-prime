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
| Código do app | Próximo: marco M0 (fundação) |

## Como foi pensado

- **Quem manda no desenho é a pessoa menos acostumada com tecnologia.** A persona de teste é a
  Dona Socorro, 62 anos: fonte Atkinson Hyperlegible, alvos de toque grandes, textos na voz do
  morador ("Bloco e apartamento", nunca "login").
- **Uma conta por unidade**, não por pessoa: é como o condomínio já funciona (um voto por
  apartamento) e dispensa aprovação de cadastro.
- **Custo zero de verdade**, sem depender de ninguém: Vercel Hobby, Neon Free, Cloudflare R2.
  Cada escolha está justificada, com o que foi descartado, em [`docs/adr/`](docs/adr/README.md).
- **LGPD desde o modelo de dados:** só nome, celular, e-mail e unidade. Sem CPF, contrato ou renda.

## Stack planejada

React + TypeScript (Vite, PWA) · FastAPI + SQLAlchemy + Alembic · PostgreSQL.

## Estrutura

```
docs/              visão, requisitos, histórias, modelo de dados, arquitetura, protótipo, roadmap
docs/adr/          registros de decisão de arquitetura
prototipo/         protótipo em HTML único, publicado na Vercel
scripts/dev/       teste automatizado do protótipo e gerador da imagem de prévia
```

Autor: Erick Santos Dantas
