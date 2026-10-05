"""Dá o papel de administrador a uma unidade que já fez o primeiro acesso. Uso, de `api/`:

    DATABASE_URL=<url do usuário app> uv run python -m app.comandos.promover_admin <login>

Sequência de produção (spec do M1, seção 2.5): deploy → primeiro acesso do Erick na unidade
dele → este comando com o login dela. Idempotente; registra no histórico.
"""

import sys

from app.banco import fabrica_de_sessoes
from app.servicos.promover_admin import ErroPromocao, promover_admin


def main(argumentos: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    if len(argumentos) != 1:
        print("Uso: python -m app.comandos.promover_admin <login>  (ex.: 1101)", file=sys.stderr)
        return 2
    login = argumentos[0]
    try:
        with fabrica_de_sessoes()() as sessao:
            promovida = promover_admin(sessao, login)
            sessao.commit()
    except ErroPromocao as erro:
        print(f"Nada feito: {erro}", file=sys.stderr)
        return 1
    if promovida:
        print(f"Unidade {login} agora é administradora do Portal.")
    else:
        print(f"Unidade {login} já era administradora. Nada mudou.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
