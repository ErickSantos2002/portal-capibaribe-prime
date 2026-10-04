"""Carga inicial das 320 unidades. Uso, de dentro de `api/`:

    DATABASE_URL=<url do usuário app> PORTAL_ADMIN_UNIDADE=1101 \\
        uv run python -m app.comandos.carga_inicial

A unidade real do administrador vem só da variável (o repositório é público).
"""

import os
import sys

from argon2 import PasswordHasher

from app.banco import fabrica_de_sessoes
from app.servicos.carga_inicial import ErroCarga, carregar

HASHER = PasswordHasher()


def main() -> int:
    try:
        with fabrica_de_sessoes()() as sessao:
            resumo = carregar(sessao, os.environ.get("PORTAL_ADMIN_UNIDADE"), hasher=HASHER)
            sessao.commit()
    except ErroCarga as erro:
        print(f"Carga não feita: {erro}", file=sys.stderr)
        return 1
    print(
        f"Carga concluída: {resumo.blocos_criados} blocos e {resumo.unidades_criadas} unidades "
        f"criados; admin {'concedido' if resumo.admin_concedido else 'já existia'}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
