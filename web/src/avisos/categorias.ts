// As 5 categorias do aviso (spec dos avisos com formatação, seção 2): nome, ícone e a classe que
// escolhe as cores (`.cat-<valor>` em avisos.css, tokens `--cat-*` em estilo.css). A categoria
// nunca aparece só pela cor: sempre ícone e nome.
import type { NomeDoIcone } from '../casca/Icone'
import type { Categoria } from './tipos'

export interface InfoCategoria {
  valor: Categoria
  nome: string
  icone: NomeDoIcone
}

/** Na ordem dos botões do formulário; `geral` é o padrão. */
export const CATEGORIAS: readonly InfoCategoria[] = [
  { valor: 'geral', nome: 'Geral', icone: 'geral' },
  { valor: 'obra', nome: 'Obra', icone: 'obra' },
  { valor: 'reuniao', nome: 'Reunião', icone: 'reuniao' },
  { valor: 'financeiro', nome: 'Financeiro', icone: 'financeiro' },
  { valor: 'urgente', nome: 'Urgente', icone: 'alerta' },
]

export function infoDaCategoria(valor: Categoria): InfoCategoria {
  return CATEGORIAS.find((c) => c.valor === valor) ?? CATEGORIAS[0]
}
