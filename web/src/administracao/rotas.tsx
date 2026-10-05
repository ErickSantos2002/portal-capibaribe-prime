// Épico B · Administração: rotas (spec do M1, seção 5.3). Pertence ao épico B.
// As telas abaixo são marcações de lugar: trocar cada `EmConstrucao` pela tela de verdade,
// mantendo os caminhos e as guardas.
import type { RouteObject } from 'react-router'
import { EmConstrucao } from '../casca/EmConstrucao'
import { ExigeAdmin, ExigeUnidade } from '../casca/guardas'

export const rotasAdministracao: RouteObject[] = [
  {
    element: <ExigeUnidade />,
    children: [
      {
        element: <ExigeAdmin />,
        children: [
          {
            path: 'unidades',
            element: <EmConstrucao titulo="Unidades" historia="H-07 · épico B" />,
          },
          {
            path: 'unidades/:login',
            element: (
              <EmConstrucao titulo="Unidade" historia="H-08 e H-09 · épico B" voltar="/unidades" />
            ),
          },
          {
            path: 'historico',
            element: <EmConstrucao titulo="Histórico" historia="H-11 · épico B" voltar="/unidades" />,
          },
        ],
      },
    ],
  },
]
