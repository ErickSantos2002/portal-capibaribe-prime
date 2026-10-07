// A situação das notificações neste aparelho numa frase, e o botão que muda (spec m2-push.md,
// seção 3.3). Mesma peça na tela "Receber os avisos" e em Minha unidade.
import { useEffect, useRef } from 'react'
import { CaixaDeErro } from '../acesso/CaixaDeErro'
import { Icone } from '../casca/Icone'
import { comoLiberar } from './aparelho'
import type { Notificacoes } from './useNotificacoes'

export function ControleNotificacoes({ n }: { n: Notificacoes }) {
  const situacaoRef = useRef<HTMLElement | null>(null)
  const guardar = (elemento: HTMLElement | null) => {
    situacaoRef.current = elemento
  }
  const anterior = useRef(n.situacao)
  // Ativou ou desativou: o botão some e outro aparece. O foco vai para a frase nova, para o
  // leitor de tela dizer o que mudou e o teclado não cair no começo da página.
  useEffect(() => {
    const mudou =
      anterior.current !== n.situacao &&
      (anterior.current === 'ativa' || anterior.current === 'inativa')
    anterior.current = n.situacao
    if (mudou) situacaoRef.current?.focus()
  }, [n.situacao])

  switch (n.situacao) {
    case 'carregando':
      return (
        <p className="suave">Conferindo as notificações deste aparelho…</p>
      )
    case 'desligado':
      return null
    case 'erro':
      return (
        // Sem `role="alert"`: é uma parte da tela, não o erro dela (o resto de Minha unidade
        // funciona, e a caixa de erro do topo é que avisa o que impede a tela inteira).
        <div className="aviso-caixa atencao">
          <Icone nome="alerta" />
          <div>
            <p>{n.falhaAoLer}</p>
            <button type="button" className="texto-link" onClick={() => void n.atualizar()}>
              Tentar de novo
            </button>
          </div>
        </div>
      )
    case 'precisa_instalar':
      return (
        <Explicacao>
          No iPhone, as notificações só funcionam com o Portal na tela inicial. Instale e abra pelo
          ícone novo: lá dentro, o Portal mostra o botão para ativar.
        </Explicacao>
      )
    case 'ios_antigo':
      return (
        <Explicacao>
          Este iPhone precisa do iOS 16.4 ou mais novo para receber notificações. Atualize em
          Ajustes › Geral › Atualização de Software.
        </Explicacao>
      )
    case 'sem_suporte':
      return (
        <Explicacao>
          Este navegador não recebe notificações. Abra o Portal no Chrome, no Edge ou no Firefox.
          Os avisos continuam no mural.
        </Explicacao>
      )
    case 'bloqueada':
      return (
        <div className="aviso-caixa atencao" ref={guardar} tabIndex={-1}>
          <Icone nome="alerta" />
          <div>
            <p>
              <strong>As notificações estão bloqueadas neste aparelho.</strong>
            </p>
            <p>{comoLiberar()}</p>
            <button type="button" className="botao leve" onClick={() => void n.atualizar()}>
              Já liberei
            </button>
          </div>
        </div>
      )
    case 'inativa':
    case 'ativa': {
      const ligada = n.situacao === 'ativa'
      return (
        <>
          <p
            className={ligada ? 'notif-situacao ligada' : 'notif-situacao'}
            ref={guardar}
            tabIndex={-1}
          >
            {ligada && <Icone nome="certo" />}
            <span>{ligada ? 'Ligadas neste aparelho.' : 'Desligadas neste aparelho.'}</span>
          </p>
          {n.problema && (
            <CaixaDeErro vez={n.problema.vez}>
              <p>{n.problema.mensagem}</p>
            </CaixaDeErro>
          )}
          {ligada ? (
            <button
              type="button"
              className="botao leve"
              disabled={n.ocupado}
              onClick={n.aoDesativar}
            >
              {n.ocupado ? 'Desativando…' : 'Desativar neste aparelho'}
            </button>
          ) : (
            // Leve, como no protótipo: na oferta, o botão cheio é "Ir para o mural" (recusar
            // não atrapalha nada); em Minha unidade, igual aos outros botões da tela.
            <button type="button" className="botao leve" disabled={n.ocupado} onClick={n.aoAtivar}>
              <Icone nome="sino" /> {n.ocupado ? 'Ativando…' : 'Ativar notificações'}
            </button>
          )}
          {n.dica && <p className="ajuda notif-dica">{n.dica}</p>}
        </>
      )
    }
  }
}

function Explicacao({ children }: { children: string | string[] }) {
  return (
    <div className="aviso-caixa info">
      <Icone nome="info" />
      <p>{children}</p>
    </div>
  )
}
