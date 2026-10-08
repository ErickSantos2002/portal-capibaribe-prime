"""Épico A · Acesso (H-01, H-02, H-03, H-06). Pertence ao épico A.

Contrato: `docs/superpowers/specs/m1-contrato.md`, seção 4.2; spec do épico:
`docs/superpowers/specs/m1-acesso.md`. As rotas são finas: chamam `app.servicos.acesso`, fazem
o commit e gravam ou apagam o cookie.

`GET /api/acesso/eu` e `POST /api/acesso/sair` são comuns e estão em `app/rotas/sessao.py`.
"""

from fastapi import APIRouter, Depends, Request, Response

from app.esquemas.acesso import (
    ApagarDados,
    AvisosPorEmail,
    DadosDaUnidade,
    Entrar,
    MinhaUnidade,
    PrimeiroAcesso,
    TrocarSenha,
)
from app.esquemas.comum import Eu
from app.seguranca.dependencias import (
    Banco,
    SessaoQualquer,
    UnidadeLogada,
    exige_cabecalho_portal,
)
from app.seguranca.ip import hash_do_ip, ip_do_cliente
from app.seguranca.sessoes import apagar_cookie, gravar_cookie
from app.servicos import acesso

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(dependencies=[Depends(exige_cabecalho_portal)])


@rotas.post("/api/acesso/entrar")
def entrar(dados: Entrar, request: Request, resposta: Response, db: Banco) -> Eu:
    try:
        eu, token = acesso.entrar(
            db,
            dados.login,
            dados.senha,
            hash_do_ip(ip_do_cliente(request)),
            request.headers.get("user-agent"),
        )
    except acesso.ErroEntrar:
        # A tentativa errada e o bloqueio valem mesmo com a resposta de erro (H-03).
        db.commit()
        raise
    db.commit()
    gravar_cookie(resposta, token)
    return eu


@rotas.post("/api/acesso/primeiro-acesso")
def primeiro_acesso(
    dados: PrimeiroAcesso, logado: SessaoQualquer, request: Request, resposta: Response, db: Banco
) -> Eu:
    eu, token = acesso.concluir_primeiro_acesso(
        db, logado.unidade_id, dados, request.headers.get("user-agent")
    )
    db.commit()
    gravar_cookie(resposta, token)
    return eu


# --- Minha unidade (H-06) -------------------------------------------------------------------------


@rotas.get("/api/minha-unidade")
def minha_unidade(logado: UnidadeLogada, resposta: Response, db: Banco) -> MinhaUnidade:
    return acesso.ver_minha_unidade(db, logado)


@rotas.put("/api/minha-unidade/dados")
def salvar_dados(
    dados: DadosDaUnidade, logado: UnidadeLogada, resposta: Response, db: Banco
) -> MinhaUnidade:
    acesso.salvar_dados(db, logado, dados)
    db.commit()
    return acesso.ver_minha_unidade(db, logado)


@rotas.put("/api/minha-unidade/avisos-por-email")
def mudar_avisos_por_email(
    dados: AvisosPorEmail, logado: UnidadeLogada, resposta: Response, db: Banco
) -> MinhaUnidade:
    acesso.mudar_avisos_por_email(db, logado, dados.receber)
    db.commit()
    return acesso.ver_minha_unidade(db, logado)


@rotas.put("/api/minha-unidade/senha", status_code=204)
def trocar_senha(
    dados: TrocarSenha, logado: UnidadeLogada, request: Request, resposta: Response, db: Banco
) -> None:
    token = acesso.trocar_senha(db, logado, dados, request.headers.get("user-agent"))
    db.commit()
    gravar_cookie(resposta, token)


@rotas.delete("/api/minha-unidade/aparelhos/{sessao_id}", status_code=204)
def desconectar_aparelho(
    sessao_id: int, logado: UnidadeLogada, resposta: Response, db: Banco
) -> None:
    acesso.desconectar_aparelho(db, logado, sessao_id)
    db.commit()
    if sessao_id == logado.sessao_id:
        apagar_cookie(resposta)


@rotas.post("/api/minha-unidade/apagar-dados", status_code=204)
def apagar_dados(
    dados: ApagarDados, logado: UnidadeLogada, request: Request, resposta: Response, db: Banco
) -> None:
    try:
        acesso.apagar_dados(db, logado, dados.senha, hash_do_ip(ip_do_cliente(request)))
    except acesso.ErroEntrar:
        # Senha errada conta para o bloqueio daquele IP (revisão do M1, C1).
        db.commit()
        raise
    db.commit()
    apagar_cookie(resposta)
