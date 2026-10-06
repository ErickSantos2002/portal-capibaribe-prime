// Itens do menu (abas no celular, menu lateral no computador). "Unidades" para a gestão
// (Comissão e administração), que vê os contatos das unidades.
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
  if (eu.gestao) itens.push({ para: '/unidades', icone: 'painel', texto: 'Unidades' })
  return itens
}
