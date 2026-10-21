// Classificados · formatos da tela: o selo do tipo, o preço, "há quanto tempo", o WhatsApp com a
// mensagem pronta (spec, seções 3.1 e 3.2).
import type { MotivoEncerramento, SituacaoAnuncio, TipoAnuncio } from './tipos'

const reais = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const inteiro = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })

/** "R$ 350" (redondo) ou "R$ 1.250,50". */
export function precoEmReais(centavos: number): string {
  return centavos % 100 === 0 ? `R$ ${inteiro.format(centavos / 100)}` : `R$ ${reais.format(centavos / 100)}`
}

const ESPACO_FIXO = ' '

/** "Vende R$ 350", "Vende · a combinar", "Troca", "Doa". Numa tela estreita, só quebra depois de
 *  "Vende" (ou do "·"): nunca "R$" de um lado e o valor do outro, nem "a" sozinho (revisão UX 17). */
export function seloDoTipo(tipo: TipoAnuncio, preco: number | null): string {
  if (tipo === 'troca') return 'Troca'
  if (tipo === 'doacao') return 'Doa'
  if (preco === null) return `Vende${ESPACO_FIXO}· a${ESPACO_FIXO}combinar`
  return `Vende ${precoEmReais(preco).replace(' ', ESPACO_FIXO)}`
}

/** O que a pessoa escreveu no campo do preço, em centavos. Vazio = `null` ("a combinar");
 *  inválido = `NaN`. Aceita "R$", ponto de milhar e vírgula (ou ponto) dos centavos. */
export function centavosDoTexto(texto: string): number | null {
  const limpo = texto.replace(/R\$/i, '').replace(/\s/g, '')
  if (!limpo) return null
  let normal = limpo
  if (/,/.test(normal)) normal = normal.replace(/\./g, '').replace(',', '.')
  else if (/^\d{1,3}(\.\d{3})+$/.test(normal)) normal = normal.replace(/\./g, '')
  if (!/^\d+(\.\d{1,2})?$/.test(normal)) return NaN
  return Math.round(Number(normal) * 100)
}

/** Centavos de volta para o campo, ao editar: "350" ou "1250,50". */
export function precoNoCampo(centavos: number | null): string {
  if (centavos === null) return ''
  const reaisInteiros = Math.floor(centavos / 100)
  const resto = centavos % 100
  return resto === 0 ? String(reaisInteiros) : `${reaisInteiros},${String(resto).padStart(2, '0')}`
}

const FUSO = 'America/Recife'
const dia = new Intl.DateTimeFormat('en-CA', { timeZone: FUSO })

function diasEntre(de: Date, ate: Date): number {
  const [a, b] = [dia.format(de), dia.format(ate)].map((d) => Date.parse(`${d}T00:00:00Z`))
  return Math.round((b - a) / 86_400_000)
}

/** "hoje", "ontem", "há 3 dias" (no calendário de Recife). */
export function haQuanto(iso: string, agora: Date = new Date()): string {
  const dias = Math.max(0, diasEntre(new Date(iso), agora))
  if (dias === 0) return 'hoje'
  if (dias === 1) return 'ontem'
  return `há ${dias} dias`
}

/** A mensagem pronta; o reservado pede para ser lembrado se não der certo (revisão UX 9). */
export function mensagemDoWhatsApp(titulo: string, reservado = false): string {
  if (reservado) {
    return `Oi! Vi seu anúncio "${titulo}" no Portal Capibaribe Prime. Vi que está reservado; se não der certo, tenho interesse.`
  }
  return `Oi! Vi seu anúncio "${titulo}" no Portal Capibaribe Prime. Ainda está disponível?`
}

/** `https://wa.me/55<dígitos>?text=<mensagem>` (spec, seção 3.2). */
export function linkWhatsAppDoAnuncio(digitos: string, titulo: string, reservado = false): string {
  return `https://wa.me/55${digitos}?text=${encodeURIComponent(mensagemDoWhatsApp(titulo, reservado))}`
}

const MOTIVOS: Record<MotivoEncerramento, string> = {
  vendi: 'Vendido',
  troquei: 'Trocado',
  doei: 'Doado',
  desisti: 'Desistiu',
}

export function textoDoMotivo(motivo: MotivoEncerramento): string {
  return MOTIVOS[motivo]
}

/** O selo da situação no cartão, ou nada quando está ativo e no prazo. */
export function seloDaSituacao(
  situacao: SituacaoAnuncio,
  vencido: boolean,
  escondido: boolean,
): string | null {
  if (escondido) return 'Escondido pela gestão'
  if (situacao === 'encerrado') return 'Encerrado'
  if (vencido) return 'Vencido'
  if (situacao === 'reservado') return 'Reservado'
  return null
}

export function encontrados(n: number): string {
  if (n === 0) return 'Nenhum anúncio encontrado.'
  return n === 1 ? '1 anúncio encontrado.' : `${n} anúncios encontrados.`
}

export function comAvisoEmTexto(n: number): string {
  return n === 1 ? '1 anúncio com aviso da vizinhança' : `${n} anúncios com aviso da vizinhança`
}
