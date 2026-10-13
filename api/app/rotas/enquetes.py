"""Épico B do M4 · Votar e resultado (H-21, H-22). Pertence ao épico B.

Contrato: `docs/superpowers/specs/m4-contrato.md`, seção 3. Esquemas em
`app/esquemas/enquetes.py`. Nesta onda, todas respondem 501 `em_construcao`; sessão, permissão,
CSRF e validação do corpo já são as de verdade.

Rotas (o roteador do épico A, `enquetes_gestao.py`, tem o mesmo prefixo; os caminhos não se
cruzam):
- `GET /api/enquetes`                         → `ListaEnquetes` (`UnidadeLogada`)
- `GET /api/enquetes/{enquete_id}`            → `Enquete` (`UnidadeLogada`)
- `PUT /api/enquetes/{enquete_id}/voto`       → `Enquete` (`UnidadeLogada`): votar e trocar
- `GET /api/enquetes/{enquete_id}/votantes`   → `Votantes` (`Gestao`)

Quem vê: a unidade comum, as enquetes para todos e as do bloco dela; fora disso, 404 igual a
enquete inexistente. A gestão vê todas, mas só vota se a unidade dela está no destino. O voto é
gravado na ordem da seção 2.6 do spec (dois celulares da mesma unidade = um voto só).
"""

from fastapi import APIRouter, Depends

from app.erros_api import em_construcao
from app.esquemas.comum import IdBanco
from app.esquemas.enquetes import Enquete, ListaEnquetes, Votantes, Votar
from app.seguranca.dependencias import Banco, Gestao, UnidadeLogada, exige_cabecalho_portal

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/enquetes", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.get("")
def listar(logado: UnidadeLogada, db: Banco) -> ListaEnquetes:
    raise em_construcao()


@rotas.get("/{enquete_id}")
def abrir(enquete_id: IdBanco, logado: UnidadeLogada, db: Banco) -> Enquete:
    raise em_construcao()


@rotas.put("/{enquete_id}/voto")
def votar(enquete_id: IdBanco, dados: Votar, logado: UnidadeLogada, db: Banco) -> Enquete:
    raise em_construcao()


@rotas.get("/{enquete_id}/votantes")
def votantes(enquete_id: IdBanco, logado: Gestao, db: Banco) -> Votantes:
    raise em_construcao()
