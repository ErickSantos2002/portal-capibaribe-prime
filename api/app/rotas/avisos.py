"""Épico C · Avisos, só texto (H-12, H-14, H-15, H-16). Pertence ao épico C.

Contrato: `docs/superpowers/specs/m1-contrato.md`, seção 4.4. Esquemas em
`app/esquemas/avisos.py`; regras de negócio em `app/servicos/avisos.py`.

Rotas (atenção à ordem: as fixas antes de `/{aviso_id}`):
- `GET  /api/avisos?busca=&arquivados=`   → `ListaAvisos` (`UnidadeLogada`)
- `GET  /api/avisos/nao-lidos`            → `ContagemNaoLidos` (`UnidadeLogada`)
- `GET  /api/avisos/alcance?blocos=`      → `Alcance` (`Gestao`)
- `GET  /api/avisos/destinos`             → `Destinos` (`Gestao`; rota a mais do épico C)
- `GET  /api/avisos/{aviso_id}`           → `AvisoCompleto`; só lê, não grava nada
- `POST /api/avisos/{aviso_id}/lido`      → 204, idempotente; a 1ª vez conta (`UnidadeLogada`)
- `POST /api/avisos`                      → 201 `AvisoCompleto` (`Gestao`)
- `PUT  /api/avisos/{aviso_id}`           → `AvisoCompleto`, versão nova (`Gestao`)
- `POST /api/avisos/{aviso_id}/arquivar`  → `AvisoCompleto` (`Gestao`)
- `PUT  /api/avisos/{aviso_id}/fixado`    → `AvisoCompleto` (`Gestao`)
- `GET  /api/avisos/{aviso_id}/leitura`   → `Leitura` (`Gestao`)
- `GET  /api/avisos/{aviso_id}/anexos/{arquivo_id}/link?baixar=` → `LinkDoArquivo`
  (`UnidadeLogada`; M3, épico B)
- `GET  /api/avisos/{aviso_id}/anexos/{arquivo_id}/abrir` → 302 para um link novo, ou página
  HTML com o erro (`UnidadeLogada`; M3, épico B)

M3 (épico B; spec do M3, seção 5.3, e `m3-anexos.md`): publicar e corrigir aceitam `anexos`
(até 5 arquivos enviados por `POST /api/arquivos`); sem anexos, tudo igual ao M1.

GET nunca altera nada: com `SameSite=Lax`, uma navegação vinda de outro site leva o cookie e
escaparia da exigência de `X-Portal`. Por isso a leitura (H-16) é um POST à parte.

Modelos em `app/modelos/avisos.py`. O banco carimba as datas, exige versões em sequência e
confere no commit que o aviso tem versão 1 e destino (restrição `aviso_completo`).
"""

import html
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from app.erros_api import ErroApi
from app.esquemas.arquivos import LinkDoArquivo
from app.esquemas.avisos import (
    Alcance,
    AvisoCompleto,
    Busca,
    ContagemNaoLidos,
    CorrigirAviso,
    Destinos,
    Leitura,
    ListaAvisos,
    MudarFixado,
    NovoAviso,
    NumeroDeBloco,
)
from app.esquemas.comum import IdBanco
from app.seguranca.dependencias import Banco, Gestao, UnidadeLogada, exige_cabecalho_portal
from app.servicos import avisos as servico
from app.servicos import notificacoes
from app.servicos.armazenamento import Armazenado

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/avisos", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.get("")
def listar(
    logado: UnidadeLogada,
    db: Banco,
    busca: Annotated[Busca, Query(max_length=100)] = "",
    arquivados: bool = False,
) -> ListaAvisos:
    return ListaAvisos(itens=servico.listar(db, logado, busca=busca, arquivados=arquivados))


@rotas.get("/nao-lidos")
def nao_lidos(logado: UnidadeLogada, db: Banco) -> ContagemNaoLidos:
    return ContagemNaoLidos(quantidade=servico.contar_nao_lidos(db, logado))


@rotas.get("/alcance")
def alcance(_: Gestao, db: Banco, blocos: Annotated[list[NumeroDeBloco], Query()] = []) -> Alcance:  # noqa: B006
    return Alcance(unidades=servico.alcance(db, sorted(set(blocos))))


@rotas.get("/destinos")
def destinos(_: Gestao, db: Banco) -> Destinos:
    return Destinos(blocos=servico.destinos(db))


@rotas.post("", status_code=201)
def publicar(
    dados: NovoAviso, logado: Gestao, db: Banco, tarefas: BackgroundTasks
) -> AvisoCompleto:
    aviso_id = servico.publicar(db, logado, dados)
    # H-13 (M2): push e e-mail saem depois da resposta (spec do M2, seção 5).
    notificacoes.agendar(tarefas, aviso_id)
    return servico.abrir(db, logado, aviso_id)


