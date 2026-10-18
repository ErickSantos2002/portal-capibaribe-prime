// Lista única de lugares do Portal (spec da navegação com bola, seção 5). Dela saem a barra do
// celular (os lugares com `naBarra`), a folha do Menu e o menu lateral do computador (todos,
// agrupados). Pôr um lugar novo = acrescentar uma entrada aqui.
// "Unidades" é da gestão (Comissão e administração), que vê os contatos das unidades, e mora só
// na folha. "Documentos" (M3) vem do épico A; "Enquetes" (M4), do épico B do M4.
import type { Eu } from '../api/tipos'
import { itemDocumentos } from '../documentos/menu'
import { itemEnquetes } from '../enquetes/votar/menu'
import type { NomeDoIcone } from './Icone'

export type Grupo = 'dia-a-dia' | 'gestao'

export const NOMES_DOS_GRUPOS: Record<Grupo, string> = {
  'dia-a-dia': 'Dia a dia',
  gestao: 'Gestão',
}

export interface Lugar {
  para: string
  icone: NomeDoIcone
  texto: string
  /** Rótulo da barra em tela estreita (< 340 px). O nome acessível continua sendo `texto`. */
  curto?: string
  /** Frase curta da folha do Menu, que diz o que tem lá. */
  frase: string
  grupo: Grupo
  /** Posição fixa na barra: 1 e 2 à esquerda da bola, 3 e 4 à direita. Sem ela, só na folha. */
  naBarra?: 1 | 2 | 3 | 4
}

export function lugaresDo(eu: Eu): Lugar[] {
  const enquetes = itemEnquetes(eu)
  const documentos = itemDocumentos(eu)
  const lugares: Lugar[] = [
    {
      para: '/avisos',
      icone: 'avisos',
      texto: 'Avisos',
      frase: 'Recados da Comissão e da obra',
      grupo: 'dia-a-dia',
      naBarra: 1,
    },
    ...(enquetes ? [enquetes] : []),
    ...(documentos ? [documentos] : []),
    {
      para: '/minha-unidade',
      icone: 'casa',
      texto: 'Minha unidade',
      frase: 'Senha, contato e e-mail',
      grupo: 'dia-a-dia',
      naBarra: 4,
    },
  ]
  if (eu.gestao) {
    lugares.push({
      para: '/unidades',
      icone: 'painel',
      texto: 'Unidades',
      frase: 'Quem já entrou e os contatos',
      grupo: 'gestao',
    })
  }
  return lugares
}

/** As 4 posições da barra. Um lugar que não vale para alguém deixa a vaga (null): ninguém sobe,
 * porque uma barra que muda de ordem confunde (spec, seção 5). */
export function daBarra(lugares: Lugar[]): (Lugar | null)[] {
  return ([1, 2, 3, 4] as const).map((posicao) => lugares.find((l) => l.naBarra === posicao) ?? null)
}

export function agrupados(lugares: Lugar[]): { grupo: Grupo; nome: string; lugares: Lugar[] }[] {
  return (Object.keys(NOMES_DOS_GRUPOS) as Grupo[])
    .map((grupo) => ({ grupo, nome: NOMES_DOS_GRUPOS[grupo], lugares: lugares.filter((l) => l.grupo === grupo) }))
    .filter((g) => g.lugares.length > 0)
}

/** O lugar em que a pessoa está: o de endereço mais longo que começa o caminho atual. */
export function lugarAtual(lugares: Lugar[], pathname: string): Lugar | undefined {
  return lugares
    .filter((l) => pathname === l.para || pathname.startsWith(`${l.para}/`))
    .sort((a, b) => b.para.length - a.para.length)[0]
}
