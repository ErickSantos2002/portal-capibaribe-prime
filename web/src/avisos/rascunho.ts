// O rascunho do formulário de aviso (novo e corrigir): estado, validação antes de enviar e o
// evento como a API recebe. Separado do componente (o Vite só recarrega arquivo de componente).
import { deRecife, paraOFormulario } from './datas'
import type { AvisoCompleto, Categoria, Evento } from './tipos'

export const LIMITE_TITULO = 120
export const LIMITE_TEXTO = 10_000
export const LIMITE_ONDE = 120

export type Campo = 'titulo' | 'texto' | 'blocos' | 'evento' | 'categoria'
export type Erros = Partial<Record<Campo, string>>

/** O que a pessoa está escrevendo. Dia e hora ficam como os campos `date` e `time` dão. */
export interface Rascunho {
  titulo: string
  texto: string
  categoria: Categoria
  eEvento: boolean
  dia: string
  hora: string
  onde: string
}

export const RASCUNHO_VAZIO: Rascunho = {
  titulo: '',
  texto: '',
  categoria: 'geral',
  eEvento: false,
  dia: '',
  hora: '',
  onde: '',
}

/** O rascunho da correção: a versão em vigor como está. */
export function rascunhoDe(aviso: AvisoCompleto): Rascunho {
  const quando = aviso.evento ? paraOFormulario(aviso.evento.quando) : { data: '', hora: '' }
  return {
    titulo: aviso.titulo,
    texto: aviso.texto,
    categoria: aviso.categoria,
    eEvento: !!aviso.evento,
    dia: quando.data,
    hora: quando.hora,
    onde: aviso.evento?.onde ?? '',
  }
}

/** O evento como a API recebe (a hora digitada é de Recife), ou nulo. */
export function eventoDe(r: Rascunho): Evento | null {
  if (!r.eEvento || !r.dia || !r.hora) return null
  return { quando: deRecife(r.dia, r.hora), onde: r.onde.trim() || null }
}

/** As mesmas regras da API (`app/esquemas/avisos.py`), para avisar antes de enviar. */
export function conferir(r: Rascunho): Erros {
  const erros: Erros = {}
  if (!r.titulo.trim()) erros.titulo = 'Escreva o título do aviso.'
  else if (r.titulo.trim().length > LIMITE_TITULO) {
    erros.titulo = 'O título pode ter até 120 letras.'
  }
  if (!r.texto.trim()) erros.texto = 'Escreva o texto do aviso.'
  else if (r.texto.trim().length > LIMITE_TEXTO) {
    erros.texto = 'O texto pode ter até 10.000 letras.'
  }
  if (r.eEvento && (!r.dia || !r.hora)) erros.evento = 'Escolha o dia e a hora do evento.'
  return erros
}

/** Qual erro cada pedaço do rascunho apaga quando a pessoa mexe nele (revisão UX 6). */
const CAMPO_DE: Record<keyof Rascunho, Campo> = {
  titulo: 'titulo',
  texto: 'texto',
  categoria: 'categoria',
  eEvento: 'evento',
  dia: 'evento',
  hora: 'evento',
  onde: 'evento',
}

/** Os erros sem os dos campos que acabaram de mudar. */
export function semErrosDe(erros: Erros, mudanca: Partial<Rascunho>): Erros {
  const restantes = { ...erros }
  for (const chave of Object.keys(mudanca) as (keyof Rascunho)[]) delete restantes[CAMPO_DE[chave]]
  return restantes
}

/** A mensagem da caixa do topo: o erro, ou quantos são e quais (revisão UX 6). */
export function mensagemGeral(erros: Erros): string {
  const mensagens = Object.values(erros)
  if (mensagens.length < 2) return mensagens[0] ?? ''
  return `Confira ${mensagens.length} coisas: ${mensagens.join(' ')}`
}
