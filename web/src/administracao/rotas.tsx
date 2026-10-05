// Épico B · Administração: rotas (spec do M1, seção 5.3). Pertence ao épico B.
// Só o administrador (dúvida 9 do M1); a permissão de verdade é da API (RNF-13).
import type { RouteObject } from 'react-router'
import { ExigeAdmin, ExigeUnidade } from '../casca/guardas'
import { FichaUnidade } from './FichaUnidade'
import { Historico } from './Historico'
import { Painel } from './Painel'

export const rotasAdministracao: RouteObject[] = [
  {
    element: <ExigeUnidade />,
    children: [
      {
        element: <ExigeAdmin />,
        children: [
          { path: 'unidades', element: <Painel /> },
          { path: 'unidades/:login', element: <FichaUnidade /> },
          { path: 'historico', element: <Historico /> },
        ],
      },
    ],
  },
]
