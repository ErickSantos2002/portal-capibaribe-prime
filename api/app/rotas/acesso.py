"""Épico A · Acesso (H-01, H-02, H-03, H-06). Pertence ao épico A.

Contrato: `docs/superpowers/specs/m1-contrato.md`, seção 4.2. Esquemas em
`app/esquemas/acesso.py`; regras de negócio em `app/servicos/acesso.py` (a criar).

Rotas a implementar:
- `POST   /api/acesso/entrar`                      → `Eu` + cookie (401, 423, 422)
- `POST   /api/acesso/primeiro-acesso`             → `Eu` (sessão restrita: `SessaoQualquer`)
- `GET    /api/minha-unidade`                      → `MinhaUnidade` (`UnidadeLogada`)
- `PUT    /api/minha-unidade/dados`                → `MinhaUnidade`
- `PUT    /api/minha-unidade/senha`                → 204
- `DELETE /api/minha-unidade/aparelhos/{sessao_id}` → 204
- `POST   /api/minha-unidade/apagar-dados`         → 204

`GET /api/acesso/eu` e `POST /api/acesso/sair` são comuns e já estão em `app/rotas/sessao.py`.
Peças prontas: `app.seguranca.sessoes` (criar sessão, cookie), `app.seguranca.senhas`,
`app.seguranca.dependencias` (`SessaoQualquer`, `UnidadeLogada`, `Banco`),
`app.servicos.historico.registrar` e `app.erros_api.ErroApi`.
"""

from fastapi import APIRouter, Depends

from app.seguranca.dependencias import exige_cabecalho_portal

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(dependencies=[Depends(exige_cabecalho_portal)])
