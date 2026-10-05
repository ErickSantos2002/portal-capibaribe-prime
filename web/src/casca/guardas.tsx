// Guardas de rota (spec do M1, seção 5.3). A permissão de verdade é do servidor (RNF-13): aqui é
// só para levar a pessoa à tela certa em vez de mostrar um erro.
import { Link, Navigate, Outlet, useLocation } from 'react-router'
import { useSessao } from './contextoSessao'
import { Tela } from './Tela'

function Esperando() {
  return (
    <Tela titulo="Abrindo o Portal" entrada>
      <p className="vazio" role="status">
        Abrindo o Portal…
      </p>
    </Tela>
  )
}

function SemConexao({ mensagem }: { mensagem: string }) {
  const { recarregar } = useSessao()
  return (
    <Tela titulo="Sem conexão" entrada>
      <div className="aviso-caixa erro" role="alert">
        <p>{mensagem}</p>
      </div>
      <button type="button" className="botao" onClick={() => void recarregar()}>
        Tentar de novo
      </button>
    </Tela>
  )
}

/** Unidade com o primeiro acesso concluído. Sem sessão → /entrar; sessão restrita →
 *  /primeiro-acesso. */
export function ExigeUnidade() {
  const { estado } = useSessao()
  const local = useLocation()
  if (estado.situacao === 'carregando') return <Esperando />
  if (estado.situacao === 'sem_conexao') return <SemConexao mensagem={estado.mensagem} />
  if (!estado.eu) return <Navigate to="/entrar" replace state={{ de: local.pathname }} />
  if (estado.eu.precisa_trocar_senha) return <Navigate to="/primeiro-acesso" replace />
  return <Outlet />
}

/** Comissão ou administração. Usar dentro de `ExigeUnidade`. */
export function ExigeGestao() {
  const { eu } = useSessao()
  return eu?.gestao ? <Outlet /> : <SemPermissao />
}

/** Só o administrador. Usar dentro de `ExigeUnidade`. */
export function ExigeAdmin() {
  const { eu } = useSessao()
  return eu?.admin ? <Outlet /> : <SemPermissao />
}

/** Tela de entrar: quem já está logado vai para o mural (ou para o primeiro acesso). */
export function SoSemSessao() {
  const { estado } = useSessao()
  if (estado.situacao === 'carregando') return <Esperando />
  if (estado.situacao === 'pronta' && estado.eu) {
    return <Navigate to={estado.eu.precisa_trocar_senha ? '/primeiro-acesso' : '/avisos'} replace />
  }
  return <Outlet />
}

/** Tela de primeiro acesso: só com a sessão restrita. */
export function SoSessaoRestrita() {
  const { estado } = useSessao()
  if (estado.situacao === 'carregando') return <Esperando />
  if (estado.situacao === 'sem_conexao') return <SemConexao mensagem={estado.mensagem} />
  if (!estado.eu) return <Navigate to="/entrar" replace />
  if (!estado.eu.precisa_trocar_senha) return <Navigate to="/avisos" replace />
  return <Outlet />
}

export function SemPermissao() {
  return (
    <Tela titulo="Sem permissão" voltar="/avisos">
      <div className="aviso-caixa erro" role="alert">
        <p>Esta tela é só da Comissão e da administração do Portal.</p>
      </div>
      <Link className="botao" to="/avisos">
        Ir para o mural
      </Link>
    </Tela>
  )
}

export function NaoEncontrado() {
  return (
    <Tela titulo="Não encontrado" voltar="/avisos">
      <div className="aviso-caixa atencao" role="alert">
        <p>Não achamos esta página. O link pode estar incompleto, ou ela é de outro bloco.</p>
      </div>
      <Link className="botao" to="/avisos">
        Ir para o mural
      </Link>
    </Tela>
  )
}
