// Épico A · Acesso: rotas (spec do M1, seção 5.3). Pertence ao épico A.
// As telas abaixo são marcações de lugar: trocar cada `EmConstrucao` pela tela de verdade,
// mantendo os caminhos e as guardas.
import type { RouteObject } from 'react-router'
import { EmConstrucao } from '../casca/EmConstrucao'
import { ExigeUnidade, SoSemSessao, SoSessaoRestrita } from '../casca/guardas'

export const rotasAcesso: RouteObject[] = [
  {
    element: <SoSemSessao />,
    children: [
      {
        path: 'entrar',
        element: <EmConstrucao titulo="Portal Capibaribe Prime" historia="H-02 · épico A" entrada />,
      },
    ],
  },
  {
    element: <SoSessaoRestrita />,
    children: [
      {
        path: 'primeiro-acesso',
        element: <EmConstrucao titulo="Primeiro acesso" historia="H-01 · épico A" />,
      },
    ],
  },
  {
    // Pública: visível antes do primeiro acesso (RNF-11).
    path: 'privacidade',
    element: (
      <EmConstrucao titulo="Política de privacidade" historia="RNF-11 · épico A" voltar="/entrar" />
    ),
  },
  {
    element: <ExigeUnidade />,
    children: [
      {
        path: 'minha-unidade',
        element: <EmConstrucao titulo="Minha unidade" historia="H-06 · épico A" />,
      },
    ],
  },
]
