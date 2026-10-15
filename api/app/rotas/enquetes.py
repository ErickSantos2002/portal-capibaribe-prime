"""Épico B do M4 · Votar e resultado (H-21, H-22). Pertence ao épico B.

Contrato: `docs/superpowers/specs/m4-contrato.md`, seção 3; spec do épico:
`docs/superpowers/specs/m4-votar.md`. Esquemas em `app/esquemas/enquetes.py`; regras em
`app/servicos/enquetes.py`.

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

from app.esquemas.comum import IdBanco
from app.esquemas.enquetes import Enquete, ListaEnquetes, Votantes, Votar
from app.seguranca.dependencias import Banco, Gestao, UnidadeLogada, exige_cabecalho_portal
from app.servicos import enquetes as servico

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/enquetes", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.get("")
def listar(logado: UnidadeLogada, db: Banco) -> ListaEnquetes:
    return ListaEnquetes(itens=servico.listar(db, logado))


@rotas.get("/{enquete_id}")
def abrir(enquete_id: IdBanco, logado: UnidadeLogada, db: Banco) -> Enquete:
    return servico.abrir(db, logado, enquete_id)


@rotas.put("/{enquete_id}/voto")
def votar(enquete_id: IdBanco, dados: Votar, logado: UnidadeLogada, db: Banco) -> Enquete:
    return servico.votar(db, logado, enquete_id, dados)


@rotas.get("/{enquete_id}/votantes")
def votantes(enquete_id: IdBanco, logado: Gestao, db: Banco) -> Votantes:
    return servico.votantes(db, logado, enquete_id)
