// Épico B · Administração: rotas (spec do M1, seção 5.3). Pertence ao épico B.
// Painel e ficha para a gestão, só leitura (a Comissão vê os contatos, decisão do Erick em
// 06/10/2026); histórico só do administrador. A permissão de verdade é da API (RNF-13).
import type { RouteObject } from 'react-router'
import { ExigeAdmin, ExigeGestao, ExigeUnidade } from '../casca/guardas'
import { FichaUnidade } from './FichaUnidade'
import { Historico } from './Historico'
import { Painel } from './Painel'

export const rotasAdministracao: RouteObject[] = [
  {
    element: <ExigeUnidade />,
    children: [
      {
        element: <ExigeGestao />,
        children: [
          { path: 'unidades', element: <Painel /> },
          { path: 'unidades/:login', element: <FichaUnidade /> },
        ],
      },
      {
        element: <ExigeAdmin />,
        children: [{ path: 'historico', element: <Historico /> }],
      },
    ],
  },
]
