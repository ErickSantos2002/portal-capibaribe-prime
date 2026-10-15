// Épico A do M4 · as contas do formulário de enquete (spec do épico, seção 2). Pertence ao
// épico A. As frases repetem as da API (`app/esquemas/enquetes.py` e
// `app/servicos/enquetes_gestao.py`): a tela avisa antes, a API confere de novo.
import type { MostrarResultado } from '../tipos'
import { quandoTermina } from '../votar/formatos'

export const LIMITE_PERGUNTA = 200
export const LIMITE_OPCAO = 100
export const MIN_OPCOES = 2
export const MAX_OPCOES = 10
const LIMITE_TITULO_AVISO = 120
const UMA_HORA = 60 * 60 * 1000
// A API aceita até 365 dias (a tela fala em "1 ano").
const UM_ANO = 365 * 24 * UMA_HORA
// Recife não tem horário de verão desde 2019: UTC-3 fixo, como na API.
const FUSO_DE_RECIFE = '-03:00'
const TRES_HORAS = 3 * UMA_HORA

export interface Rascunho {
  pergunta: string
  /** Na ordem da tela; as caixas em branco são descartadas ao enviar. */
  opcoes: string[]
  multipla: boolean
  /** `AAAA-MM-DD` e `HH:MM`, no horário de Recife. */
  dia: string
  hora: string
  mostrar: MostrarResultado
}

export const RASCUNHO_VAZIO: Rascunho = {
  pergunta: '',
  opcoes: ['', ''],
  multipla: false,
  dia: '',
  hora: '20:00',
  mostrar: 'durante',
}

export type Campo = 'pergunta' | 'opcoes' | 'termino' | 'blocos'
export type Erros = Partial<Record<Campo, string>>

/** Dia e hora de Recife → data com fuso, como a API pede. */
export function paraIso(dia: string, hora: string): string {
  return `${dia}T${hora}:00${FUSO_DE_RECIFE}`
}

/** Data da API (qualquer fuso) → dia e hora de Recife, para o formulário de editar. */
export function deIso(iso: string): { dia: string; hora: string } {
  const emRecife = new Date(new Date(iso).getTime() - TRES_HORAS).toISOString()
  return { dia: emRecife.slice(0, 10), hora: emRecife.slice(11, 16) }
}

/** O destino que a API grava, a partir dos botões. */
export function destinoEmTexto(paraTodos: boolean, blocos: readonly number[]): string {
  if (paraTodos || blocos.length === 0) return 'Todos os blocos'
  if (blocos.length === 1) return `Bloco ${blocos[0]}`
  return `Blocos ${blocos.slice(0, -1).join(', ')} e ${blocos[blocos.length - 1]}`
}

/** NFC e sem espaço nas pontas, como a API grava (revisão, ponto 6). */
export function limpo(texto: string): string {
  return texto.normalize('NFC').trim()
}

/** Letras contadas como a API conta (por code point): um emoji é uma letra (revisão, ponto 7). */
export function letras(texto: string): number {
  return Array.from(texto).length
}

/** Um texto só de acentos soltos ou pontuação não aparece (revisão, ponto 6). */
function temLetraOuNumero(texto: string): boolean {
  return /[\p{L}\p{N}]/u.test(texto)
}

export function opcoesLimpas(opcoes: readonly string[]): string[] {
  return opcoes.map(limpo).filter(Boolean)
}

/** "Sábado de manhã" e "sábado  de MANHÃ" são a mesma opção. O mais perto possível do
 *  `casefold` da API (revisão, ponto 8): NFC, minúsculas e "ß" vira "ss". Não é igual em
 *  tudo (o `casefold` também dobra, por exemplo, o "ﬁ" ligado); a API é a palavra final. */
function comparavel(texto: string): string {
  return texto
    .normalize('NFC')
    .toLocaleLowerCase('pt-BR')
    .replace(/ß/g, 'ss')
    .split(/\s+/)
    .filter(Boolean)
    .join(' ')
}

