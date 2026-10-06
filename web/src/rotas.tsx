// Todas as rotas do Portal. Arquivo comum: cada épico mexe só no próprio `rotas.tsx`, que é
// juntado aqui (spec do M1, seções 5.3 e 7).
import { Navigate, type RouteObject } from 'react-router'
import { rotasAcesso } from './acesso/rotas'
import { rotasAdministracao } from './administracao/rotas'
import { rotasAvisos } from './avisos/rotas'
import { NaoEncontrado } from './casca/guardas'
import { Raiz } from './casca/Raiz'
import { rotasNotificacoes } from './notificacoes/rotas'
import { rotasRecuperacao } from './recuperacao/rotas'

export const rotas: RouteObject[] = [
  {
    element: <Raiz />,
    children: [
      { index: true, element: <Navigate to="/avisos" replace /> },
      ...rotasAcesso,
      ...rotasAvisos,
      ...rotasAdministracao,
      // M2: épico A (notificações) e épico B (esqueci a senha).
      ...rotasNotificacoes,
      ...rotasRecuperacao,
      { path: '*', element: <NaoEncontrado /> },
    ],
  },
]
