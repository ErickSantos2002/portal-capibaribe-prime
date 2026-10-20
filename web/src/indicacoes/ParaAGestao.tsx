// Indicações · a moderação no prestador aberto (spec, seções 3.2 e 8): a seção "Para a gestão"
// (o nome já usado em avisos, documentos e enquetes) com os avisos recebidos e "Esconder este
// prestador", e o "Esconder esta opinião" de cada opinião. Esconder é definitivo e pergunta antes.
import { useEffect, useRef, useState } from 'react'
import { comoErroDaApi } from '../avisos/carregar'
import { useRecado } from '../casca/contextoRecado'
import { formatarDataEHora } from '../casca/formatar'
import { Icone } from '../casca/Icone'
import { centralizar } from '../casca/rolar'
import { esconderOpiniao, esconderPrestador, resolverAviso } from './api'
import type { Prestador } from './tipos'

interface PropsConfirmar {
  id: string
  /** O botão que abre a pergunta, e o título dela com "?". */
  acao: string
  explicacao: string
  executar: () => Promise<void>
  /** Botão discreto (na opinião) ou o de sempre (na seção). */
  discreto?: boolean
}

/** Um botão que pergunta antes: "Esconder de vez" ou "Cancelar". Também nos classificados. */
export function Confirmar({ id, acao, explicacao, executar, discreto }: PropsConfirmar) {
  const [aberto, setAberto] = useState(false)
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState('')
  const caixa = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (aberto) centralizar(caixa.current)
  }, [aberto])

  async function confirmar() {
    setOcupado(true)
    setErro('')
    try {
      await executar()
      setAberto(false)
    } catch (e) {
      setErro(comoErroDaApi(e).mensagem)
    } finally {
      setOcupado(false)
    }
  }

  if (!aberto) {
    return (
      <button
        type="button"
        className={discreto ? 'texto-link ind-esconder' : 'botao leve'}
        onClick={() => setAberto(true)}
      >
        {!discreto && <Icone nome="olho" />} {acao}
      </button>
    )
  }
  return (
    <div className="aviso-caixa atencao" role="group" aria-labelledby={id} ref={caixa} tabIndex={-1}>
      <Icone nome="alerta" />
      <div>
        <p id={id}>
          <strong>{acao}?</strong> {explicacao}
        </p>
        {erro && (
          <p className="ind-erro-campo" role="alert">
            {erro}
          </p>
        )}
        <button type="button" className="botao perigo" disabled={ocupado} onClick={confirmar}>
          Esconder de vez
        </button>
        <button type="button" className="botao leve" disabled={ocupado} onClick={() => setAberto(false)}>
          Cancelar
        </button>
      </div>
    </div>
  )
}

export function EsconderOpiniao({ opiniaoId, recarregar }: { opiniaoId: number; recarregar: () => void }) {
  const recado = useRecado()
  return (
    <Confirmar
      id={`ind-esconder-opiniao-${opiniaoId}`}
      acao="Esconder esta opinião"
      explicacao="Ela sai da página para todos, menos para o apartamento que escreveu, que não pode mais mudá-la nem apagá-la."
      discreto
      executar={async () => {
        await esconderOpiniao(opiniaoId)
        recado('Opinião escondida.')
        recarregar()
      }}
    />
  )
}

export function ParaAGestao({ prestador, recarregar }: { prestador: Prestador; recarregar: () => void }) {
  const recado = useRecado()
  const [resolvendo, setResolvendo] = useState<number | null>(null)
  const [erro, setErro] = useState('')
  const avisos = prestador.avisos ?? []

  async function resolver(id: number) {
    setResolvendo(id)
    setErro('')
    try {
      await resolverAviso(id)
      recado('Aviso resolvido.')
      recarregar()
    } catch (e) {
      setErro(comoErroDaApi(e).mensagem)
    } finally {
      setResolvendo(null)
    }
  }

  return (
    <section className="ind-gestao" aria-labelledby="ind-para-a-gestao">
      <h2 id="ind-para-a-gestao" className="secao">
        Para a gestão
      </h2>
      <h3 className="ind-gestao-titulo">Avisos da vizinhança</h3>
      {erro && (
        <div className="aviso-caixa erro" role="alert">
          <Icone nome="alerta" />
          <p>{erro}</p>
        </div>
      )}
      {avisos.length === 0 ? (
        <p className="vazio">Nenhum aviso aberto.</p>
      ) : (
        <ul className="folha ind-avisos">
          {avisos.map((a) => (
            <li key={a.id} className="ind-aviso">
              <div>
                <p className="ind-aviso-motivo">{a.motivo ?? 'Sem motivo escrito.'}</p>
                <p className="ind-data">{formatarDataEHora(a.em)}</p>
              </div>
              <button
                type="button"
                className="botao leve"
                disabled={resolvendo !== null}
                onClick={() => resolver(a.id)}
              >
                Resolver
              </button>
            </li>
          ))}
        </ul>
      )}
      {prestador.escondido ? (
        <p className="ajuda">
          Este prestador saiu da lista. O telefone dele continua guardado, para ele não voltar.
        </p>
      ) : (
        <Confirmar
          id="ind-esconder-prestador"
          acao="Esconder este prestador"
          explicacao="Ele sai da lista e não volta. Quem tem o telefone dele não consegue indicá-lo de novo."
          executar={async () => {
            await esconderPrestador(prestador.id)
            recado('Prestador escondido da lista.')
            recarregar()
          }}
        />
      )}
    </section>
  )
}
