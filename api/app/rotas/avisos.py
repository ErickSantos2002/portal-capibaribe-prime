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

GET nunca altera nada: com `SameSite=Lax`, uma navegação vinda de outro site leva o cookie e
escaparia da exigência de `X-Portal`. Por isso a leitura (H-16) é um POST à parte.

Modelos em `app/modelos/avisos.py`. O banco carimba as datas, exige versões em sequência e
confere no commit que o aviso tem versão 1 e destino (restrição `aviso_completo`).
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query

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
)
from app.seguranca.dependencias import Banco, Gestao, UnidadeLogada, exige_cabecalho_portal
from app.servicos import avisos as servico
from app.servicos import notificacoes

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
def alcance(_: Gestao, db: Banco, blocos: Annotated[list[int], Query()] = []) -> Alcance:  # noqa: B006
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
def abrir(aviso_id: int, logado: UnidadeLogada, db: Banco) -> AvisoCompleto:
    return servico.abrir(db, logado, aviso_id)


@rotas.post("/{aviso_id}/lido", status_code=204)
def marcar_lido(aviso_id: int, logado: UnidadeLogada, db: Banco) -> None:
    servico.marcar_lido(db, logado, aviso_id)


@rotas.put("/{aviso_id}")
def corrigir(aviso_id: int, dados: CorrigirAviso, logado: Gestao, db: Banco) -> AvisoCompleto:
    servico.corrigir(db, logado, aviso_id, dados)
    return servico.abrir(db, logado, aviso_id)


@rotas.post("/{aviso_id}/arquivar")
def arquivar(aviso_id: int, logado: Gestao, db: Banco) -> AvisoCompleto:
    servico.arquivar(db, logado, aviso_id)
    db.expire_all()
    return servico.abrir(db, logado, aviso_id)


@rotas.put("/{aviso_id}/fixado")
def mudar_fixado(aviso_id: int, dados: MudarFixado, logado: Gestao, db: Banco) -> AvisoCompleto:
    servico.mudar_fixado(db, logado, aviso_id, dados.fixado)
    return servico.abrir(db, logado, aviso_id)


@rotas.get("/{aviso_id}/leitura")
def leitura(aviso_id: int, logado: Gestao, db: Banco) -> Leitura:
    return servico.leitura(db, logado, aviso_id)
