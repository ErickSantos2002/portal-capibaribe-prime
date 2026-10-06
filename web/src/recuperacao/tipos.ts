// Épico B do M2 · Esqueci a senha (docs/superpowers/specs/m2-contrato.md, seção 4.3).
// Pertence ao épico B. Espelho de api/app/esquemas/recuperacao.py: o teste
// api/testes/test_contrato.py confere os campos.
import type { UnidadeRef } from '../api/tipos'

/** `POST /api/acesso/recuperacao`. */
export interface PedirRecuperacao {
  login: string
}

/** Resposta 202, a mesma para qualquer apartamento (H-04: não revela se há e-mail). */
export interface RecuperacaoPedida {
  mensagem: string
}

/** `POST /api/acesso/recuperacao/conferir`: o token do link do e-mail. */
export interface LinkDeRecuperacao {
  token: string
}

export interface LinkValido {
  unidade: UnidadeRef
}

/** `POST /api/acesso/recuperacao/redefinir` (responde `Eu` e já deixa a pessoa entrada). */
export interface RedefinirSenha {
  token: string
  senha_nova: string
  senha_nova_repetida: string
}
