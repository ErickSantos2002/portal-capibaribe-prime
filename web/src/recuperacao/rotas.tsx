// Épico B do M2 · rotas (spec do M2, seção 7). Pertence ao épico B: "Esqueci minha senha"
// (`/esqueci-a-senha`, só sem sessão, como a entrada) e "Criar senha nova" (`/redefinir-senha`,
// pública: o link do e-mail pode abrir num aparelho já conectado).
import type { RouteObject } from 'react-router'
import { SoSemSessao } from '../casca/guardas'
import { EsqueciASenha } from './EsqueciASenha'
import { RedefinirSenha } from './RedefinirSenha'

export const rotasRecuperacao: RouteObject[] = [
  {
    element: <SoSemSessao />,
    children: [{ path: 'esqueci-a-senha', element: <EsqueciASenha /> }],
  },
  { path: 'redefinir-senha', element: <RedefinirSenha /> },
]
