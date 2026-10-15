import { useCallback, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useLocation } from 'react-router'
import { ContextoLugarDoRecado, ContextoRecado } from './contextoRecado'

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
 *
 * Ajustes do M4, ponto 8: o recado cobria o título e o conteúdo (era `position: fixed`). Agora a
 * caixa visível vai para o lugar que a tela reserva no topo (`Tela`, via portal) e ocupa espaço
 * ali: o topo cresce e a página desce. A região de status continua aqui, sempre montada e
 * escondida da vista, para o anúncio não depender da tela que acabou de abrir; a frase da caixa
 * fica fora da árvore de acessibilidade (seria lida duas vezes).
 */
export function RecadoProvider({ children }: { children: ReactNode }) {
  const local = useLocation()
  const [recadoAtual, setRecadoAtual] = useState<{ texto: string; tela: string } | null>(null)
  const [dispensado, setDispensado] = useState<string | null>(null)
  const [lugar, setLugar] = useState<HTMLElement | null>(null)

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

  const caixa = mensagem ? (
    <div className="recado on">
      <p className="recado-texto" aria-hidden="true">
        {mensagem}
      </p>
      <button type="button" className="recado-fechar" onClick={fechar}>
        Fechar
      </button>
    </div>
  ) : null

  return (
    <ContextoRecado.Provider value={recado}>
      <ContextoLugarDoRecado.Provider value={setLugar}>
        {children}
        <p className="oculto" role="status" aria-live="polite">
          {mensagem}
        </p>
        {lugar ? createPortal(caixa, lugar) : caixa}
      </ContextoLugarDoRecado.Provider>
    </ContextoRecado.Provider>
  )
}
