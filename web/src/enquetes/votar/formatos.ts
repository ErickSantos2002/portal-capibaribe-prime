// Épico B do M4 · textos das enquetes na voz do morador. Pertence ao épico B.
import type { UnidadeRef } from '../../api/tipos'
import type { Participacao, Votantes } from '../tipos'

const FUSO = 'America/Recife'
const MESES = [
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

const partesDeRecife = new Intl.DateTimeFormat('en-US', {
  timeZone: FUSO,
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: 'numeric',
  minute: 'numeric',
  hourCycle: 'h23',
})

function emRecife(data: Date) {
  const partes = partesDeRecife.formatToParts(data)
  const valor = (tipo: string) => Number(partes.find((p) => p.type === tipo)?.value ?? 0)
  return {
    ano: valor('year'),
    mes: valor('month'),
    dia: valor('day'),
    hora: valor('hour'),
    minuto: valor('minute'),
  }
}

/** "10 de novembro, às 20h"; "às 19h30"; em outro ano, "5 de janeiro de 2027, às 12h". */
export function quandoTermina(iso: string, agora: Date = new Date()): string {
  const p = emRecife(new Date(iso))
  const ano = p.ano !== emRecife(agora).ano ? ` de ${p.ano}` : ''
  const minuto = p.minuto ? String(p.minuto).padStart(2, '0') : ''
  return `${p.dia} de ${MESES[p.mes - 1]}${ano}, às ${p.hora}h${minuto}`
}

/** Porcentagem inteira; 0 quando não há de onde tirar. */
export function porcentagem(parte: number, total: number): number {
  return total > 0 ? Math.round((parte * 100) / total) : 0
}

/** "46%"; entre 0 e 1%, "menos de 1%" (1 de 320 não é 0%). */
export function porcentagemEmTexto(parte: number, total: number): string {
  if (parte > 0 && total > 0 && (parte * 100) / total < 0.5) return 'menos de 1%'
  return `${porcentagem(parte, total)}%`
}

export function votosEmTexto(votos: number): string {
  return `${votos} ${votos === 1 ? 'voto' : 'votos'}`
}

/** "192 de 320 apartamentos votaram (60%)." */
export function participacaoEmTexto({ votaram, total }: Participacao): string {
  if (votaram === 0) return 'Nenhum apartamento votou ainda.'
  const verbo = votaram === 1 ? 'votou' : 'votaram'
  return `${votaram} de ${total} apartamentos ${verbo} (${porcentagemEmTexto(votaram, total)}).`
}

/** O bloco da unidade está no destino da enquete (o selo e o "vota nela" da lista). */
export function noDestino(enquete: { para_todos: boolean; blocos: number[] }, bloco: number): boolean {
  return enquete.para_todos || enquete.blocos.includes(bloco)
}

/** Ordem crescente, por bloco e apartamento (do térreo ao último andar), na tela e no texto
 *  copiado: é a ordem em que a Comissão procura um apartamento. */
export function ordemCrescente(unidades: UnidadeRef[]): UnidadeRef[] {
  return [...unidades].sort(
    (a, b) => a.bloco - b.bloco || Number(a.apartamento) - Number(b.apartamento),
  )
}

/** O andar do apartamento ("701" → 7, "003" → 0). */
export function andar(u: UnidadeRef): number {
  return Math.floor(Number(u.apartamento) / 100)
}

function linhasPorBloco(unidades: UnidadeRef[]): string[] {
  const porBloco = new Map<number, string[]>()
  for (const u of ordemCrescente(unidades)) {
    porBloco.set(u.bloco, [...(porBloco.get(u.bloco) ?? []), u.apartamento])
  }
  return [...porBloco].map(([bloco, aptos]) => `Bloco ${bloco}: ${aptos.join(', ')}`)
}

/** Texto para colar no grupo: primeiro quem já usa o Portal (basta lembrar), depois quem nem
 *  entrou ainda. Só quem falta: quem votou não precisa de cobrança. */
export function faltamParaCopiar(pergunta: string, lista: Votantes): string {
  const partes = [`Ainda não votaram na enquete “${pergunta}”:`]
  if (lista.entraram_sem_votar.length) {
    partes.push(
      ['Entraram no Portal, mas não votaram:', ...linhasPorBloco(lista.entraram_sem_votar)].join(
        '\n',
      ),
    )
  }
  if (lista.nao_entraram.length) {
    partes.push(['Ainda não entraram no Portal:', ...linhasPorBloco(lista.nao_entraram)].join('\n'))
  }
  return partes.join('\n\n')
}
