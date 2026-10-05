// Épico A · Acesso: rotas (spec do M1, seção 5.3). Pertence ao épico A.
import type { RouteObject } from 'react-router'
import { ExigeUnidade, SoSemSessao, SoSessaoRestrita } from '../casca/guardas'
import { Entrar } from './Entrar'
import { MinhaUnidade } from './MinhaUnidade'
import { PrimeiroAcesso } from './PrimeiroAcesso'
import { Privacidade } from './Privacidade'

export const rotasAcesso: RouteObject[] = [
  {
    element: <SoSemSessao />,
    children: [{ path: 'entrar', element: <Entrar /> }],
  },
  {
    element: <SoSessaoRestrita />,
    children: [{ path: 'primeiro-acesso', element: <PrimeiroAcesso /> }],
  },
  // Pública: visível antes do primeiro acesso (RNF-11).
  { path: 'privacidade', element: <Privacidade /> },
  {
    element: <ExigeUnidade />,
    children: [{ path: 'minha-unidade', element: <MinhaUnidade /> }],
  },
]
