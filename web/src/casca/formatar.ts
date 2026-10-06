// Formatos na voz do morador. Comum aos épicos.
import type { Papel, UnidadeRef } from '../api/tipos'

/** "Bloco 1, 101", nunca o código colado "1101". */
export function nomeDaUnidade(unidade: UnidadeRef): string {
  return `Bloco ${unidade.bloco}, ${unidade.apartamento}`
}

/** A API guarda só dígitos: "81912345678" → "(81) 9 1234-5678"; "8133334444" → "(81) 3333-4444". */
export function formatarCelular(digitos: string | null | undefined): string {
  if (!digitos) return ''
  const d = digitos.replace(/\D/g, '')
  if (d.length === 11) return `(${d.slice(0, 2)}) ${d[2]} ${d.slice(3, 7)}-${d.slice(7)}`
  if (d.length === 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return digitos
}

const FUSO = 'America/Recife'
const dataCurta = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'long', timeZone: FUSO })
const dataEHora = new Intl.DateTimeFormat('pt-BR', {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: FUSO,
})

/** "3 de novembro" (no horário de Recife). */
export function formatarData(iso: string): string {
  return dataCurta.format(new Date(iso))
}

/** "3 de nov., 09:12" (no horário de Recife). */
export function formatarDataEHora(iso: string): string {
  return dataEHora.format(new Date(iso))
}

const hora = new Intl.DateTimeFormat('pt-BR', {
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
  timeZone: FUSO,
})

/** "18h17" (no horário de Recife), como se diz a hora no Brasil. */
export function formatarHora(iso: string): string {
  const partes = hora.formatToParts(new Date(iso))
  const valor = (tipo: string) => partes.find((p) => p.type === tipo)?.value ?? '00'
  return `${valor('hour')}h${valor('minute')}`
}

const NOMES_DOS_PAPEIS: Record<Papel, string> = {
  admin: 'Administrador',
  comissao: 'Comissão',
  sindico: 'Síndico',
  conselho: 'Conselho',
}

export function nomeDoPapel(papel: Papel): string {
  return NOMES_DOS_PAPEIS[papel]
}
