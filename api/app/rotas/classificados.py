"""Classificados entre vizinhos: o que o morador faz (spec de 20/10/2026, seções 3 e 8).

Esquemas em `app/esquemas/classificados.py`; regras em `app/servicos/classificados.py` e
`classificados_fotos.py`. A moderação e a faxina estão em `classificados_gestao.py`, com o mesmo
prefixo; os caminhos não se cruzam. As rotas fixas vêm antes de `/{anuncio_id}`.

- `GET  /api/classificados/categorias`             → `ListaCategoriasClassificado`
- `GET  /api/classificados?tipo=&categoria=&busca=&com_aviso=` → `ListaClassificados`
- `GET  /api/classificados/meus`                   → `MeusAnuncios`
- `POST /api/classificados/fotos`                  → 201 `FotoAutorizada`
- `POST /api/classificados/fotos/{id}/confirmar`   → `FotoEnviada`
- `POST /api/classificados`                        → 201 `AnuncioCriado`
- `GET  /api/classificados/{id}`                   → `Anuncio`
- `PUT  /api/classificados/{id}`                   → `Anuncio` (o dono)
- `POST /api/classificados/{id}/reservar|liberar|renovar` → `Anuncio` (o dono)
- `POST /api/classificados/{id}/encerrar`          → `Anuncio` (o dono)
- `POST /api/classificados/{id}/aviso`             → 204

Só unidade logada e com o primeiro acesso concluído (`UnidadeLogada`). Para quem não é o dono nem
a gestão, vencido, encerrado e escondido são 404 "Este anúncio não está mais disponível.".
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response

from app.esquemas.classificados import (
    Anuncio,
    AnuncioCriado,
    EncerrarAnuncio,
    FotoAutorizada,
    FotoEnviada,
    ListaCategoriasClassificado,
    ListaClassificados,
    MeusAnuncios,
    NovoAnuncio,
    PedirFoto,
    TipoAnuncio,
)
from app.esquemas.comum import IdBanco
from app.esquemas.indicacoes import AvisarGestao
from app.modelos.classificados import LIMITE_TITULO
from app.seguranca.dependencias import Banco, UnidadeLogada, exige_cabecalho_portal
from app.servicos import classificados as servico
from app.servicos import classificados_email, segundo_plano
from app.servicos import classificados_fotos as fotos
from app.servicos.armazenamento import Armazenado

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/classificados", dependencies=[Depends(exige_cabecalho_portal)])

Texto = Annotated[str | None, Query(max_length=LIMITE_TITULO)]


@rotas.get("/categorias")
def categorias(_: UnidadeLogada, db: Banco) -> ListaCategoriasClassificado:
    return ListaCategoriasClassificado(itens=servico.listar_categorias(db))


@rotas.get("")
def listar(
    logado: UnidadeLogada,
    db: Banco,
    bucket: Armazenado,
    tipo: TipoAnuncio | None = None,
    categoria: IdBanco | None = None,
    busca: Texto = None,
    com_aviso: bool = False,
) -> ListaClassificados:
    return servico.listar(
        db, logado, bucket, tipo=tipo, categoria=categoria, busca=busca, com_aviso=com_aviso
    )


@rotas.get("/meus")
def meus(logado: UnidadeLogada, db: Banco, bucket: Armazenado) -> MeusAnuncios:
    return MeusAnuncios(itens=servico.meus(db, logado, bucket))


@rotas.post("/fotos", status_code=201)
def pedir_foto(
    dados: PedirFoto, logado: UnidadeLogada, db: Banco, bucket: Armazenado
) -> FotoAutorizada:
    return fotos.pedir(db, logado, dados, bucket)


@rotas.post("/fotos/{foto_id}/confirmar")
def confirmar_foto(
    foto_id: IdBanco, logado: UnidadeLogada, db: Banco, bucket: Armazenado
) -> FotoEnviada:
    return fotos.confirmar(db, logado, foto_id, bucket)


@rotas.post("", status_code=201)
def anunciar(dados: NovoAnuncio, logado: UnidadeLogada, db: Banco) -> AnuncioCriado:
    return AnuncioCriado(id=servico.criar(db, logado, dados))


@rotas.get("/{anuncio_id}")
def abrir(anuncio_id: IdBanco, logado: UnidadeLogada, db: Banco, bucket: Armazenado) -> Anuncio:
    return servico.abrir(db, logado, bucket, anuncio_id)


@rotas.put("/{anuncio_id}")
def editar(
    anuncio_id: IdBanco, dados: NovoAnuncio, logado: UnidadeLogada, db: Banco, bucket: Armazenado
) -> Anuncio:
    servico.editar(db, logado, bucket, anuncio_id, dados)
    return servico.abrir(db, logado, bucket, anuncio_id)


@rotas.post("/{anuncio_id}/reservar")
def reservar(anuncio_id: IdBanco, logado: UnidadeLogada, db: Banco, bucket: Armazenado) -> Anuncio:
    servico.reservar(db, logado, anuncio_id)
    return servico.abrir(db, logado, bucket, anuncio_id)


@rotas.post("/{anuncio_id}/liberar")
def liberar(anuncio_id: IdBanco, logado: UnidadeLogada, db: Banco, bucket: Armazenado) -> Anuncio:
    servico.liberar(db, logado, anuncio_id)
    return servico.abrir(db, logado, bucket, anuncio_id)


@rotas.post("/{anuncio_id}/renovar")
def renovar(anuncio_id: IdBanco, logado: UnidadeLogada, db: Banco, bucket: Armazenado) -> Anuncio:
    servico.renovar(db, logado, anuncio_id)
    return servico.abrir(db, logado, bucket, anuncio_id)


@rotas.post("/{anuncio_id}/encerrar")
def encerrar(
    anuncio_id: IdBanco,
    dados: EncerrarAnuncio,
    logado: UnidadeLogada,
    db: Banco,
    bucket: Armazenado,
) -> Anuncio:
    servico.encerrar(db, logado, anuncio_id, dados.motivo)
    return servico.abrir(db, logado, bucket, anuncio_id)


@rotas.post("/{anuncio_id}/aviso", status_code=204)
def avisar(
    anuncio_id: IdBanco,
    logado: UnidadeLogada,
    db: Banco,
    tarefas: BackgroundTasks,
    dados: AvisarGestao | None = None,
) -> Response:
    aviso_id = servico.avisar(db, logado, anuncio_id, dados or AvisarGestao())
    # O primeiro aviso aberto do anúncio acorda a administração por e-mail (depois da resposta;
    # spec, seção 9).
    if aviso_id is not None:
        segundo_plano.agendar(tarefas, classificados_email.avisar_administracao, aviso_id)
    return Response(status_code=204)
