// Épico A do M3 · rotas (spec do épico, seção 3). Pertence ao épico A. Juntadas em
// `src/rotas.tsx`. Os públicos ficam fora das guardas: são para quem ainda não entrou.
import type { RouteObject } from 'react-router'
import { ExigeGestao, ExigeUnidade } from '../casca/guardas'
import { PaginaDocumento } from './DocumentoAberto'
import { NovoDocumento, PaginaNovaVersao } from './Formularios'
import { ListaDocumentos } from './Lista'
import { DocumentosPublicos } from './Publicos'

export const rotasDocumentos: RouteObject[] = [
  { path: 'documentos/publicos', element: <DocumentosPublicos /> },
  {
    element: <ExigeUnidade />,
    children: [
      { path: 'documentos', element: <ListaDocumentos /> },
      { path: 'documentos/:id', element: <PaginaDocumento /> },
      {
        element: <ExigeGestao />,
        children: [
          {
            path: 'documentos/arquivados',
            element: <ListaDocumentos key="arquivados" arquivados />,
          },
          { path: 'documentos/novo', element: <NovoDocumento /> },
          { path: 'documentos/:id/nova-versao', element: <PaginaNovaVersao /> },
        ],
      },
    ],
  },
]
