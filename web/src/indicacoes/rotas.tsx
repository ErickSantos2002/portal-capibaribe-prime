// Indicações · rotas (spec, seção 3). Juntadas em `src/rotas.tsx`. As fixas vêm antes de `:id`.
import type { RouteObject } from 'react-router'
import { ExigeAdmin, ExigeUnidade } from '../casca/guardas'
import { PaginaCategorias } from './Categorias'
import { ListaIndicacoes } from './Lista'
import { PaginaNovaIndicacao } from './NovaIndicacao'
import { PaginaIndicacao } from './PrestadorAberto'

export const rotasIndicacoes: RouteObject[] = [
  {
    element: <ExigeUnidade />,
    children: [
      { path: 'indicacoes', element: <ListaIndicacoes /> },
      { path: 'indicacoes/nova', element: <PaginaNovaIndicacao /> },
      {
        element: <ExigeAdmin />,
        children: [{ path: 'indicacoes/categorias', element: <PaginaCategorias /> }],
      },
      { path: 'indicacoes/:id', element: <PaginaIndicacao /> },
    ],
  },
]
