// Épico A do M2 · rotas (spec do M2, seção 7). Pertence ao épico A: a tela "Receber os avisos"
// (instalar e ativar notificações, com o passo a passo do iPhone).
import type { RouteObject } from 'react-router'
import { ExigeUnidade } from '../casca/guardas'
import { ReceberAvisos } from './ReceberAvisos'

export const rotasNotificacoes: RouteObject[] = [
  {
    element: <ExigeUnidade />,
    children: [{ path: 'receber-avisos', element: <ReceberAvisos /> }],
  },
]
