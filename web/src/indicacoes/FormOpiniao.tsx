// Indicações · a minha opinião (spec, seção 3.2): recomendo ou não recomendo (sem padrão
// marcado) e o comentário opcional. Dar e mudar são o mesmo formulário; com opinião, também
// "Apagar a minha opinião", que pergunta antes. `CamposDaOpiniao` é a mesma parte em "Indicar
// alguém" (seção 3.3).
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useRecado } from '../casca/contextoRecado'
import { Icone } from '../casca/Icone'
import { centralizar } from '../casca/rolar'
import { comoErroDaApi } from '../avisos/carregar'
import { apagarOpiniao, opinar } from './api'
import type { MinhaOpiniao, Prestador } from './tipos'

export const LIMITE_COMENTARIO = 500
export const MSG_ESCOLHA = 'Escolha se você recomenda ou não.'

interface PropsCampos {
  /** Prefixo dos ids (a tela pode ter mais de um formulário). */
  id: string
  recomenda: boolean | null
  setRecomenda: (valor: boolean) => void
  comentario: string
  setComentario: (valor: string) => void
  erroRecomenda?: string
  erroComentario?: string
}

export function CamposDaOpiniao({
  id,
  recomenda,
  setRecomenda,
  comentario,
  setComentario,
  erroRecomenda,
  erroComentario,
}: PropsCampos) {
  return (
    <>
      <fieldset
        className="ind-recomenda"
        aria-describedby={erroRecomenda ? `${id}-recomenda-erro` : undefined}
      >
        <legend>Você recomenda?</legend>
        <label className={recomenda === true ? 'ind-voto marcado' : 'ind-voto'}>
          <input
            type="radio"
            name={`${id}-recomenda`}
            checked={recomenda === true}
            onChange={() => setRecomenda(true)}
          />
          <span aria-hidden="true">👍 </span>Recomendo
        </label>
        <label className={recomenda === false ? 'ind-voto marcado' : 'ind-voto'}>
          <input
            type="radio"
            name={`${id}-recomenda`}
            checked={recomenda === false}
            onChange={() => setRecomenda(false)}
          />
          <span aria-hidden="true">👎 </span>Não recomendo
        </label>
      </fieldset>
      {erroRecomenda && (
        <p className="ind-erro-campo" id={`${id}-recomenda-erro`}>
          {erroRecomenda}
        </p>
      )}
      <label htmlFor={`${id}-comentario`}>Conte como foi (opcional)</label>
      <textarea
        id={`${id}-comentario`}
        rows={4}
        maxLength={LIMITE_COMENTARIO}
        value={comentario}
        onChange={(e) => setComentario(e.target.value)}
        className={erroComentario ? 'campo-erro' : undefined}
        aria-invalid={erroComentario ? true : undefined}
        aria-describedby={`${id}-contador${erroComentario ? ` ${id}-comentario-erro` : ''}`}
      />
      <p className="ajuda" id={`${id}-contador`}>
        {comentario.length} de {LIMITE_COMENTARIO} letras
      </p>
      {erroComentario && (
        <p className="ind-erro-campo" id={`${id}-comentario-erro`}>
          {erroComentario}
        </p>
      )}
    </>
  )
}

interface Props {
  prestadorId: number
  inicial: MinhaOpiniao | null
  /** Salvou: a API devolve o prestador já com a opinião nova. */
  aoSalvar: (prestador: Prestador) => void
  /** Apagou: a tela recarrega o prestador. */
  aoApagar: () => void
  aoCancelar: () => void
}

export function FormOpiniao({ prestadorId, inicial, aoSalvar, aoApagar, aoCancelar }: Props) {
  const recado = useRecado()
  const [recomenda, setRecomenda] = useState<boolean | null>(inicial?.recomenda ?? null)
  const [comentario, setComentario] = useState(inicial?.comentario ?? '')
  const [erros, setErros] = useState<{ recomenda?: string; comentario?: string; geral?: string }>({})
  const [ocupado, setOcupado] = useState(false)
  const [apagando, setApagando] = useState(false)
  const pergunta = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (apagando) centralizar(pergunta.current)
  }, [apagando])

  async function salvar(evento: FormEvent) {
    evento.preventDefault()
    if (recomenda === null) {
      setErros({ recomenda: MSG_ESCOLHA })
      return
    }
    setOcupado(true)
    setErros({})
    try {
      const prestador = await opinar(prestadorId, {
        recomenda,
        comentario: comentario.trim() ? comentario : null,
      })
      recado(inicial ? 'Sua opinião foi mudada.' : 'Sua opinião foi publicada.')
      aoSalvar(prestador)
    } catch (e) {
      const erro = comoErroDaApi(e)
      setErros({ comentario: erro.doCampo('comentario'), geral: erro.mensagem })
    } finally {
      setOcupado(false)
    }
  }

  async function apagar() {
    setOcupado(true)
    setErros({})
    try {
      await apagarOpiniao(prestadorId)
      recado('Sua opinião foi apagada.')
      aoApagar()
    } catch (e) {
      setErros({ geral: comoErroDaApi(e).mensagem })
      setApagando(false)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <form className="ind-form-opiniao" onSubmit={salvar} noValidate>
      <h3>{inicial ? 'Mudar a minha opinião' : 'Dar a minha opinião'}</h3>
      {erros.geral && (
        <div className="aviso-caixa erro" role="alert">
          <Icone nome="alerta" />
          <p>{erros.geral}</p>
        </div>
      )}
      <CamposDaOpiniao
        id="minha"
        recomenda={recomenda}
        setRecomenda={setRecomenda}
        comentario={comentario}
        setComentario={setComentario}
        erroRecomenda={erros.recomenda}
        erroComentario={erros.comentario}
      />
      <div className="ind-acoes">
        <button type="submit" className="botao" disabled={ocupado}>
          Salvar a minha opinião
        </button>
        <button type="button" className="botao leve" disabled={ocupado} onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
      {inicial &&
        (apagando ? (
          <div
            className="aviso-caixa atencao"
            role="group"
            aria-labelledby="ind-apagar-titulo"
            ref={pergunta}
            tabIndex={-1}
          >
            <Icone nome="alerta" />
            <div>
              <p id="ind-apagar-titulo">
                <strong>Apagar a sua opinião?</strong> Ela sai da lista e não volta. Você pode dar
                outra depois.
              </p>
              <button type="button" className="botao perigo" disabled={ocupado} onClick={apagar}>
                Apagar de vez
              </button>
              <button
                type="button"
                className="botao leve"
                disabled={ocupado}
                onClick={() => setApagando(false)}
              >
                Manter a minha opinião
              </button>
            </div>
          </div>
        ) : (
          <button type="button" className="texto-link ind-apagar" onClick={() => setApagando(true)}>
            Apagar a minha opinião
          </button>
        ))}
    </form>
  )
}