function conferirTermino(dia: string, hora: string, agora: Date): string | undefined {
  if (!dia) return 'Escolha o dia do término.'
  if (!hora) return 'Escolha a hora do término.'
  const quando = new Date(paraIso(dia, hora)).getTime()
  if (Number.isNaN(quando)) return 'Escolha o dia do término.'
  const falta = quando - agora.getTime()
  if (falta > UM_ANO) return 'A enquete pode durar até 1 ano.'
  if (falta <= 0) return 'A data de término já passou. Escolha uma data no futuro.'
  if (falta < UMA_HORA) return 'Escolha um término daqui a pelo menos 1 hora.'
  return undefined
}

function conferirOpcoes(opcoes: readonly string[]): string | undefined {
  const limpas = opcoesLimpas(opcoes)
  if (limpas.some((o) => !temLetraOuNumero(o))) return 'Cada opção precisa ter letras ou números.'
  if (limpas.some((o) => letras(o) > LIMITE_OPCAO)) {
    return `Cada opção pode ter até ${LIMITE_OPCAO} letras.`
  }
  if (limpas.length < MIN_OPCOES) return 'Escreva pelo menos 2 opções de resposta.'
  if (limpas.length > MAX_OPCOES) return `O limite é de ${MAX_OPCOES} opções.`
  if (new Set(limpas.map(comparavel)).size < limpas.length) return 'Duas opções estão iguais.'
  return undefined
}

/**
 * O que falta ou está errado, campo por campo (vazio: pode enviar). `terminoGravado`, na
 * edição: se o término é o mesmo, não confere de novo (a enquete está aberta; a API confere
 * o resto). Revisão, ponto 4: perto do fim, dá para corrigir a pergunta sem adiar o prazo.
 */
export function conferir(
  r: Rascunho,
  agora: Date = new Date(),
  terminoGravado?: { dia: string; hora: string },
): Erros {
  const erros: Erros = {}
  const pergunta = limpo(r.pergunta)
  if (!pergunta) erros.pergunta = 'Escreva a pergunta.'
  else if (!temLetraOuNumero(pergunta)) erros.pergunta = 'Escreva a pergunta com letras ou números.'
  else if (letras(pergunta) > LIMITE_PERGUNTA) {
    erros.pergunta = `A pergunta pode ter até ${LIMITE_PERGUNTA} letras.`
  }
  const opcoes = conferirOpcoes(r.opcoes)
  if (opcoes) erros.opcoes = opcoes
  const mesmoTermino =
    !!terminoGravado && terminoGravado.dia === r.dia && terminoGravado.hora === r.hora
  const termino = mesmoTermino ? undefined : conferirTermino(r.dia, r.hora, agora)
  if (termino) erros.termino = termino
  return erros
}

// --- o aviso automático (spec do épico, seção 1.2) ----------------------------------------------

/** Corta por code point, como a API: nunca parte um emoji ao meio (revisão, ponto 7). */
export function tituloDoAviso(pergunta: string): string {
  const completo = Array.from(`Enquete nova: ${limpo(pergunta)}`)
  if (completo.length <= LIMITE_TITULO_AVISO) return completo.join('')
  return completo.slice(0, LIMITE_TITULO_AVISO - 1).join('').trimEnd() + '…'
}

/** O texto que a API vai publicar no mural (a mesma frase, para a prévia). A data por extenso,
 *  como na tela da enquete ("16 de outubro, às 20h"; em outro ano, com o ano): ajustes do M4,
 *  ponto 16; a API usa `quando_em_texto`, com a mesma regra. */
export function textoDoAviso(r: Rascunho, agora: Date = new Date()): string {
  const lista = opcoesLimpas(r.opcoes)
    .map((o) => `- ${o}`)
    .join('\n')
  const escolha = r.multipla ? 'Pode marcar mais de uma opção.' : 'Marque uma opção.'
  const resultado =
    r.mostrar === 'so_no_fim'
      ? 'O resultado só aparece quando a enquete terminar.'
      : 'O resultado aparece durante a votação.'
  return (
    `Uma enquete nova está aberta no Portal: “${limpo(r.pergunta)}”.\n\n` +
    `As opções são:\n\n${lista}\n\n` +
    `Dá para votar até ${quandoTermina(paraIso(r.dia, r.hora), agora)} (horário de Recife). ${escolha} Vale um voto` +
    ` por apartamento, e dá para trocar o voto até o fim. ${resultado}\n\n` +
    '> Enquete é consulta. Não tem valor legal de votação em assembleia.\n\n' +
    'O botão “Ir para a enquete”, neste aviso, leva direto a ela.'
  )
}
