"""Apoio dos testes do épico B do M4 (não tem testes; o nome segue a posse de arquivos do épico).

Enquetes criadas direto no banco, no prédio de teste (`predio`), com as funções comuns de
`apoio_m4.py`: o épico B não depende da rota de criar, que é do épico A. Personagens: 1101 admin
(Bloco 1), 2304 Comissão (Bloco 2), 1203 comum (Bloco 1), 4203 não ativada (Bloco 4).
"""

from dataclasses import dataclass

from sqlalchemy import Engine, text

from testes.apoio_m4 import criar_enquete, opcoes_da_enquete, votar
from testes.conftest import ADMIN, COMISSAO, COMUM, NAO_ATIVADA

__all__ = [
    "ADMIN",
    "COMISSAO",
    "COMUM",
    "NAO_ATIVADA",
    "Criada",
    "nova",
    "vencer",
    "votar_no_banco",
]


@dataclass(frozen=True)
class Criada:
    id: int
    opcoes: list[int]
    aviso_id: int


def nova(
    engine: Engine,
    predio: dict[str, int],
    *,
    blocos: tuple[int, ...] = (),
    multipla: bool = False,
    so_no_fim: bool = False,
    opcoes: tuple[str, ...] = ("Terça à noite", "Quinta à noite", "Sábado de manhã"),
    pergunta: str = "Qual o melhor dia para a reunião?",
    dias: int = 7,
) -> Criada:
    """Cria a enquete inteira (aviso, opções, destino) pela Comissão. `blocos` são números."""
    with engine.begin() as con:
        ids_dos_blocos = tuple(
            con.execute(
                text("select id from bloco where numero = any(:n) order by numero"),
                {"n": list(blocos)},
            ).scalars()
        )
        e = criar_enquete(
            con,
            predio[COMISSAO],
            blocos=ids_dos_blocos,
            multipla=multipla,
            opcoes=opcoes,
            pergunta=pergunta,
            encerra=f"now() + interval '{dias} days'",
        )
        if so_no_fim:
            con.execute(
                text("update enquete set mostrar_resultado = 'so_no_fim' where id = :e"), {"e": e}
            )
        aviso = con.execute(text("select aviso_id from enquete where id = :e"), {"e": e})
        return Criada(id=e, opcoes=opcoes_da_enquete(con, e), aviso_id=aviso.scalar_one())


def vencer(engine_superusuario: Engine, enquete: int, *, minutos: int = 1) -> None:
    """Simula o prazo passando (há `minutos`): só o superusuário consegue, sem as triggers."""
    with engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(
            text(
                "update enquete set encerra_em = now() - make_interval(mins => :m),"
                " criada_em = now() - interval '30 days' where id = :e"
            ),
            {"e": enquete, "m": minutos},
        )


def votar_no_banco(engine: Engine, enquete: int, unidade: int, *opcoes: int) -> None:
    with engine.begin() as con:
        votar(con, enquete, unidade, *opcoes)
