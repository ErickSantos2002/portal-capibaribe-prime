"""Épico A do M3 · Documentos (H-17, H-18, H-19, RF-33). Pertence ao épico A.

Contrato: `docs/superpowers/specs/m3-contrato.md`, seção 5.2; spec do épico:
`docs/superpowers/specs/m3-documentos.md`. Esquemas em `app/esquemas/documentos.py`; regras em
`app/servicos/documentos.py`.

Rotas (as fixas antes de `/{documento_id}`):
- `GET  /api/documentos?arquivados=`                     → `ListaDocumentos` (`UnidadeLogada`)
- `GET  /api/documentos/publicos`                        → `ListaDocumentos` (sem sessão)
- `GET  /api/documentos/{documento_id}`                  → `Documento` (`UnidadeLogada`)
- `POST /api/documentos`                                 → 201 `Documento` (`Gestao`)
- `POST /api/documentos/{documento_id}/versoes`          → 201 `Documento` (`Gestao`)
- `POST /api/documentos/{documento_id}/arquivar`         → `Documento` (`Gestao`)
- `GET  /api/documentos/{documento_id}/versoes/{versao}/link?baixar=` → `LinkDoArquivo`
  (sessão opcional: sem sessão, só documento `publico`)

Quem vê o quê: `app.servicos.visibilidade.niveis_que_ve`, e arquivado só para a gestão. Fora
disso, 404 igual a documento inexistente.
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from app.esquemas.arquivos import LinkDoArquivo
from app.esquemas.documentos import (
    Documento,
    ListaDocumentos,
    NovaVersaoDocumento,
    NovoDocumento,
)
from app.seguranca.dependencias import (
    Banco,
    Gestao,
    SessaoOpcional,
    UnidadeLogada,
    exige_cabecalho_portal,
)
from app.servicos import documentos as servico
from app.servicos import notificacoes
from app.servicos.armazenamento import Armazenado

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/documentos", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.get("")
def listar(logado: UnidadeLogada, db: Banco, arquivados: bool = False) -> ListaDocumentos:
    return ListaDocumentos(itens=servico.listar(db, logado, arquivados=arquivados))


@rotas.get("/publicos")
def publicos(db: Banco) -> ListaDocumentos:
    return ListaDocumentos(itens=servico.publicos(db))


@rotas.get("/{documento_id}")
def abrir(documento_id: int, logado: UnidadeLogada, db: Banco) -> Documento:
    return servico.abrir(db, logado, documento_id)


@rotas.post("", status_code=201)
def publicar(
    dados: NovoDocumento, logado: Gestao, db: Banco, tarefas: BackgroundTasks
) -> Documento:
    documento_id, aviso_id = servico.publicar(db, logado, dados)
    # RF-33: o aviso automático notifica como qualquer aviso, depois do commit (M2).
    if aviso_id is not None:
        notificacoes.agendar(tarefas, aviso_id)
    return servico.abrir(db, logado, documento_id)


@rotas.post("/{documento_id}/versoes", status_code=201)
def nova_versao(
    documento_id: int, dados: NovaVersaoDocumento, logado: Gestao, db: Banco
) -> Documento:
    servico.nova_versao(db, logado, documento_id, dados)
    return servico.abrir(db, logado, documento_id)


@rotas.post("/{documento_id}/arquivar")
def arquivar(documento_id: int, logado: Gestao, db: Banco) -> Documento:
    servico.arquivar(db, logado, documento_id)
    db.expire_all()
    return servico.abrir(db, logado, documento_id)


@rotas.get("/{documento_id}/versoes/{versao}/link")
def link(
    documento_id: int,
    versao: int,
    logado: SessaoOpcional,
    db: Banco,
    bucket: Armazenado,
    baixar: bool = False,
) -> LinkDoArquivo:
    return servico.link(db, logado, documento_id, versao, bucket, baixar=baixar)
