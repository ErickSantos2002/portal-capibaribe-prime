"""Contrato API × front: cada esquema Pydantic tem um tipo TypeScript com os mesmos campos.

Os tipos do front são escritos à mão (spec do M1, seção 4) e moram ao lado de cada épico. Este
teste pega o caso de alguém mudar uma das pontas e esquecer a outra: campo novo, campo
renomeado, valor de enum a mais.
"""

import enum
import inspect
import re
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.esquemas import acesso, administracao, avisos, comum
from app.modelos import Papel

WEB = Path(__file__).resolve().parents[2] / "web" / "src"
ARQUIVOS_TS = {
    comum: WEB / "api" / "tipos.ts",
    acesso: WEB / "acesso" / "tipos.ts",
    administracao: WEB / "administracao" / "tipos.ts",
    avisos: WEB / "avisos" / "tipos.ts",
}
BASES = {comum.Entrada, comum.Saida}

_INTERFACE = re.compile(r"export interface (\w+)(?: extends ([\w, ]+))? \{(.*?)\n\}", re.S)
_APELIDO = re.compile(r"export type (\w+) = ([A-Z]\w*)\s*$", re.M)
_UNIAO = re.compile(r"export type (\w+) = ((?:\s*\|?\s*'[^']*')+)\s*$", re.M)
_CAMPO = re.compile(r"^\s+(\w+)\??:", re.M)


def _ler_ts() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Campos de cada interface (com os herdados) e valores de cada união de textos."""
    proprios: dict[str, set[str]] = {}
    pais: dict[str, list[str]] = {}
    unioes: dict[str, set[str]] = {}
    for arquivo in ARQUIVOS_TS.values():
        texto = arquivo.read_text(encoding="utf-8")
        for nome, herda, corpo in _INTERFACE.findall(texto):
            proprios[nome] = set(_CAMPO.findall(corpo))
            pais[nome] = [p.strip() for p in herda.split(",")] if herda else []
        for nome, outro in _APELIDO.findall(texto):
            proprios[nome] = set()
            pais[nome] = [outro]
        for nome, valores in _UNIAO.findall(texto):
            unioes[nome] = set(re.findall(r"'([^']*)'", valores))

    def campos(nome: str) -> set[str]:
        return proprios[nome].union(*(campos(p) for p in pais[nome]))

    return {nome: campos(nome) for nome in proprios}, unioes


INTERFACES, UNIOES = _ler_ts()


def _definidos(modulo, tipo) -> list:
    return [
        obj
        for _, obj in inspect.getmembers(modulo, inspect.isclass)
        if issubclass(obj, tipo) and obj.__module__ == modulo.__name__ and obj not in BASES
    ]


ESQUEMAS = [(m, e) for m in ARQUIVOS_TS for e in _definidos(m, BaseModel)]
ENUMS = [Papel] + [e for m in ARQUIVOS_TS for e in _definidos(m, enum.Enum)]


@pytest.mark.parametrize(("modulo", "esquema"), ESQUEMAS, ids=lambda x: getattr(x, "__name__", ""))
def test_esquema_tem_tipo_ts_com_os_mesmos_campos(modulo, esquema):
    arquivo = ARQUIVOS_TS[modulo].relative_to(WEB.parent.parent)
    assert esquema.__name__ in INTERFACES, (
        f"falta `export interface {esquema.__name__}` em {arquivo}"
    )
    assert INTERFACES[esquema.__name__] == set(esquema.model_fields), arquivo


@pytest.mark.parametrize("enumeracao", ENUMS, ids=lambda e: e.__name__)
def test_enum_tem_uniao_ts_com_os_mesmos_valores(enumeracao):
    assert UNIOES.get(enumeracao.__name__) == {m.value for m in enumeracao}


def test_o_teste_enxerga_os_esquemas():
    # Se a leitura do TS quebrar em silêncio, os testes acima passariam sem conferir nada.
    assert len(ESQUEMAS) >= 30
    assert {"Eu", "MinhaUnidade", "PainelAtivacao", "AvisoCompleto"} <= set(INTERFACES)
    assert INTERFACES["AvisoCompleto"] >= {"id", "titulo", "texto", "leitura", "lido"}
