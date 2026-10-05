// Raiz de todas as rotas: sessão e recado disponíveis para qualquer tela.
import { Outlet } from 'react-router'
import { RecadoProvider } from './RecadoProvider'
import { SessaoProvider } from './SessaoProvider'

export function Raiz() {
  return (
    <SessaoProvider>
      <RecadoProvider>
        <Outlet />
      </RecadoProvider>
    </SessaoProvider>
  )
}
