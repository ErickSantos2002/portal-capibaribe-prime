import { useCallback, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router'
import { ContextoRecado } from './contextoRecado'

/**
 * Recado de confirmação (ou de erro), de dois jeitos:
 * - na mesma tela: `useRecado()('Voto registrado.')`;
 * - depois de ir para outra tela: `navigate('/avisos', { state: { recado: 'Aviso publicado.' } })`.
 *
 * A região de status existe desde o início (o leitor de tela só anuncia texto que muda numa
 * região que já estava lá). O recado é da tela em que nasceu: trocou de tela, some.
 *
 * Fechamento do M3: o recado não some mais sozinho (sumia em 2,6 s, rápido demais para quem lê
 * devagar). Fica até a pessoa tocar em "Fechar" ou trocar de tela. O botão fica fora da região
 * de status, para o leitor de tela anunciar só a frase.
 */
export function RecadoProvider({ children }: { children: ReactNode }) {
  const local = useLocation()
  const [recadoAtual, setRecadoAtual] = useState<{ texto: string; tela: string } | null>(null)
  const [dispensado, setDispensado] = useState<string | null>(null)

  const recado = useCallback(
    (texto: string) => setRecadoAtual({ texto, tela: local.key }),
    [local.key],
  )

  const doEstado = (local.state as { recado?: unknown } | null)?.recado
  const recadoDaNavegacao = typeof doEstado === 'string' && dispensado !== local.key ? doEstado : ''

  const mensagem = recadoAtual?.tela === local.key ? recadoAtual.texto : recadoDaNavegacao

  function fechar() {
    setRecadoAtual(null)
    setDispensado(local.key)
  }

  return (
    <ContextoRecado.Provider value={recado}>
      {children}
      <div className={mensagem ? 'recado on' : 'recado'}>
        <p className="recado-texto" role="status" aria-live="polite">
          {mensagem}
        </p>
        {mensagem && (
          <button type="button" className="recado-fechar" onClick={fechar}>
            Fechar
          </button>
        )}
      </div>
    </ContextoRecado.Provider>
  )
}
