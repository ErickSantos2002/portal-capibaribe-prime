import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router'
import { ContextoRecado } from './contextoRecado'

const DURACAO_MS = 2600

/**
 * Recado de confirmação, de dois jeitos:
 * - na mesma tela: `useRecado()('Voto registrado.')`;
 * - depois de ir para outra tela: `navigate('/avisos', { state: { recado: 'Aviso publicado.' } })`.
 *
 * A região de status existe desde o início (o leitor de tela só anuncia texto que muda numa
 * região que já estava lá). O recado é da tela em que nasceu: trocou de tela, some.
 */
export function RecadoProvider({ children }: { children: ReactNode }) {
  const local = useLocation()
  const [recadoAtual, setRecadoAtual] = useState<{ texto: string; tela: string } | null>(null)
  const [dispensado, setDispensado] = useState<string | null>(null)
  const relogio = useRef<number | undefined>(undefined)

  const recado = useCallback(
    (texto: string) => {
      window.clearTimeout(relogio.current)
      setRecadoAtual({ texto, tela: local.key })
      relogio.current = window.setTimeout(() => setRecadoAtual(null), DURACAO_MS)
    },
    [local.key],
  )

  const doEstado = (local.state as { recado?: unknown } | null)?.recado
  const recadoDaNavegacao = typeof doEstado === 'string' && dispensado !== local.key ? doEstado : ''

  useEffect(() => {
    if (!recadoDaNavegacao) return
    const chave = local.key
    const tempo = window.setTimeout(() => setDispensado(chave), DURACAO_MS)
    return () => window.clearTimeout(tempo)
  }, [recadoDaNavegacao, local.key])

  useEffect(() => () => window.clearTimeout(relogio.current), [])

  const mensagem = recadoAtual?.tela === local.key ? recadoAtual.texto : recadoDaNavegacao
  return (
    <ContextoRecado.Provider value={recado}>
      {children}
      <div className={mensagem ? 'recado on' : 'recado'} role="status">
        {mensagem}
      </div>
    </ContextoRecado.Provider>
  )
}
