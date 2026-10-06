"""Contrato API × front: cada esquema Pydantic tem um tipo TypeScript igual.

Os tipos do front são escritos à mão (spec do M1, seção 4) e moram ao lado de cada épico. Para
cada campo, este teste confere nome, tipo básico (texto, número, booleano, data, lista, objeto
do contrato, enum, literal), se aceita nulo (`X | None` ↔ `X | null`) e se é opcional (campo
com valor padrão ↔ `campo?:`). Também confere que cada enum tem a mesma união de textos.
"""

import enum
import inspect
import json
import re
import types
import typing
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, Union

import pytest
from pydantic import BaseModel

from app.esquemas import acesso, administracao, avisos, comum
from app.modelos import Canal, Papel, SituacaoEnvio

WEB = Path(__file__).resolve().parents[2] / "web" / "src"
ARQUIVOS_TS = {
    comum: WEB / "api" / "tipos.ts",
    acesso: WEB / "acesso" / "tipos.ts",
    administracao: WEB / "administracao" / "tipos.ts",
    avisos: WEB / "avisos" / "tipos.ts",
}
BASES = {comum.Entrada, comum.Saida}
# Apelidos de tipo do front que valem o tipo básico.
APELIDOS_TS = {"DataHora": "string"}

_INTERFACE = re.compile(r"export interface (\w+)(?: extends ([\w, ]+))? \{(.*?)\n\}", re.S)
_APELIDO = re.compile(r"export type (\w+) = ([A-Z]\w*)\s*$", re.M)
_UNIAO = re.compile(r"export type (\w+) = ((?:\s*\|?\s*'[^']*')+)\s*$", re.M)
_CAMPO = re.compile(r"^\s+(\w+)(\??):\s*(.+?)\s*$", re.M)


# --- lado TypeScript ---------------------------------------------------------------------------


def _uniao(tipo: str) -> frozenset[str]:
    """`string | null` → {'string', 'null'}; apelidos viram o tipo básico."""
    partes = [p.strip() for p in tipo.split("|") if p.strip()]
    return frozenset(APELIDOS_TS.get(p, p) for p in partes)


Campo = tuple[frozenset[str], bool]  # (membros da união, opcional)


def _ler_ts() -> tuple[dict[str, dict[str, Campo]], dict[str, set[str]]]:
    proprios: dict[str, dict[str, Campo]] = {}
    pais: dict[str, list[str]] = {}
    unioes: dict[str, set[str]] = {}
    for arquivo in ARQUIVOS_TS.values():
        texto = arquivo.read_text(encoding="utf-8")
        for nome, herda, corpo in _INTERFACE.findall(texto):
            proprios[nome] = {
                campo: (_uniao(tipo), opcional == "?")
                for campo, opcional, tipo in _CAMPO.findall(corpo)
            }
            pais[nome] = [p.strip() for p in herda.split(",")] if herda else []
        for nome, outro in _APELIDO.findall(texto):
            proprios[nome] = {}
            pais[nome] = [outro]
        for nome, valores in _UNIAO.findall(texto):
            unioes[nome] = set(re.findall(r"'([^']*)'", valores))

    def campos(nome: str) -> dict[str, Campo]:
        herdados: dict[str, Campo] = {}
        for pai in pais[nome]:
            herdados.update(campos(pai))
        return {**herdados, **proprios[nome]}

    return {nome: campos(nome) for nome in proprios}, unioes


INTERFACES, UNIOES = _ler_ts()


# --- lado Python -------------------------------------------------------------------------------


def _ts(anotacao: Any) -> frozenset[str]:
    """O tipo TS que corresponde a uma anotação Python, como união de membros."""
    origem, argumentos = typing.get_origin(anotacao), typing.get_args(anotacao)
    if origem is Annotated:
        return _ts(argumentos[0])
    if origem in (Union, types.UnionType):
        membros: set[str] = set()
        for argumento in argumentos:
            membros |= {"null"} if argumento is type(None) else _ts(argumento)
        return frozenset(membros)
    if origem is list:
        interno = _ts(argumentos[0])
        texto = " | ".join(sorted(interno))
        return frozenset({f"({texto})[]" if len(interno) > 1 else f"{texto}[]"})
    if origem is dict:
        return frozenset({"Record<string, unknown>"})
    if origem is Literal:
        return frozenset(
            json.dumps(v) if isinstance(v, str) else str(v).lower() for v in argumentos
        )
    if anotacao is str or anotacao in (datetime, date):
        return frozenset({"string"})
    if anotacao in (int, float):
        return frozenset({"number"})
    if anotacao is bool:
        return frozenset({"boolean"})
    if inspect.isclass(anotacao) and issubclass(anotacao, (BaseModel, enum.Enum)):
        return frozenset({anotacao.__name__})
    raise AssertionError(f"tipo sem correspondência no teste do contrato: {anotacao!r}")


def _python(esquema: type[BaseModel]) -> dict[str, Campo]:
    return {
        nome: (_ts(campo.annotation), not campo.is_required())
        for nome, campo in esquema.model_fields.items()
    }


def _definidos(modulo, tipo) -> list:
    return [
        obj
        for _, obj in inspect.getmembers(modulo, inspect.isclass)
        if issubclass(obj, tipo) and obj.__module__ == modulo.__name__ and obj not in BASES
    ]


ESQUEMAS = [(m, e) for m in ARQUIVOS_TS for e in _definidos(m, BaseModel)]
ENUMS = [Papel, Canal, SituacaoEnvio] + [e for m in ARQUIVOS_TS for e in _definidos(m, enum.Enum)]


@pytest.mark.parametrize(("modulo", "esquema"), ESQUEMAS, ids=lambda x: getattr(x, "__name__", ""))
def test_esquema_tem_tipo_ts_igual(modulo, esquema):
    arquivo = ARQUIVOS_TS[modulo].relative_to(WEB.parent.parent)
    assert esquema.__name__ in INTERFACES, (
        f"falta `export interface {esquema.__name__}` em {arquivo}"
    )
    assert INTERFACES[esquema.__name__] == _python(esquema), arquivo


@pytest.mark.parametrize("enumeracao", ENUMS, ids=lambda e: e.__name__)
def test_enum_tem_uniao_ts_com_os_mesmos_valores(enumeracao):
    assert UNIOES.get(enumeracao.__name__) == {m.value for m in enumeracao}


def test_o_teste_enxerga_os_esquemas():
    # Se a leitura do TS quebrar em silêncio, os testes acima passariam sem conferir nada.
    assert len(ESQUEMAS) >= 30
    assert {"Eu", "MinhaUnidade", "PainelAtivacao", "AvisoCompleto"} <= set(INTERFACES)
    assert INTERFACES["MinhaUnidade"]["email"] == (frozenset({"string", "null"}), False)
    assert INTERFACES["UnidadeRef"]["bloco"] == (frozenset({"number"}), False)
    assert INTERFACES["NovoAviso"]["blocos"] == (frozenset({"number[]"}), True)
    assert _python(comum.ErroResposta)["campos"] == (
        frozenset({"CampoInvalido[]", "null"}),
        True,
    )
