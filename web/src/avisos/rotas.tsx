// Épico C · Avisos: rotas (spec do M1, seção 5.3). Pertence ao épico C.
// As telas abaixo são marcações de lugar: trocar cada `EmConstrucao` pela tela de verdade,
// mantendo os caminhos e as guardas. `contarNaoLidos` (./api.ts) é usada pela casca.
import type { RouteObject } from 'react-router'
import { EmConstrucao } from '../casca/EmConstrucao'
import { ExigeGestao, ExigeUnidade } from '../casca/guardas'

export const rotasAvisos: RouteObject[] = [
  {
    element: <ExigeUnidade />,
    children: [
      { path: 'avisos', element: <EmConstrucao titulo="Avisos" historia="H-14 · épico C" /> },
      {
        path: 'avisos/arquivados',
        element: (
          <EmConstrucao titulo="Avisos arquivados" historia="H-15 · épico C" voltar="/avisos" />
        ),
      },
      {
        path: 'avisos/:id',
        element: <EmConstrucao titulo="Aviso" historia="H-14 e H-15 · épico C" voltar="/avisos" />,
      },
      {
        element: <ExigeGestao />,
        children: [
          {
            path: 'avisos/novo',
            element: <EmConstrucao titulo="Novo aviso" historia="H-12 · épico C" voltar="/avisos" />,
          },
          {
            path: 'avisos/:id/corrigir',
            element: (
              <EmConstrucao titulo="Corrigir aviso" historia="H-15 · épico C" voltar="/avisos" />
            ),
          },
          {
            path: 'avisos/:id/leitura',
            element: <EmConstrucao titulo="Quem leu" historia="H-16 · épico C" voltar="/avisos" />,
          },
        ],
      },
    ],
  },
]