@rotas.get("/{aviso_id}")
def abrir(aviso_id: IdBanco, logado: UnidadeLogada, db: Banco) -> AvisoCompleto:
    return servico.abrir(db, logado, aviso_id)


@rotas.post("/{aviso_id}/lido", status_code=204)
def marcar_lido(aviso_id: IdBanco, logado: UnidadeLogada, db: Banco) -> None:
    servico.marcar_lido(db, logado, aviso_id)


@rotas.put("/{aviso_id}")
def corrigir(aviso_id: IdBanco, dados: CorrigirAviso, logado: Gestao, db: Banco) -> AvisoCompleto:
    servico.corrigir(db, logado, aviso_id, dados)
    return servico.abrir(db, logado, aviso_id)


@rotas.post("/{aviso_id}/arquivar")
def arquivar(aviso_id: IdBanco, logado: Gestao, db: Banco) -> AvisoCompleto:
    servico.arquivar(db, logado, aviso_id)
    db.expire_all()
    return servico.abrir(db, logado, aviso_id)


@rotas.put("/{aviso_id}/fixado")
def mudar_fixado(aviso_id: IdBanco, dados: MudarFixado, logado: Gestao, db: Banco) -> AvisoCompleto:
    servico.mudar_fixado(db, logado, aviso_id, dados.fixado)
    return servico.abrir(db, logado, aviso_id)


@rotas.get("/{aviso_id}/leitura")
def leitura(aviso_id: IdBanco, logado: Gestao, db: Banco) -> Leitura:
    return servico.leitura(db, logado, aviso_id)


# Ids das rotas dos anexos: fora do `bigint`, 422 (revisão do épico B, C5); desde o fechamento do
# M3, o tipo comum, em toda rota com id.
IdNaRota = IdBanco


@rotas.get("/{aviso_id}/anexos/{arquivo_id}/link")
def link_do_anexo(
    aviso_id: IdNaRota,
    arquivo_id: IdNaRota,
    logado: UnidadeLogada,
    db: Banco,
    bucket: Armazenado,
    baixar: bool = False,
) -> LinkDoArquivo:
    # M3, épico B: o aviso visível para a unidade e o arquivo anexo de alguma versão dele; senão
    # 404 `aviso_nao_encontrado`. Sem bucket, 503 depois dessas conferências.
    return servico.link_do_anexo(db, logado, aviso_id, arquivo_id, bucket, baixar=baixar)


def _pagina_de_erro(erro: ErroApi) -> HTMLResponse:
    """O erro numa página simples: quem abriu o anexo está numa aba nova (ou numa <img>), não na
    tela do Portal, e um JSON não diria nada à Dona Socorro."""
    mensagem = html.escape(erro.mensagem)
    corpo = (
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Portal Capibaribe Prime</title>"
        f"<h1>Não deu para abrir o arquivo</h1><p>{mensagem}</p>"
        "<p>Feche esta aba e volte ao Portal.</p></html>"
    )
    return HTMLResponse(corpo, status_code=erro.status)


# No OpenAPI e nas listas do contrato (`test_m3_rotas.py`, `test_cache.py`) desde o fechamento
# do M3 (dúvida 11 do épico B).
@rotas.get(
    "/{aviso_id}/anexos/{arquivo_id}/abrir",
    response_class=RedirectResponse,
    status_code=302,
    responses={404: {"description": "Página HTML com a frase do erro"}},
)
def abrir_anexo(
    aviso_id: IdNaRota,
    arquivo_id: IdNaRota,
    logado: UnidadeLogada,
    db: Banco,
    bucket: Armazenado,
):
    """Revisão do épico B, U12: a tela abre o anexo por aqui (`<img src>` e o botão do PDF numa
    aba nova). A sessão vai no cookie da navegação; cada pedido confere quem vê e redireciona
    para um link **novo**: a foto e o PDF abrem mesmo com a página do aviso aberta há horas.
    Depois do redirecionamento a aba mostra o endereço do R2, que vale 1 hora (fechamento do M3):
    recarregar essa aba dentro de 1 hora funciona; depois disso, tocar de novo no Portal. A
    resposta sai com `no-store`, como toda a API."""
    try:
        link = servico.link_do_anexo(db, logado, aviso_id, arquivo_id, bucket, baixar=False)
    except ErroApi as erro:
        return _pagina_de_erro(erro)
    return RedirectResponse(link.url, status_code=302)
