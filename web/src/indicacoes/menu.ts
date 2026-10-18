// Indicações · o lugar no menu (spec, seção 3.4). Chamado por `casca/menu.ts`, entre Documentos
// e Minha unidade. Fora da barra do celular: mora na folha do Menu e no menu lateral.
import type { Eu } from '../api/tipos'
import type { Lugar } from '../casca/menu'

export function itemIndicacoes(eu: Eu): Lugar {
  void eu
  return {
    para: '/indicacoes',
    icone: 'indicacoes',
    texto: 'Indicações',
    frase: 'Serviços que os vizinhos recomendam',
    grupo: 'dia-a-dia',
  }
}
