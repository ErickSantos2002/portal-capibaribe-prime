// Épico A do M2 · seção "Notificações" de Minha unidade: ativar e desativar neste aparelho, e o
// caminho para instalar (H-05; spec m2-push.md, seção 3.2). Desativar nos outros aparelhos é
// "Desconectar", logo abaixo: a inscrição vai junto com a sessão.
import { Link } from 'react-router'
import { Icone } from '../casca/Icone'
import { ControleNotificacoes } from './ControleNotificacoes'
import { useNotificacoes } from './useNotificacoes'
import './notificacoes.css'

export function SecaoNotificacoes() {
  const n = useNotificacoes()
  return (
    <section className="notif-secao" aria-labelledby="notif-titulo">
      <h2 className="secao" id="notif-titulo">
        Notificações
      </h2>
      {n.situacao !== 'desligado' && (
        <div className="folha notif-cartao">
          <ControleNotificacoes n={n} />
        </div>
      )}
      <p className="notif-instalar">
        <Link className="texto-link com-icone" to="/receber-avisos" state={{ de: 'minha-unidade' }}>
          <Icone nome="celular" />
          Como instalar o Portal na tela inicial
        </Link>
      </p>
    </section>
  )
}
