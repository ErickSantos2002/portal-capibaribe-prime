// Épico A do M4 · Criar e gerir enquetes (H-20): rotas. Pertence ao épico A. Juntadas em
// `enquetes/rotas.tsx` (antes das do épico B: `/enquetes/nova` não pode cair em
// `/enquetes/:id`). Endereços em `enquetes/caminhos.ts`, atrás de `ExigeGestao`.
import type { RouteObject } from 'react-router'
import { ExigeGestao, ExigeUnidade } from '../../casca/guardas'
import { CAMINHO_NOVA_ENQUETE } from '../caminhos'
import { NovaEnquete, PaginaEditarEnquete } from './Paginas'

export const rotasGestaoEnquetes: RouteObject[] = [
  {
    element: <ExigeUnidade />,
    children: [
      {
        element: <ExigeGestao />,
        children: [
          { path: CAMINHO_NOVA_ENQUETE.slice(1), element: <NovaEnquete /> },
          // `caminhoEditarEnquete(id)`.
          { path: 'enquetes/:id/editar', element: <PaginaEditarEnquete /> },
        ],
      },
    ],
  },
]
