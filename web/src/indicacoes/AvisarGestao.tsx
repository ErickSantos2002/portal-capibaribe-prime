// Indicações · "Tem algo errado aqui? Avisar a gestão" (spec, seção 3.2): um link discreto que
// abre a confirmação com o motivo opcional (até 300 letras). Depois, só o texto "Você já avisou
// a gestão." (um aviso aberto por apartamento; a API ignora o repetido).
import { useEffect, useRef, useState } from 'react'
import { comoErroDaApi } from '../avisos/carregar'
import { useRecado } from '../casca/contextoRecado'
import { Icone } from '../casca/Icone'
import { centralizar } from '../casca/rolar'
import { avisarGestao } from './api'
import { useDevolverFoco } from './useDevolverFoco'

export const LIMITE_MOTIVO = 300

interface Props {
  prestadorId: number
  jaAvisei: boolean
  aoAvisar: () => void
  /** Outro lugar que usa a mesma confirmação (os classificados): quem manda o aviso e o que a
   *  gestão vai olhar ("esta indicação", "este anúncio"). */
  enviar?: (motivo: string | null) => Promise<void>
  oQue?: string
}

export function AvisarGestao({
  prestadorId,
  jaAvisei,
  aoAvisar,
  enviar,
  oQue = 'esta indicação',
}: Props) {
  const recado = useRecado()
  const [aberto, setAberto] = useState(false)
  // Avisou agora: o texto aparece na hora, sem esperar o prestador recarregar.
  const [avisou, setAvisou] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState('')
  const caixa = useRef<HTMLDivElement>(null)
  const campo = useRef<HTMLTextAreaElement>(null)
  // Cancelar: o foco volta ao "Tem algo errado aqui?".
  const botao = useDevolverFoco<HTMLButtonElement>(aberto)

  useEffect(() => {
    if (aberto) centralizar(caixa.current, campo.current)
  }, [aberto])

  if (jaAvisei || avisou) {
    return (
      <p className="ind-avisou com-icone">
        <Icone nome="certo" tamanho={20} /> Você já avisou a gestão.
      </p>
    )
  }

  async function avisar() {
    setOcupado(true)
    setErro('')
    try {
      const escrito = motivo.trim() ? motivo : null
      await (enviar ? enviar(escrito) : avisarGestao(prestadorId, { motivo: escrito }))
      recado('A gestão foi avisada. Obrigado!')
      setAberto(false)
      setAvisou(true)
      aoAvisar()
    } catch (e) {
      const falha = comoErroDaApi(e)
      setErro(falha.doCampo('motivo') ?? falha.mensagem)
    } finally {
      setOcupado(false)
    }
  }

  if (!aberto) {
    return (
      <button
        type="button"
        className="texto-link ind-avisar"
        ref={botao}
        onClick={() => setAberto(true)}
      >
        Tem algo errado aqui? Avisar a gestão
      </button>
    )
  }

  return (
    <div
      className="aviso-caixa atencao ind-avisar-caixa"
      role="group"
      aria-labelledby="ind-avisar-titulo"
      ref={caixa}
      tabIndex={-1}
    >
      <Icone nome="alerta" />
      <div>
        <p id="ind-avisar-titulo">
          <strong>Avisar a gestão?</strong> A Comissão e a administração vão olhar {oQue}.
          Elas não veem quem avisou.
        </p>
        {erro && (
          <p className="ind-erro-campo" role="alert">
            {erro}
          </p>
        )}
        <label htmlFor="ind-motivo">O que está errado? (opcional)</label>
        <textarea
          id="ind-motivo"
          ref={campo}
          rows={3}
          maxLength={LIMITE_MOTIVO}
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          aria-describedby="ind-motivo-contador"
        />
        <p className="ajuda" id="ind-motivo-contador">
          {motivo.length} de {LIMITE_MOTIVO} letras
        </p>
        <button type="button" className="botao" disabled={ocupado} onClick={avisar}>
          Avisar a gestão
        </button>
        <button
          type="button"
          className="botao leve"
          disabled={ocupado}
          onClick={() => setAberto(false)}
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}
