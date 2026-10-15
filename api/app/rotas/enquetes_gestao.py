"""Épico A do M4 · Criar e gerir enquetes (H-20). Pertence ao épico A.

Contrato: `docs/superpowers/specs/m4-contrato.md`, seção 3; spec do épico:
`docs/superpowers/specs/m4-gestao.md`. Esquemas em `app/esquemas/enquetes.py`; regras em
`app/servicos/enquetes_gestao.py`.

Rotas (mesmo prefixo do roteador do épico B, `enquetes.py`; os caminhos não se cruzam):
- `POST /api/enquetes`                → 201 `EnqueteGravada` (`Gestao`)
- `PUT  /api/enquetes/{enquete_id}`   → `EnqueteGravada` (`Gestao`): só sem voto e aberta

Criar: na mesma transação, `avisos.gravar_publicacao` (o aviso automático, H-13, com o mesmo
destino), a enquete, as opções e os blocos; depois do commit, `notificacoes.agendar`. Editar:
apaga e insere as opções de novo e corrige o aviso com `avisos.gravar_correcao`. Os erros do
banco (`enquete_com_voto`, `enquete_encerrada`) viram 409, nunca 500.
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from app.esquemas.comum import IdBanco
from app.esquemas.enquetes import EditarEnquete, EnqueteGravada, NovaEnquete
from app.seguranca.dependencias import Banco, Gestao, exige_cabecalho_portal
from app.servicos import enquetes_gestao as servico
from app.servicos import notificacoes

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/enquetes", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.post("", status_code=201)
def publicar(
    dados: NovaEnquete, logado: Gestao, db: Banco, tarefas: BackgroundTasks
) -> EnqueteGravada:
    enquete_id, aviso_id = servico.criar(db, logado, dados)
    # H-13: o aviso automático notifica como qualquer aviso, depois do commit (M2).
    notificacoes.agendar(tarefas, aviso_id)
    return EnqueteGravada(id=enquete_id, aviso_id=aviso_id)


@rotas.put("/{enquete_id}")
def editar(enquete_id: IdBanco, dados: EditarEnquete, logado: Gestao, db: Banco) -> EnqueteGravada:
    # Correção do aviso automático sem notificar de novo (correção nunca notifica).
    aviso_id = servico.editar(db, logado, enquete_id, dados)
    return EnqueteGravada(id=enquete_id, aviso_id=aviso_id)
