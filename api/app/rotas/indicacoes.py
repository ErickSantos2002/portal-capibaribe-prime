"""Indicações de serviços: o que o morador faz (spec de 18/10/2026, seções 3 e 7).

Esquemas em `app/esquemas/indicacoes.py`; regras em `app/servicos/indicacoes.py`. A moderação
(gestão e administração) está em `indicacoes_gestao.py`, com o mesmo prefixo; os caminhos não se
cruzam. As rotas fixas vêm antes de `/{prestador_id}`.

- `GET  /api/indicacoes/categorias`              → `ListaCategorias`
- `GET  /api/indicacoes?categoria=&busca=&com_aviso=` → `ListaIndicacoes`
- `GET  /api/indicacoes/parecidos?nome=`         → `Parecidos`
- `POST /api/indicacoes`                         → 201 `IndicacaoCriada`
- `GET  /api/indicacoes/{id}`                    → `Prestador`
- `PUT  /api/indicacoes/{id}`                    → `Prestador` (quem indicou ou a gestão)
- `PUT  /api/indicacoes/{id}/opiniao`            → `Prestador`
- `DELETE /api/indicacoes/{id}/opiniao`          → 204
- `POST /api/indicacoes/{id}/aviso`              → 204

Só unidade logada e com o primeiro acesso concluído (`UnidadeLogada`). Prestador escondido: 404
para o morador, igual a um que não existe.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response

from app.esquemas.comum import IdBanco
from app.esquemas.indicacoes import (
    AvisarGestao,
    CorrigirPrestador,
    DarOpiniao,
    IndicacaoCriada,
    ListaCategorias,
    ListaIndicacoes,
    NovaIndicacao,
    Parecidos,
    Prestador,
)
from app.modelos.indicacoes import LIMITE_NOME
from app.seguranca.dependencias import Banco, UnidadeLogada, exige_cabecalho_portal
from app.servicos import indicacoes as servico

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/indicacoes", dependencies=[Depends(exige_cabecalho_portal)])

Texto = Annotated[str | None, Query(max_length=LIMITE_NOME)]


@rotas.get("/categorias")
def categorias(_: UnidadeLogada, db: Banco) -> ListaCategorias:
    return ListaCategorias(itens=servico.listar_categorias(db))


@rotas.get("")
def listar(
    logado: UnidadeLogada,
    db: Banco,
    categoria: IdBanco | None = None,
    busca: Texto = None,
    com_aviso: bool = False,
) -> ListaIndicacoes:
    return servico.listar(db, logado, categoria=categoria, busca=busca, com_aviso=com_aviso)


@rotas.get("/parecidos")
def parecidos(_: UnidadeLogada, db: Banco, nome: Texto = None) -> Parecidos:
    return Parecidos(itens=servico.parecidos(db, nome or ""))


@rotas.post("", status_code=201)
def indicar(dados: NovaIndicacao, logado: UnidadeLogada, db: Banco) -> IndicacaoCriada:
    return IndicacaoCriada(id=servico.criar(db, logado, dados))


@rotas.get("/{prestador_id}")
def abrir(prestador_id: IdBanco, logado: UnidadeLogada, db: Banco) -> Prestador:
    return servico.abrir(db, logado, prestador_id)


@rotas.put("/{prestador_id}")
def corrigir(
    prestador_id: IdBanco, dados: CorrigirPrestador, logado: UnidadeLogada, db: Banco
) -> Prestador:
    servico.corrigir(db, logado, prestador_id, dados)
    return servico.abrir(db, logado, prestador_id)


@rotas.put("/{prestador_id}/opiniao")
def opinar(prestador_id: IdBanco, dados: DarOpiniao, logado: UnidadeLogada, db: Banco) -> Prestador:
    servico.opinar(db, logado, prestador_id, dados)
    return servico.abrir(db, logado, prestador_id)


@rotas.delete("/{prestador_id}/opiniao", status_code=204)
def apagar_opiniao(prestador_id: IdBanco, logado: UnidadeLogada, db: Banco) -> Response:
    servico.apagar_opiniao(db, logado, prestador_id)
    return Response(status_code=204)


@rotas.post("/{prestador_id}/aviso", status_code=204)
def avisar(
    prestador_id: IdBanco,
    logado: UnidadeLogada,
    db: Banco,
    tarefas: BackgroundTasks,
    dados: AvisarGestao | None = None,
) -> Response:
    servico.avisar(db, logado, prestador_id, dados or AvisarGestao())
    return Response(status_code=204)
