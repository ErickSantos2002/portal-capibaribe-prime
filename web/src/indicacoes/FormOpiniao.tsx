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
import { LIMITE_COMENTARIO, MSG_CONFIRA, type RascunhoDaOpiniao } from './formulario'
import type { MinhaOpiniao, Prestador } from './tipos'
import { useDevolverFoco } from './useDevolverFoco'

export const MSG_ESCOLHA = 'Escolha se você recomenda ou não.'

/** A caixa de erro do topo do formulário, com o foco nela (como `ErroGeral` das enquetes). */
export function ErroGeral({ mensagem }: { mensagem: string }) {
  const caixa = useRef<HTMLDivElement>(null)
  useEffect(() => caixa.current?.focus(), [mensagem])
  return (
    <div className="aviso-caixa erro" role="alert" tabIndex={-1} ref={caixa}>
      <Icone nome="alerta" />
      <p>{mensagem}</p>
    </div>
  )
}

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
        aria-invalid={erroRecomenda ? true : undefined}
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
          <span className="ind-voto-texto">
            <span aria-hidden="true">👍 </span>Recomendo
          </span>
        </label>
        <label className={recomenda === false ? 'ind-voto marcado' : 'ind-voto'}>
          <input
            type="radio"
            name={`${id}-recomenda`}
            checked={recomenda === false}
            onChange={() => setRecomenda(false)}
          />
          <span className="ind-voto-texto">
            <span aria-hidden="true">👎 </span>Não recomendo
          </span>
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
  /** Sem opinião ainda: o que a pessoa escreveu em "Indicar alguém", para não perder. */
  rascunho?: RascunhoDaOpiniao | null
  /** Aberto por um toque: o foco vai ao título (aberto com a página, fica no h1 da tela). */
  focarAoAbrir?: boolean
  /** Salvou: a API devolve o prestador já com a opinião nova. */
  aoSalvar: (prestador: Prestador) => void
  /** Apagou: a tela recarrega o prestador. */
  aoApagar: () => void
  aoCancelar: () => void
}

export function FormOpiniao({
  prestadorId,
  inicial,
  rascunho,
  focarAoAbrir = false,
  aoSalvar,
  aoApagar,
  aoCancelar,
}: Props) {
  const recado = useRecado()
  const comeco = inicial ?? rascunho ?? null
  const [recomenda, setRecomenda] = useState<boolean | null>(comeco?.recomenda ?? null)
  const [comentario, setComentario] = useState(comeco?.comentario ?? '')
  const [erros, setErros] = useState<{ recomenda?: string; comentario?: string; geral?: string }>({})
  const [ocupado, setOcupado] = useState(false)
  const [apagando, setApagando] = useState(false)
  const pergunta = useRef<HTMLDivElement>(null)
  const formulario = useRef<HTMLFormElement>(null)
  const titulo = useRef<HTMLHeadingElement>(null)
  const botaoApagar = useDevolverFoco<HTMLButtonElement>(apagando)

  useEffect(() => {
    if (focarAoAbrir) centralizar(formulario.current, titulo.current)
    // Só ao abrir.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (apagando) centralizar(pergunta.current)
  }, [apagando])

  /** Mexeu no campo: o erro dele some, e o do topo também quando não sobra nenhum. */
  function limparErro(campo: 'recomenda' | 'comentario') {
    setErros((antes) => {
      if (!antes[campo]) return antes
      const resto = { ...antes, [campo]: undefined }
      if (resto.geral === MSG_CONFIRA || resto.geral === antes[campo]) {
        if (!resto.recomenda && !resto.comentario) resto.geral = undefined
      }
      return resto
    })
  }

  async function salvar(evento: FormEvent) {
    evento.preventDefault()
    if (recomenda === null) {
      setErros({ recomenda: MSG_ESCOLHA, geral: MSG_ESCOLHA })
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
      const doComentario = erro.doCampo('comentario')
      setErros({ comentario: doComentario, geral: doComentario ?? erro.mensagem })
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
    <form className="ind-form-opiniao" onSubmit={salvar} noValidate ref={formulario}>
      <h3 ref={titulo} tabIndex={-1}>
        {inicial ? 'Mudar a minha opinião' : 'Dar a minha opinião'}
      </h3>
      {erros.geral && <ErroGeral mensagem={erros.geral} />}
      <CamposDaOpiniao
        id="minha"
        recomenda={recomenda}
        setRecomenda={(valor) => {
          setRecomenda(valor)
          limparErro('recomenda')
        }}
        comentario={comentario}
        setComentario={(valor) => {
          setComentario(valor)
          limparErro('comentario')
        }}
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
          <button
            type="button"
            className="texto-link ind-apagar"
            ref={botaoApagar}
            onClick={() => setApagando(true)}
          >
            Apagar a minha opinião
          </button>
        ))}
    </form>
  )
}
