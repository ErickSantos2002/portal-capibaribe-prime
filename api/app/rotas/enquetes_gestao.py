"""Épico A do M4 · Criar e gerir enquetes (H-20). Pertence ao épico A.

Contrato: `docs/superpowers/specs/m4-contrato.md`, seção 3. Esquemas em
`app/esquemas/enquetes.py`. Nesta onda, as duas respondem 501 `em_construcao`; sessão,
permissão, CSRF e validação do corpo já são as de verdade.

Rotas (mesmo prefixo do roteador do épico B, `enquetes.py`; os caminhos não se cruzam):
- `POST /api/enquetes`                → 201 `EnqueteGravada` (`Gestao`)
- `PUT  /api/enquetes/{enquete_id}`   → `EnqueteGravada` (`Gestao`): só sem voto e aberta

Criar: na mesma transação, `avisos.gravar_publicacao` (o aviso automático, H-13, com o mesmo
destino), a enquete, as opções e os blocos; depois do commit, `notificacoes.agendar`. Editar:
apaga e insere as opções de novo e corrige o aviso com `avisos.gravar_correcao`. Os erros do
banco (`enquete_com_voto`, `enquete_encerrada`) viram 409, nunca 500.
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from app.erros_api import em_construcao
from app.esquemas.comum import IdBanco
from app.esquemas.enquetes import EditarEnquete, EnqueteGravada, NovaEnquete
from app.seguranca.dependencias import Banco, Gestao, exige_cabecalho_portal

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/enquetes", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.post("", status_code=201)
def publicar(
    dados: NovaEnquete, logado: Gestao, db: Banco, tarefas: BackgroundTasks
) -> EnqueteGravada:
    raise em_construcao()


@rotas.put("/{enquete_id}")
def editar(enquete_id: IdBanco, dados: EditarEnquete, logado: Gestao, db: Banco) -> EnqueteGravada:
    raise em_construcao()
