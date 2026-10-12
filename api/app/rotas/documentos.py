"""Épico A do M3 · Documentos (H-17, H-18, H-19). Pertence ao épico A.

Contrato: `docs/superpowers/specs/m3-contrato.md`, seção 5.2. Esquemas em
`app/esquemas/documentos.py`. Nesta onda, todas respondem 501 `em_construcao`; sessão,
permissão, CSRF e validação do corpo já são as de verdade.

Rotas (as fixas antes de `/{documento_id}`):
- `GET  /api/documentos?arquivados=`                     → `ListaDocumentos` (`UnidadeLogada`)
- `GET  /api/documentos/publicos`                        → `ListaDocumentos` (sem sessão)
- `GET  /api/documentos/{documento_id}`                  → `Documento` (`UnidadeLogada`)
- `POST /api/documentos`                                 → 201 `Documento` (`Gestao`)
- `POST /api/documentos/{documento_id}/versoes`          → 201 `Documento` (`Gestao`)
- `POST /api/documentos/{documento_id}/arquivar`         → `Documento` (`Gestao`)
- `GET  /api/documentos/{documento_id}/versoes/{versao}/link?baixar=` → `LinkDoArquivo`
  (sessão opcional: sem sessão, só documento `publico`)

Quem vê o quê: `app.servicos.visibilidade.niveis_que_ve`. Fora disso, 404 igual a documento
inexistente.
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from app.erros_api import em_construcao
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
from app.servicos.armazenamento import Armazenado

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/documentos", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.get("")
def listar(logado: UnidadeLogada, db: Banco, arquivados: bool = False) -> ListaDocumentos:
    raise em_construcao()


@rotas.get("/publicos")
def publicos(db: Banco) -> ListaDocumentos:
    raise em_construcao()


@rotas.get("/{documento_id}")
def abrir(documento_id: int, logado: UnidadeLogada, db: Banco) -> Documento:
    raise em_construcao()


@rotas.post("", status_code=201)
def publicar(
    dados: NovoDocumento, logado: Gestao, db: Banco, tarefas: BackgroundTasks
) -> Documento:
    # "Avisar as unidades": `avisos.gravar_publicacao` na mesma transação e, depois do commit,
    # `notificacoes.agendar(tarefas, aviso_id)` (spec do M3, seção 5.2).
    raise em_construcao()


@rotas.post("/{documento_id}/versoes", status_code=201)
def nova_versao(
    documento_id: int, dados: NovaVersaoDocumento, logado: Gestao, db: Banco
) -> Documento:
    raise em_construcao()


@rotas.post("/{documento_id}/arquivar")
def arquivar(documento_id: int, logado: Gestao, db: Banco) -> Documento:
    raise em_construcao()


@rotas.get("/{documento_id}/versoes/{versao}/link")
def link(
    documento_id: int,
    versao: int,
    logado: SessaoOpcional,
    db: Banco,
    bucket: Armazenado,
    baixar: bool = False,
) -> LinkDoArquivo:
    raise em_construcao()
