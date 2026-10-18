// Indicações · rotas (spec, seção 3). Juntadas em `src/rotas.tsx`. As fixas vêm antes de `:id`.
import type { RouteObject } from 'react-router'
import { ExigeUnidade } from '../casca/guardas'
import { ListaIndicacoes } from './Lista'
import { PaginaNovaIndicacao } from './NovaIndicacao'
import { PaginaIndicacao } from './PrestadorAberto'

export const rotasIndicacoes: RouteObject[] = [
  {
    element: <ExigeUnidade />,
    children: [
      { path: 'indicacoes', element: <ListaIndicacoes /> },
      { path: 'indicacoes/nova', element: <PaginaNovaIndicacao /> },
      { path: 'indicacoes/:id', element: <PaginaIndicacao /> },
    ],
  },
]
