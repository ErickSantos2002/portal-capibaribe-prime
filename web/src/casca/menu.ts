// Itens do menu (abas no celular, menu lateral no computador). "Unidades" só para o admin.
import type { Eu } from '../api/tipos'
import type { NomeDoIcone } from './Icone'

export interface Item {
  para: string
  icone: NomeDoIcone
  texto: string
}

export function itensDoMenu(eu: Eu): Item[] {
  const itens: Item[] = [
    { para: '/avisos', icone: 'avisos', texto: 'Avisos' },
    { para: '/minha-unidade', icone: 'casa', texto: 'Minha unidade' },
  ]
  if (eu.admin) itens.push({ para: '/unidades', icone: 'painel', texto: 'Unidades' })
  return itens
}
