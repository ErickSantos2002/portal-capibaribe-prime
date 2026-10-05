"""Carga inicial das 320 unidades. Uso, de dentro de `api/`:

    DATABASE_URL=<url do usuário app> uv run python -m app.comandos.carga_inicial

Não dá papel nenhum. Depois que a unidade do administrador fizer o primeiro acesso:
`python -m app.comandos.promover_admin <login>` (spec do M1, seção 2.5).
"""

import sys

from argon2 import PasswordHasher

from app.banco import fabrica_de_sessoes
from app.servicos.carga_inicial import carregar

HASHER = PasswordHasher()


def main() -> int:
    with fabrica_de_sessoes()() as sessao:
        resumo = carregar(sessao, hasher=HASHER)
        sessao.commit()
    print(
        f"Carga concluída: {resumo.blocos_criados} blocos e {resumo.unidades_criadas} unidades "
        "criados. Nenhum papel foi dado: o administrador vem com "
        "`python -m app.comandos.promover_admin <login>`, depois do primeiro acesso dele."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
