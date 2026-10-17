// Letra grande e tela baixa (M5, revisões, R1): marcas no <html> para o CSS que não tem como
// perguntar pelo tamanho da letra de outro jeito.
//
// Por que JS: no iPhone, o Dynamic Type chega pela declaração `font: -apple-system-body` do
// <html> (spec m5-letra, 3.6). Uma media query em em/rem é medida pelo tamanho INICIAL da fonte,
// não pelo do <html> do autor (Media Queries 4, §1.3), então lá ela não acompanha a letra. Para
// larguras, o CSS usa container query em rem (o rem de uma container query é o do <html>); para
// o que não tem container query (a altura da tela, o topo), vale a marca daqui:
//   - `data-letra="grande"`: o <html> com 20 px ou mais (125 % da letra de fábrica);
//   - `data-altura="baixa"`: a janela com menos de 35 letras de altura (560 px com a de fábrica).
// O tamanho é lido do próprio <html> (getComputedStyle), e uma régua invisível de 1rem avisa
// quando ele muda (ResizeObserver): a pessoa trocou a letra com o Portal aberto.
import { useSyncExternalStore } from 'react'

/** A partir daqui a letra é "grande". 20 px = 125 %: o "Grande" de fábrica do iPhone (17 px) e
 *  o passo seguinte (19 px), e o 115 % do Android (18,4 px), ficam no desenho de fábrica; o
 *  130 % do Android (20,8 px), o "Grande" do Chrome de computador (20 px) e o "Extra Grande" do
 *  iPhone (21 px) em diante passam para o desenho de letra grande. */
export const LETRA_GRANDE_PX = 20
/** Altura da janela, em letras, abaixo da qual a tela é "baixa" (o antigo `max-height: 35em`). */
export const ALTURA_BAIXA_EM_LETRAS = 35

export interface EstadoDaLetra {
  grande: boolean
  baixa: boolean
}

export function classificar(raizPx: number, alturaPx: number): EstadoDaLetra {
  return {
    grande: raizPx >= LETRA_GRANDE_PX,
    baixa: alturaPx < ALTURA_BAIXA_EM_LETRAS * raizPx,
  }
}

const ouvintes = new Set<() => void>()

function atualizar(): void {
  const raiz = document.documentElement
  const px = parseFloat(getComputedStyle(raiz).fontSize) || 16
  const { grande, baixa } = classificar(px, window.innerHeight)
  const antes = raiz.dataset.letra
  if (grande) raiz.dataset.letra = 'grande'
  else delete raiz.dataset.letra
  if (baixa) raiz.dataset.altura = 'baixa'
  else delete raiz.dataset.altura
  if (antes !== raiz.dataset.letra) ouvintes.forEach((avisar) => avisar())
}

/** Marca o <html> agora e a cada mudança de letra ou de altura. Devolve quem desliga. */
export function vigiarLetra(): () => void {
  const regua = document.createElement('span')
  regua.className = 'regua-letra'
  regua.setAttribute('aria-hidden', 'true')
  document.body.append(regua)
  atualizar()
  const observador = typeof ResizeObserver === 'function' ? new ResizeObserver(atualizar) : null
  observador?.observe(regua)
  window.addEventListener('resize', atualizar)
  return () => {
    observador?.disconnect()
    window.removeEventListener('resize', atualizar)
    regua.remove()
  }
}

function inscrever(avisar: () => void): () => void {
  ouvintes.add(avisar)
  return () => ouvintes.delete(avisar)
}

const ehGrande = () => document.documentElement.dataset.letra === 'grande'

/** O componente que muda de forma com a letra grande (o topo, `Tela`) lê daqui. */
export function useLetraGrande(): boolean {
  return useSyncExternalStore(inscrever, ehGrande, () => false)
}
