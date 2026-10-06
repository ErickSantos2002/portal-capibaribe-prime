// Datas do aviso na voz do morador, no horário de Recife (spec dos avisos com formatação, 3.4).
const FUSO = 'America/Recife'
// Recife não tem horário de verão desde 2020: a hora digitada no formulário é sempre -03:00.
const DESLOCAMENTO_DE_RECIFE = '-03:00'

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
const MESES_POR_EXTENSO = [
  'janeiro',
  'fevereiro',
  'março',
  'abril',
  'maio',
  'junho',
  'julho',
  'agosto',
  'setembro',
  'outubro',
  'novembro',
  'dezembro',
]
const DIAS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
const DIAS_POR_EXTENSO = [
  'Domingo',
  'Segunda-feira',
  'Terça-feira',
  'Quarta-feira',
  'Quinta-feira',
  'Sexta-feira',
  'Sábado',
]

const partesDeRecife = new Intl.DateTimeFormat('en-US', {
  timeZone: FUSO,
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: 'numeric',
  minute: 'numeric',
  weekday: 'short',
  hourCycle: 'h23',
})
const SEMANA = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

interface Partes {
  ano: number
  mes: number // 1 a 12
  dia: number
  hora: number
  minuto: number
  semana: number // 0 = domingo
}

function emRecife(iso: string): Partes {
  const partes = partesDeRecife.formatToParts(new Date(iso))
  const valor = (tipo: string) => partes.find((p) => p.type === tipo)?.value ?? ''
  return {
    ano: Number(valor('year')),
    mes: Number(valor('month')),
    dia: Number(valor('day')),
    hora: Number(valor('hour')),
    minuto: Number(valor('minute')),
    semana: SEMANA.indexOf(valor('weekday')),
  }
}

const doisDigitos = (n: number) => String(n).padStart(2, '0')

/** "9h", "19h30": como se diz a hora. */
function horario({ hora, minuto }: Partes): string {
  return minuto ? `${hora}h${doisDigitos(minuto)}` : `${hora}h`
}

/** O bloco de data: `{ dia: '04', mes: 'out' }`, com `ano` se não for o ano de hoje. */
export function dataEmBloco(
  iso: string,
  agora: Date = new Date(),
): { dia: string; mes: string; ano?: string } {
  const p = emRecife(iso)
  const bloco = { dia: doisDigitos(p.dia), mes: MESES[p.mes - 1] }
  return outroAno(p, agora) ? { ...bloco, ano: String(p.ano) } : bloco
}

/** "10 de outubro" ou, em outro ano, "9 de outubro de 2027" (o rótulo do bloco de data). */
export function dataPorExtenso(iso: string, agora: Date = new Date()): string {
  const p = emRecife(iso)
  const ano = outroAno(p, agora) ? ` de ${p.ano}` : ''
  return `${p.dia} de ${MESES_POR_EXTENSO[p.mes - 1]}${ano}`
}

/** Linha do evento no cartão do mural, quando o bloco já mostra o dia do evento (dúvida A):
 *  "Sáb, 9h · publicado 6/10" ou "Já aconteceu · publicado 6/10". */
export function eventoNaLinha(quando: string, publicado: string, agora: Date = new Date()): string {
  const p = emRecife(quando)
  const pub = emRecife(publicado)
  const inicio = new Date(quando) < agora ? 'Já aconteceu' : `${DIAS[p.semana]}, ${horario(p)}`
  return `${inicio} · publicado ${pub.dia}/${pub.mes}`
}

/** O evento é de outro ano que o de hoje (em Recife)? Aí a data leva o ano (revisão UX 1). */
function outroAno(p: Partes, agora: Date): boolean {
  return p.ano !== emRecife(agora.toISOString()).ano
}

/** Linha do evento no mural: "Sáb, 11/10 · 9h" ou, se já passou, "Sáb, 11/10 · Já aconteceu".
 *  Em outro ano: "Sáb, 09/10/27 · 9h". */
export function eventoCurto(iso: string, agora: Date = new Date()): string {
  const p = emRecife(iso)
  const quando = new Date(iso) < agora ? 'Já aconteceu' : horario(p)
  const ano = outroAno(p, agora) ? `/${doisDigitos(p.ano % 100)}` : ''
  return `${DIAS[p.semana]}, ${doisDigitos(p.dia)}/${doisDigitos(p.mes)}${ano} · ${quando}`
}

/** "Sábado, 11 de outubro, 9h" (o dia 1 é "1º", como se escreve no Brasil). Em outro ano:
 *  "Sábado, 9 de outubro de 2027, 9h". */
export function eventoPorExtenso(iso: string, agora: Date = new Date()): string {
  const p = emRecife(iso)
  const dia = p.dia === 1 ? '1º' : String(p.dia)
  const ano = outroAno(p, agora) ? ` de ${p.ano}` : ''
  return `${DIAS_POR_EXTENSO[p.semana]}, ${dia} de ${MESES_POR_EXTENSO[p.mes - 1]}${ano}, ${horario(p)}`
}

/** O evento já aconteceu? */
export function jaAconteceu(iso: string, agora: Date = new Date()): boolean {
  return new Date(iso) < agora
}

/** Valores dos campos `type=date` e `type=time` para um instante. */
export function paraOFormulario(iso: string): { data: string; hora: string } {
  const p = emRecife(iso)
  return {
    data: `${p.ano}-${doisDigitos(p.mes)}-${doisDigitos(p.dia)}`,
    hora: `${doisDigitos(p.hora)}:${doisDigitos(p.minuto)}`,
  }
}

/** O instante (com fuso) de um dia e hora digitados em Recife. */
export function deRecife(data: string, hora: string): string {
  return `${data}T${hora}:00${DESLOCAMENTO_DE_RECIFE}`
}
