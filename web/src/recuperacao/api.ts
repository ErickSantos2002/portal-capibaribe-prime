// Épico B do M2 · uma função por rota do contrato (spec do M2, seção 4.3). Pertence ao épico B.
// Rotas sem sessão, mas com o `X-Portal: 1` que o cliente manda sempre.
import { api } from '../api/cliente'
import type { Eu } from '../api/tipos'
import type {
  LinkDeRecuperacao,
  LinkValido,
  PedirRecuperacao,
  RecuperacaoPedida,
  RedefinirSenha,
} from './tipos'

export const pedirRecuperacao = (login: string) =>
  api.post<RecuperacaoPedida>('/api/acesso/recuperacao', { login } satisfies PedirRecuperacao)

export const conferirLink = (token: string) =>
  api.post<LinkValido>('/api/acesso/recuperacao/conferir', { token } satisfies LinkDeRecuperacao)

export const redefinirSenha = (dados: RedefinirSenha) =>
  api.post<Eu>('/api/acesso/recuperacao/redefinir', dados)
