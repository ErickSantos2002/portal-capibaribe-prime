"""Quem vê qual nível de documento (RF-31; spec do M3, seção 5.2). Arquivo comum.

- sem sessão, ou com a sessão restrita do primeiro acesso: só `publico`;
- unidade comum: `publico` e `compradores`;
- gestão (Comissão, administrador, síndico, conselho): os três.

Fora disso, a resposta é 404, igual a documento inexistente: o de nível `gestao` não aparece nem
abre por link direto para a conta comum (critério do roadmap, M3).
"""

from app.seguranca.dependencias import Logado


def niveis_que_ve(logado: Logado | None) -> tuple[str, ...]:
    if logado is None or logado.precisa_trocar_senha:
        return ("publico",)
    if logado.gestao:
        return ("publico", "compradores", "gestao")
    return ("publico", "compradores")
