"""Dados fictícios para desenvolvimento (RNF-16). Uso, de dentro de `api/`, depois da carga:

PORTAL_AMBIENTE=local DATABASE_URL=<url local> uv run python -m app.comandos.dados_ficticios
"""

import os
import sys

from app.banco import fabrica_de_sessoes
from app.servicos.dados_ficticios import ErroAmbiente, preencher_ficticios


def main() -> int:
    try:
        with fabrica_de_sessoes()() as sessao:
            ativadas = preencher_ficticios(sessao, os.environ.get("PORTAL_AMBIENTE"))
            sessao.commit()
    except ErroAmbiente as erro:
        print(f"Nada feito: {erro}", file=sys.stderr)
        return 1
    print(f"Dados fictícios: {ativadas} unidades ativadas nesta rodada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
