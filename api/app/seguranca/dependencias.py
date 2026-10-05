"""Dependências FastAPI de sessão, permissão (RNF-13) e CSRF (ADR-0005).

Uso numa rota de épico:

    @rotas.post("/api/avisos", status_code=201)
    def publicar(dados: NovoAviso, logado: Gestao, db: Banco) -> AvisoCompleto: ...

Os papéis são lidos do banco a cada requisição: retirar o papel de Comissão vale na hora,
mesmo com a pessoa logada (H-09). Unidade desativada não tem sessão.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.banco import obter_sessao
from app.erros_api import ErroApi
from app.modelos import Bloco, Papel, Unidade, UnidadePapel
from app.seguranca.sessoes import NOME_COOKIE, buscar_sessao, gravar_cookie, renovar

PAPEIS_DE_GESTAO = frozenset({Papel.admin, Papel.comissao, Papel.sindico, Papel.conselho})
METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS"})

Banco = Annotated[Session, Depends(obter_sessao)]


@dataclass(frozen=True)
class Logado:
    sessao_id: int
    unidade_id: int
    login: str
    bloco: int
    apartamento: str
    papeis: frozenset[Papel]
    precisa_trocar_senha: bool

    @property
    def gestao(self) -> bool:
        return bool(self.papeis & PAPEIS_DE_GESTAO)

    @property
    def admin(self) -> bool:
        return Papel.admin in self.papeis


def _sem_sessao() -> ErroApi:
    return ErroApi(401, "sem_sessao", "Entre de novo com o bloco, o apartamento e a senha.")


def sessao_qualquer(request: Request, response: Response, db: Banco) -> Logado:
    """Qualquer sessão válida, inclusive a restrita do primeiro acesso."""
    token = request.cookies.get(NOME_COOKIE)
    sessao = buscar_sessao(db, token)
    if sessao is None or token is None:
        raise _sem_sessao()
    login, numero, bloco, precisa_trocar = db.execute(
        select(Unidade.login, Unidade.numero, Bloco.numero, Unidade.precisa_trocar_senha)
        .join(Bloco, Bloco.id == Unidade.bloco_id)
        .where(Unidade.id == sessao.unidade_id)
    ).one()
    papeis = frozenset(
        db.scalars(
            select(UnidadePapel.papel).where(
                UnidadePapel.unidade_id == sessao.unidade_id,
                UnidadePapel.retirado_em.is_(None),
            )
        )
    )
    if renovar(db, sessao):
        db.commit()
        gravar_cookie(response, token)
    # O registro de erros (tabela `erro`) anota quem estava logado.
    request.state.unidade_id = sessao.unidade_id
    return Logado(
        sessao_id=sessao.id,
        unidade_id=sessao.unidade_id,
        login=login,
        bloco=bloco,
        apartamento=numero,
        papeis=papeis,
        precisa_trocar_senha=precisa_trocar,
    )


def unidade_logada(logado: Annotated[Logado, Depends(sessao_qualquer)]) -> Logado:
    """Sessão completa: o primeiro acesso já foi concluído (ADR-0005, sessão restrita)."""
    if logado.precisa_trocar_senha:
        raise ErroApi(
            403, "primeiro_acesso_pendente", "Conclua o primeiro acesso antes de continuar."
        )
    return logado


def exige_gestao(logado: Annotated[Logado, Depends(unidade_logada)]) -> Logado:
    """Comissão, administrador, síndico ou conselho (papel em vigor)."""
    if not logado.gestao:
        raise ErroApi(
            403, "sem_permissao", "Esta função é só da Comissão e da administração do Portal."
        )
    return logado


def exige_admin(logado: Annotated[Logado, Depends(unidade_logada)]) -> Logado:
    """Só o administrador do sistema."""
    if not logado.admin:
        raise ErroApi(403, "sem_permissao", "Esta função é só da administração do Portal.")
    return logado


def exige_cabecalho_portal(request: Request) -> None:
    """CSRF (ADR-0005): toda alteração exige `X-Portal: 1`, que outro site não consegue mandar
    sem CORS. Vai em `dependencies=` de cada roteador de épico."""
    if request.method not in METODOS_SEGUROS and request.headers.get("x-portal") != "1":
        raise ErroApi(
            403,
            "requisicao_recusada",
            "Requisição recusada. Recarregue a página e tente de novo.",
        )


SessaoQualquer = Annotated[Logado, Depends(sessao_qualquer)]
UnidadeLogada = Annotated[Logado, Depends(unidade_logada)]
Gestao = Annotated[Logado, Depends(exige_gestao)]
Admin = Annotated[Logado, Depends(exige_admin)]
