// Épico B do M4 · Votar e resultado (H-21, H-22): rotas. Pertence ao épico B. Juntadas em
// `enquetes/rotas.tsx`. Endereços em `enquetes/caminhos.ts` (`/enquetes`, `/enquetes/:id`,
// `/enquetes/:id/votantes`), atrás de `ExigeUnidade` (votantes, de `ExigeGestao`).
import type { RouteObject } from 'react-router'
import { ExigeGestao, ExigeUnidade } from '../../casca/guardas'
import { PaginaEnquete } from './EnqueteAberta'
import { ListaEnquetes } from './Lista'
import { PaginaVotantes } from './Votantes'

export const rotasVotar: RouteObject[] = [
  {
    element: <ExigeUnidade />,
    children: [
      { path: 'enquetes', element: <ListaEnquetes /> },
      { path: 'enquetes/:id', element: <PaginaEnquete /> },
      {
        element: <ExigeGestao />,
        children: [{ path: 'enquetes/:id/votantes', element: <PaginaVotantes /> }],
      },
    ],
  },
]
