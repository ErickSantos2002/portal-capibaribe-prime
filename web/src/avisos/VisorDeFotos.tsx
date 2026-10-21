// Comum · as fotos grandes, por cima da tela (M3, C4, U7, U8), usadas nos anexos do aviso e nos
// classificados (revisão dos classificados, UX 1 e 2). Enquanto aberto: no `body` (portal), o
// resto da página fica inerte, o foco não sai (Tab gira entre os botões), Esc no document fecha e
// as setas trocam de foto, a página não rola por trás e o fundo é preto e opaco. Quem abre devolve
// o foco à foto que estava aberta (`fechar(indice)`). O zoom de dois dedos continua valendo.
// Com a letra grande, "Anterior" e "Próxima" viram só a seta (o nome continua para o leitor de
// tela) e o "Foto 1 de 3" vai para entre elas: a foto fica com o máximo da tela.
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Icone } from '../casca/Icone'
import { IconeAnexo } from './IconesAnexo'
import './anexos.css'

interface Props {
  /** O endereço de cada foto (nulo: ainda sem endereço). */
  fotos: readonly (string | null)[]
  inicio: number
  /** Fecha e diz qual foto estava aberta (o foco volta para a miniatura dela). */
  fechar: (indice: number) => void
  /** O texto alternativo de cada foto; sem ele, "Foto 2 de 3". */
  descrever?: (indice: number) => string
}

export function VisorDeFotos({ fotos, inicio, fechar, descrever }: Props) {
  const [indice, setIndice] = useState(inicio)
  const janela = useRef<HTMLDivElement>(null)
  const botaoFechar = useRef<HTMLButtonElement>(null)
  const atual = useRef(indice)
  useEffect(() => {
    atual.current = indice
  }, [indice])
  const varias = fotos.length > 1
  const rotulo = `Foto ${indice + 1} de ${fotos.length}`

  useEffect(() => {
    const dialogo = janela.current
    botaoFechar.current?.focus()
    // O resto da página fica inerte (nem foco nem leitor de tela chegam lá).
    const fundo = [...document.body.children].filter((e) => dialogo && !e.contains(dialogo))
    for (const e of fundo) e.setAttribute('inert', '')
    const rolagem = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function teclar(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        fechar(atual.current)
      } else if (e.key === 'ArrowRight') {
        setIndice((i) => (i + 1) % fotos.length)
      } else if (e.key === 'ArrowLeft') {
        setIndice((i) => (i - 1 + fotos.length) % fotos.length)
      } else if (e.key === 'Tab' && dialogo) {
        // O foco gira entre os botões da janela.
        const botoes = [...dialogo.querySelectorAll('button')]
        const posicao = botoes.indexOf(document.activeElement as HTMLButtonElement)
        const proximo = e.shiftKey ? posicao - 1 : posicao + 1
        e.preventDefault()
        botoes[(proximo + botoes.length) % botoes.length]?.focus()
      }
    }
    // O foco que escapar (um toque na foto, por exemplo) volta para a janela.
    function prender(e: FocusEvent) {
      if (dialogo && !dialogo.contains(e.target as Node)) botaoFechar.current?.focus()
    }
    document.addEventListener('keydown', teclar)
    document.addEventListener('focusin', prender)
    return () => {
      document.removeEventListener('keydown', teclar)
      document.removeEventListener('focusin', prender)
      for (const e of fundo) e.removeAttribute('inert')
      document.body.style.overflow = rolagem
    }
  }, [fechar, fotos.length])

  const url = fotos[indice]
  return createPortal(
    <div
      ref={janela}
      className="anexo-visualizador"
      role="dialog"
      aria-modal="true"
      aria-label={rotulo}
      // Um toque na foto ou no fundo mantém o foco na janela.
      tabIndex={-1}
    >
      <div className="anexo-visualizador-topo">
        <p aria-live="polite">{rotulo}</p>
        <button
          ref={botaoFechar}
          type="button"
          className="botao leve"
          onClick={() => fechar(indice)}
        >
          <IconeAnexo nome="fechar" /> Fechar
        </button>
      </div>
      {url && <img src={url} alt={descrever ? descrever(indice) : rotulo} />}
      {varias && (
        <div className="anexo-visualizador-passar">
          <button
            type="button"
            className="botao leve"
            aria-label="Foto anterior"
            onClick={() => setIndice((i) => (i - 1 + fotos.length) % fotos.length)}
          >
            <Icone nome="voltar" /> <span className="anexo-visualizador-texto">Anterior</span>
          </button>
          <span className="anexo-visualizador-conta" aria-hidden="true">
            {indice + 1} de {fotos.length}
          </span>
          <button
            type="button"
            className="botao leve"
            aria-label="Próxima foto"
            onClick={() => setIndice((i) => (i + 1) % fotos.length)}
          >
            <span className="anexo-visualizador-texto">Próxima</span> <Icone nome="seta" />
          </button>
        </div>
      )}
    </div>,
    document.body,
  )
}
