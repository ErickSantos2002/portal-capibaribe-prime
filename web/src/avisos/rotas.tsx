// Épico C · Avisos: rotas (spec do M1, seção 5.3). Pertence ao épico C.
// `contarNaoLidos` (./api.ts) é usada pela casca no número da aba "Avisos".
import type { RouteObject } from 'react-router'
import { ExigeGestao, ExigeUnidade } from '../casca/guardas'
import { PaginaAviso } from './AvisoAberto'
import { NovoAviso, PaginaCorrigir } from './Formularios'
import { Mural } from './Mural'
import { PaginaQuemLeu } from './QuemLeu'

export const rotasAvisos: RouteObject[] = [
  {
    element: <ExigeUnidade />,
    children: [
      { path: 'avisos', element: <Mural /> },
      { path: 'avisos/arquivados', element: <Mural key="arquivados" arquivados /> },
      { path: 'avisos/:id', element: <PaginaAviso /> },
      {
        element: <ExigeGestao />,
        children: [
          { path: 'avisos/novo', element: <NovoAviso /> },
          { path: 'avisos/:id/corrigir', element: <PaginaCorrigir /> },
          { path: 'avisos/:id/leitura', element: <PaginaQuemLeu /> },
        ],
      },
    ],
  },
]
