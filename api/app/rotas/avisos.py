"""Épico C · Avisos, só texto (H-12, H-14, H-15, H-16). Pertence ao épico C.

Contrato: `docs/superpowers/specs/m1-contrato.md`, seção 4.4. Esquemas em
`app/esquemas/avisos.py`; regras de negócio em `app/servicos/avisos.py` (a criar).

Rotas a implementar (atenção à ordem: as fixas antes de `/{aviso_id}`):
- `GET  /api/avisos?busca=&arquivados=`   → `ListaAvisos` (`UnidadeLogada`)
- `GET  /api/avisos/nao-lidos`            → `ContagemNaoLidos` (`UnidadeLogada`)
- `GET  /api/avisos/alcance?blocos=`      → `Alcance` (`Gestao`)
- `GET  /api/avisos/{aviso_id}`           → `AvisoCompleto`; só lê, não grava nada
- `POST /api/avisos/{aviso_id}/lido`      → 204, idempotente; a 1ª vez conta (`UnidadeLogada`)
- `POST /api/avisos`                      → 201 `AvisoCompleto` (`Gestao`)
- `PUT  /api/avisos/{aviso_id}`           → `AvisoCompleto`, versão nova (`Gestao`)
- `POST /api/avisos/{aviso_id}/arquivar`  → `AvisoCompleto` (`Gestao`)
- `PUT  /api/avisos/{aviso_id}/fixado`    → `AvisoCompleto` (`Gestao`)
- `GET  /api/avisos/{aviso_id}/leitura`   → `Leitura` (`Gestao`)

GET nunca altera nada: com `SameSite=Lax`, uma navegação vinda de outro site leva o cookie e
escaparia da exigência de `X-Portal`. Por isso a leitura (H-16) é um POST à parte.

Modelos em `app/modelos/avisos.py`. O banco carimba as datas, exige versões em sequência e
confere no commit que o aviso tem versão 1 e destino (restrição `aviso_completo`).
"""

from fastapi import APIRouter, Depends

from app.seguranca.dependencias import exige_cabecalho_portal

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(dependencies=[Depends(exige_cabecalho_portal)])
