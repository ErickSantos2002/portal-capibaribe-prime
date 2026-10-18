// A folha do Menu (spec docs/superpowers/specs/2026-10-18-navegacao-bola-design.md, seção 4):
// sobe de baixo quando a pessoa toca na bola, com todos os lugares, agrupados, cada um com o nome
// e uma frase do que tem lá. O padrão de janela é o de `sobre/BotaoVersao.tsx`: `<dialog>` com
// showModal(), que deixa o resto da tela inerte, prende o foco, fecha no Esc e, no Chrome do
// Android (120+), fecha no gesto de voltar sem mexer no histórico. Montada só enquanto aberta.
import { useEffect, useId, useRef, type PointerEvent } from 'react'
import { Link } from 'react-router'
import { Icone } from './Icone'
import { agrupados, type Lugar } from './menu'
import { Conta } from './Conta'

const FOCAVEIS = 'button:not([disabled]), a[href], [tabindex="0"]'
/** Arrastou mais que esta parte da altura da folha: fecha; menos, ela volta. */
const ARRASTO_QUE_FECHA = 0.25

interface Props {
  lugares: Lugar[]
  atual?: Lugar
  naoLidos: number
  aoFechar: () => void
}

/** Trava a rolagem da página atrás da folha. No iPhone, `overflow: hidden` no body não basta: o
 *  body vira `position: fixed` na altura em que estava, e a rolagem volta ao fechar. */
function useTravarRolagem() {
  useEffect(() => {
    const corpo = document.body
    const y = window.scrollY
    const antes = { position: corpo.style.position, top: corpo.style.top, width: corpo.style.width }
    corpo.style.position = 'fixed'
    corpo.style.top = `${-y}px`
    corpo.style.width = '100%'
    return () => {
      corpo.style.position = antes.position
      corpo.style.top = antes.top
      corpo.style.width = antes.width
      window.scrollTo(0, y)
    }
  }, [])
}

export function MenuFolha({ lugares, atual, naoLidos, aoFechar }: Props) {
  const janela = useRef<HTMLDialogElement>(null)
  const caixa = useRef<HTMLDivElement>(null)
  const titulo = useRef<HTMLHeadingElement>(null)
  const arrasto = useRef<{ inicio: number; altura: number; desce: number } | null>(null)
  const idTitulo = useId()
  useTravarRolagem()

  useEffect(() => {
    const dialogo = janela.current
    // O StrictMode monta duas vezes: abrir só se ainda não estiver aberta.
    if (dialogo && !dialogo.open) dialogo.showModal()
    // O foco vai para o título (o leitor de tela anuncia a pergunta), não para o primeiro lugar.
    titulo.current?.focus()
  }, [])

  const fechar = () => janela.current?.close()

  // Arrastar a pegadinha (ou o cabeçalho) para baixo é só um atalho: o botão Fechar é a
  // alternativa (WCAG 2.5.7). A lista não arrasta, para não brigar com a rolagem dela.
  const comecarArrasto = (evento: PointerEvent<HTMLElement>) => {
    const altura = caixa.current?.getBoundingClientRect().height ?? 0
    arrasto.current = { inicio: evento.clientY, altura, desce: 0 }
    evento.currentTarget.setPointerCapture?.(evento.pointerId)
  }
  const arrastar = (evento: PointerEvent<HTMLElement>) => {
    const atualArrasto = arrasto.current
    if (!atualArrasto || !caixa.current) return
    atualArrasto.desce = Math.max(0, evento.clientY - atualArrasto.inicio)
    caixa.current.style.transform = `translateY(${atualArrasto.desce}px)`
  }
  const soltar = () => {
    const fim = arrasto.current
    arrasto.current = null
    if (!fim) return
    if (fim.altura > 0 && fim.desce > fim.altura * ARRASTO_QUE_FECHA) fechar()
    else if (caixa.current) caixa.current.style.transform = ''
  }

  return (
    <dialog
      ref={janela}
      className="menu-folha"
      aria-modal="true"
      aria-labelledby={idTitulo}
      onClose={aoFechar}
      onKeyDown={(evento) => {
        // O <dialog> já deixa o resto da tela inerte, mas o Tab ainda passaria pela barra do
        // navegador antes de voltar. Aqui ele dá a volta direto, do último ao primeiro.
        if (evento.key !== 'Tab') return
        const focaveis = evento.currentTarget.querySelectorAll<HTMLElement>(FOCAVEIS)
        const primeiro = focaveis[0]
        const ultimo = focaveis[focaveis.length - 1]
        if (!primeiro) return
        if (!evento.shiftKey && document.activeElement === ultimo) {
          evento.preventDefault()
          primeiro.focus()
        } else if (evento.shiftKey && (document.activeElement === primeiro || document.activeElement === titulo.current)) {
          evento.preventDefault()
          ultimo.focus()
        }
      }}
      onClick={(evento) => {
        // O clique cai no próprio <dialog> só fora da caixa (no véu).
        if (evento.target === evento.currentTarget) fechar()
      }}
    >
      <div ref={caixa} className="menu-folha-caixa">
        <header
          className="menu-folha-topo"
          onPointerDown={comecarArrasto}
          onPointerMove={arrastar}
          onPointerUp={soltar}
          onPointerCancel={soltar}
        >
          <span className="menu-folha-pega" aria-hidden="true" />
          <h2 id={idTitulo} ref={titulo} tabIndex={-1}>
            Para onde você quer ir?
          </h2>
        </header>
        <div className="menu-folha-lista">
          {agrupados(lugares).map((grupo) => (
            <div key={grupo.grupo} className="menu-folha-grupo">
              <h3>{grupo.nome}</h3>
              {grupo.lugares.map((lugar) => {
                const aqui = lugar === atual
                return (
                  <Link
                    key={lugar.para}
                    to={lugar.para}
                    aria-current={aqui ? 'page' : undefined}
                    onClick={fechar}
                  >
                    <span className="menu-folha-ic">
                      <Icone nome={lugar.icone} />
                    </span>
                    <span className="menu-folha-texto">
                      <span className="menu-folha-nome">{lugar.texto}</span>
                      <span className="menu-folha-frase">{aqui ? 'Você está aqui' : lugar.frase}</span>
                    </span>
                    <Conta lugar={lugar} naoLidos={naoLidos} />
                    <Icone nome="seta" tamanho={20} />
                  </Link>
                )
              })}
            </div>
          ))}
        </div>
        {/* A bola-X: no mesmo ponto da tela onde estava a bola (o dedo não procura). A barra fica
            atrás do véu e inerte, por isso a de fechar é desenhada aqui dentro. */}
        <div className="menu-folha-pe">
          <button type="button" className="nav-bola menu-folha-fechar" onClick={fechar}>
            <span className="nav-bola-circulo">
              <Icone nome="fechar" />
            </span>
            <span className="nav-bola-rotulo">Fechar</span>
          </button>
        </div>
      </div>
    </dialog>
  )
}
