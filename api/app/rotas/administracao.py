"""Épico B · Administração (H-07, H-08, H-09, H-11). Pertence ao épico B.

Contrato: `docs/superpowers/specs/m1-contrato.md`, seção 4.3. Esquemas em
`app/esquemas/administracao.py`; regras de negócio em `app/servicos/administracao.py` (a criar).
Todas as rotas com `Admin` (`exige_admin`).

Rotas a implementar:
- `GET    /api/admin/unidades?situacao=`                → `PainelAtivacao`
- `GET    /api/admin/unidades/{login}`                  → `UnidadeAdmin` (404)
- `POST   /api/admin/unidades/{login}/resetar`          → `UnidadeAdmin` (409 `ultimo_admin`)
- `PUT    /api/admin/unidades/{login}/papeis/{papel}`   → `UnidadeAdmin` (409 `unidade_nao_ativada`)
- `DELETE /api/admin/unidades/{login}/papeis/{papel}`   → `UnidadeAdmin` (409 `ultimo_admin`)
- `GET    /api/admin/historico?antes_de=&limite=`       → `PaginaHistorico`

O banco recusa retirar o último admin com `IntegrityError` cuja restrição
(`erro.orig.diag.constraint_name`) é `ultimo_admin`: traduzir para 409.
"""

from fastapi import APIRouter, Depends

from app.seguranca.dependencias import exige_cabecalho_portal

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(dependencies=[Depends(exige_cabecalho_portal)])
