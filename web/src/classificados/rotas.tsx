// Classificados · rotas (spec, seção 3). Juntadas em `src/rotas.tsx`. As fixas vêm antes de `:id`.
import type { RouteObject } from 'react-router'
import { ExigeAdmin, ExigeUnidade } from '../casca/guardas'
import { PaginaDeCategorias, type OrigemDasCategorias } from '../indicacoes/Categorias'
import { PaginaAnuncio } from './AnuncioAberto'
import { criarCategoria, listarCategoriasParaAdmin, renomearCategoria } from './api'
import { ListaClassificados } from './Lista'
import { PaginaMeusAnuncios } from './MeusAnuncios'
import { PaginaEditarAnuncio, PaginaNovoAnuncio } from './NovoAnuncio'

// A tela das categorias é a mesma das indicações, com as categorias dos classificados.
const DOS_CLASSIFICADOS: OrigemDasCategorias = {
  titulo: 'Categorias dos classificados',
  explicacao:
    'As categorias aparecem no filtro “Categoria” da lista de classificados e no formulário de anunciar. Uma categoria nova entra antes de “Outros”. Categoria não é apagada.',
  listar: listarCategoriasParaAdmin,
  criar: criarCategoria,
  renomear: renomearCategoria,
}

export const rotasClassificados: RouteObject[] = [
  {
    element: <ExigeUnidade />,
    children: [
      { path: 'classificados', element: <ListaClassificados /> },
      { path: 'classificados/novo', element: <PaginaNovoAnuncio /> },
      { path: 'classificados/meus', element: <PaginaMeusAnuncios /> },
      {
        element: <ExigeAdmin />,
        children: [
          {
            path: 'classificados/categorias',
            element: <PaginaDeCategorias origem={DOS_CLASSIFICADOS} />,
          },
        ],
      },
      { path: 'classificados/:id', element: <PaginaAnuncio /> },
      { path: 'classificados/:id/editar', element: <PaginaEditarAnuncio /> },
    ],
  },
]
