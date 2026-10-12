// Épico A do M3 · abrir e baixar o arquivo de um documento (spec do épico, seção 3).
// Pertence ao épico A.
//
// O link vale 5 minutos e é pedido no toque (contrato, seção 5.2). Mas o navegador só deixa
// abrir aba nova **no próprio toque**: depois de esperar a API, o `window.open` é bloqueado
// (Safari do iPhone, sobretudo). Por isso a aba abre antes, vazia, e recebe o endereço quando o
// link chega. Sem aba (bloqueada mesmo assim), a própria tela vai para o arquivo; o "voltar"
// do celular traz de volta ao Portal.
import { useState } from 'react'
import { comoErroDaApi } from './carregar'
import type { LinkDoArquivo } from '../arquivos/tipos'

/** O que toca no navegador, num objeto só: os testes trocam as duas funções. */
export const navegador = {
  abrirAba(): Window | null {
    return window.open('', '_blank')
  },
  irPara(url: string): void {
    window.location.assign(url)
  },
}

type Pedir = () => Promise<LinkDoArquivo>

function avisarQueEstaAbrindo(aba: Window): void {
  try {
    aba.document.title = 'Abrindo o documento…'
    aba.document.body.textContent = 'Abrindo o documento…'
  } catch {
    // Aba de outro endereço ou sem documento: só não mostra o recado.
  }
}

export async function abrirArquivo(pedir: Pedir): Promise<void> {
  const aba = navegador.abrirAba()
  if (aba) avisarQueEstaAbrindo(aba)
  try {
    const { url } = await pedir()
    if (aba) {
      // A aba do arquivo não precisa (nem deve) mexer na tela do Portal.
      aba.opener = null
      aba.location.href = url
    } else {
      navegador.irPara(url)
    }
  } catch (erro) {
    aba?.close()
    throw erro
  }
}

/** O link com `baixar=true` vem como anexo: o navegador salva e o Portal fica na tela. */
export async function baixarArquivo(pedir: Pedir): Promise<void> {
  const { url } = await pedir()
  navegador.irPara(url)
}

/** `const { abrir, baixar, ocupado, erro } = useArquivo()`: um pedido de cada vez, e o erro na
 *  voz do morador. `ocupado` diz qual botão está esperando. */
export function useArquivo() {
  const [ocupado, setOcupado] = useState<string | null>(null)
  const [erro, setErro] = useState('')

  async function executar(chave: string, acao: () => Promise<void>) {
    if (ocupado) return
    setOcupado(chave)
    setErro('')
    try {
      await acao()
    } catch (e) {
      setErro(comoErroDaApi(e).mensagem)
    } finally {
      setOcupado(null)
    }
  }

  return {
    ocupado,
    erro,
    abrir: (chave: string, pedir: Pedir) => executar(chave, () => abrirArquivo(pedir)),
    baixar: (chave: string, pedir: Pedir) => executar(chave, () => baixarArquivo(pedir)),
  }
}
