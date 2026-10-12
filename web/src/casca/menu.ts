// Itens do menu (abas no celular, menu lateral no computador). "Unidades" para a gestão
// (Comissão e administração), que vê os contatos das unidades. "Documentos" (M3) vem do épico A.
import type { Eu } from '../api/tipos'
import { itemDocumentos } from '../documentos/menu'
import type { NomeDoIcone } from './Icone'

export interface Item {
  para: string
  icone: NomeDoIcone
  texto: string
}

export function itensDoMenu(eu: Eu): Item[] {
  const documentos = itemDocumentos(eu)
  const itens: Item[] = [
    { para: '/avisos', icone: 'avisos', texto: 'Avisos' },
    ...(documentos ? [documentos] : []),
    { para: '/minha-unidade', icone: 'casa', texto: 'Minha unidade' },
  ]
  if (eu.gestao) itens.push({ para: '/unidades', icone: 'painel', texto: 'Unidades' })
  return itens
}
