// Classificados · o que o dono faz no anúncio aberto (spec, seção 3.2): editar, marcar como
// reservado ou tirar a reserva, renovar (vencido ou a menos de 7 dias de vencer) e encerrar, com
// o motivo. O vencido só renova ou encerra; o escondido pela gestão só encerra; o encerrado não
// volta.
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { comoErroDaApi } from '../avisos/carregar'
import { useRecado } from '../casca/contextoRecado'
import { Icone } from '../casca/Icone'
import { centralizar } from '../casca/rolar'
import { useDevolverFoco } from '../indicacoes/useDevolverFoco'
import { encerrar, liberar, renovar, reservar } from './api'
import { caminhoEditarAnuncio } from './caminhos'
import type { Anuncio, MotivoEncerramento } from './tipos'

const MOTIVOS: { valor: MotivoEncerramento; texto: string }[] = [
  { valor: 'vendi', texto: 'Vendi' },
  { valor: 'troquei', texto: 'Troquei' },
  { valor: 'doei', texto: 'Doei' },
  { valor: 'desisti', texto: 'Desisti' },
]

interface Props {
  anuncio: Anuncio
  trocar: (novo: Anuncio) => void
}

export function AcoesDoDono({ anuncio, trocar }: Props) {
  const recado = useRecado()
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState('')
  const [encerrando, setEncerrando] = useState(false)
  const botaoEncerrar = useDevolverFoco<HTMLButtonElement>(encerrando)

  if (anuncio.situacao === 'encerrado') return null
  const aberto = !anuncio.escondido && !anuncio.vencido

  async function fazer(acao: () => Promise<Anuncio>, frase: string) {
    setOcupado(true)
    setErro('')
    try {
      trocar(await acao())
      recado(frase)
    } catch (e) {
      setErro(comoErroDaApi(e).mensagem)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <section className="cla-dono" aria-labelledby="cla-dono-titulo">
      <h2 id="cla-dono-titulo" className="secao">
        O seu anúncio
      </h2>
      {erro && (
        <div className="aviso-caixa erro" role="alert">
          <Icone nome="alerta" />
          <p>{erro}</p>
        </div>
      )}
      <div className="ind-acoes">
        {aberto && (
          <Link className="botao leve" to={caminhoEditarAnuncio(anuncio.id)}>
            <Icone nome="editar" /> Editar
          </Link>
        )}
        {aberto &&
          (anuncio.situacao === 'reservado' ? (
            <button
              type="button"
              className="botao leve"
              disabled={ocupado}
              onClick={() => fazer(() => liberar(anuncio.id), 'A reserva foi tirada.')}
            >
              Tirar a reserva
            </button>
          ) : (
            <button
              type="button"
              className="botao leve"
              disabled={ocupado}
              onClick={() => fazer(() => reservar(anuncio.id), 'Anúncio marcado como reservado.')}
            >
              Marcar como reservado
            </button>
          ))}
        {anuncio.pode_renovar && (
          <button
            type="button"
            className="botao"
            disabled={ocupado}
            onClick={() =>
              fazer(() => renovar(anuncio.id), 'Anúncio renovado por mais 30 dias.')
            }
          >
            <Icone nome="relogio" /> Renovar por mais 30 dias
          </button>
        )}
        {encerrando ? (
          <Encerrar
            aoEncerrar={async (motivo) => {
              await fazer(() => encerrar(anuncio.id, motivo), 'Anúncio encerrado.')
              setEncerrando(false)
            }}
            aoCancelar={() => setEncerrando(false)}
            ocupado={ocupado}
          />
        ) : (
          <button
            type="button"
            className="botao leve"
            ref={botaoEncerrar}
            disabled={ocupado}
            onClick={() => setEncerrando(true)}
          >
            <Icone nome="certo" /> Encerrar
          </button>
        )}
      </div>
    </section>
  )
}

interface PropsEncerrar {
  aoEncerrar: (motivo: MotivoEncerramento) => Promise<void>
  aoCancelar: () => void
  ocupado: boolean
}

function Encerrar({ aoEncerrar, aoCancelar, ocupado }: PropsEncerrar) {
  const [motivo, setMotivo] = useState<MotivoEncerramento | null>(null)
  const [erro, setErro] = useState('')
  const caixa = useRef<HTMLFieldSetElement>(null)

  useEffect(() => {
    centralizar(caixa.current, caixa.current?.querySelector('input'))
  }, [])

  return (
    <fieldset
      className="aviso-caixa atencao cla-encerrar"
      ref={caixa}
      aria-describedby={erro ? 'cla-encerrar-erro' : undefined}
    >
      <legend>
        <strong>Encerrar o anúncio?</strong>
      </legend>
      <p>Ele sai da lista e não volta. Se quiser, anuncie de novo depois. O que aconteceu?</p>
      {MOTIVOS.map((m) => (
        <label key={m.valor} className={motivo === m.valor ? 'ind-voto marcado' : 'ind-voto'}>
          <input
            type="radio"
            name="cla-motivo"
            checked={motivo === m.valor}
            onChange={() => {
              setMotivo(m.valor)
              setErro('')
            }}
          />
          <span className="ind-voto-texto">{m.texto}</span>
        </label>
      ))}
      {erro && (
        <p className="ind-erro-campo" id="cla-encerrar-erro" role="alert">
          {erro}
        </p>
      )}
      <button
        type="button"
        className="botao perigo"
        disabled={ocupado}
        onClick={() => {
          if (!motivo) setErro('Escolha o que aconteceu.')
          else void aoEncerrar(motivo)
        }}
      >
        Encerrar anúncio
      </button>
      <button type="button" className="botao leve" disabled={ocupado} onClick={aoCancelar}>
        Cancelar
      </button>
    </fieldset>
  )
}
