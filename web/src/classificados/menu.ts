// Classificados · o lugar no menu (spec, seção 3.4). Chamado por `casca/menu.ts`, logo depois de
// Indicações. Fora da barra do celular: mora na folha do Menu e no menu lateral.
import type { Eu } from '../api/tipos'
import type { Lugar } from '../casca/menu'

export function itemClassificados(eu: Eu): Lugar {
  void eu
  return {
    para: '/classificados',
    icone: 'classificados',
    texto: 'Classificados',
    frase: 'Vender, trocar ou doar entre vizinhos',
    grupo: 'dia-a-dia',
  }
}
