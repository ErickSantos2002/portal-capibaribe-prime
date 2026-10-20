// Todas as rotas do Portal. Arquivo comum: cada épico mexe só no próprio `rotas.tsx`, que é
// juntado aqui (spec do M1, seções 5.3 e 7).
import { Navigate, type RouteObject } from 'react-router'
import { rotasAcesso } from './acesso/rotas'
import { rotasAdministracao } from './administracao/rotas'
import { rotasAvisos } from './avisos/rotas'
import { NaoEncontrado } from './casca/guardas'
import { rotasClassificados } from './classificados/rotas'
import { Raiz } from './casca/Raiz'
import { rotasDocumentos } from './documentos/rotas'
import { rotasEnquetes } from './enquetes/rotas'
import { rotasIndicacoes } from './indicacoes/rotas'
import { rotasNotificacoes } from './notificacoes/rotas'
import { rotasRecuperacao } from './recuperacao/rotas'

export const rotas: RouteObject[] = [
  {
    element: <Raiz />,
    children: [
      { index: true, element: <Navigate to="/avisos" replace /> },
      ...rotasAcesso,
      ...rotasAvisos,
      ...rotasAdministracao,
      // M2: épico A (notificações) e épico B (esqueci a senha).
      ...rotasNotificacoes,
      ...rotasRecuperacao,
      // M3: épico A (documentos; os anexos do épico B ficam nas rotas dos avisos).
      ...rotasDocumentos,
      // M4: épico A (criar e gerir) e épico B (votar e resultado), juntados em
      // `enquetes/rotas.tsx`.
      ...rotasEnquetes,
      // Indicações de serviços (spec de 18/10/2026).
      ...rotasIndicacoes,
      // Classificados entre vizinhos (spec de 20/10/2026).
      ...rotasClassificados,
      { path: '*', element: <NaoEncontrado /> },
    ],
  },
]
