// Comum · Compressão de foto no navegador, antes do envio (ADR-0004; spec do M3, seção 4).
// Foto com o lado maior acima de 1920 px é reduzida para 1920 px e regravada em WEBP (0,82); se
// o navegador não grava WEBP, JPEG (0,85, com fundo branco no lugar da transparência). Foto
// menor, mas acima do limite do destino (um print PNG pesado), é regravada com as mesmas
// dimensões. Se o resultado ficar maior, vai o original. PDF vai como está.
//
// JPEG é sempre regravado (resposta do Erick, 12/10/2026, dúvida 9 do M3), mesmo pequeno e
// dentro do limite, com as mesmas dimensões: regravar descarta os metadados (EXIF), inclusive a
// localização do GPS, que a foto do celular traz. Vai o regravado mesmo se ficar maior; se passar
// do limite, a tela recusa pelo tamanho, como qualquer outro. Só vai o original se o navegador não
// conseguir regravar.
import type { TipoArquivo } from './tipos'

export const LADO_MAXIMO = 1920

const EXTENSAO: Record<TipoArquivo, string> = {
  'application/pdf': '.pdf',
  'image/jpeg': '.jpg',
  'image/png': '.png',
  'image/webp': '.webp',
}

/** O que o navegador faz com a imagem. Separado para o teste (o jsdom não desenha). */
export interface Ferramentas {
  medir(arquivo: Blob): Promise<{ largura: number; altura: number }>
  /** `null` se o navegador não conseguiu gravar. O tipo do Blob diz o que ele gravou de fato. */
  regravar(
    arquivo: Blob,
    largura: number,
    altura: number,
    tipo: string,
    qualidade: number,
  ): Promise<Blob | null>
}

/** Lado maior em no máximo 1920 px, mantendo a proporção; nunca aumenta. */
export function dimensoesReduzidas(largura: number, altura: number, maximo = LADO_MAXIMO) {
  const escala = Math.min(1, maximo / Math.max(largura, altura))
  return { largura: Math.round(largura * escala), altura: Math.round(altura * escala) }
}

/** `foto.jpg` + WEBP → `foto.webp`. Um nome que só começa com ponto não tem extensão. */
export function nomeComExtensao(nome: string, tipo: TipoArquivo): string {
  const ponto = nome.lastIndexOf('.')
  const base = ponto > 0 ? nome.slice(0, ponto) : nome
  return base + EXTENSAO[tipo]
}

export const ferramentasDoNavegador: Ferramentas = {
  async medir(arquivo) {
    // `imageOrientation: 'from-image'`: a foto de celular deitada fica em pé (EXIF).
    const imagem = await createImageBitmap(arquivo, { imageOrientation: 'from-image' })
    try {
      return { largura: imagem.width, altura: imagem.height }
    } finally {
      imagem.close()
    }
  },
  async regravar(arquivo, largura, altura, tipo, qualidade) {
    const imagem = await createImageBitmap(arquivo, { imageOrientation: 'from-image' })
    try {
      const tela = document.createElement('canvas')
      tela.width = largura
      tela.height = altura
      const contexto = tela.getContext('2d')
      if (!contexto) return null
      if (tipo === 'image/jpeg') {
        // JPEG não tem transparência: sem fundo, o transparente do PNG sai preto.
        contexto.fillStyle = '#ffffff'
        contexto.fillRect(0, 0, largura, altura)
      }
      contexto.drawImage(imagem, 0, 0, largura, altura)
      return await new Promise<Blob | null>((pronto) => tela.toBlob(pronto, tipo, qualidade))
    } finally {
      imagem.close()
    }
  },
}

async function regravarComo(
  arquivo: File,
  ferramentas: Ferramentas,
  largura: number,
  altura: number,
  tipo: 'image/webp' | 'image/jpeg',
  qualidade: number,
): Promise<File | null> {
  const blob = await ferramentas.regravar(arquivo, largura, altura, tipo, qualidade)
  // O canvas devolve PNG quando não sabe gravar o tipo pedido.
  if (!blob || blob.type !== tipo) return null
  return new File([blob], nomeComExtensao(arquivo.name, tipo), { type: tipo })
}

/** O arquivo como deve ser enviado: a foto reduzida, ou o próprio arquivo. `limite` é o tamanho
 *  máximo do destino (`LIMITES[finalidade]`): a foto pequena acima dele também é regravada.
 *  Nunca falha: uma foto que o navegador não abre vai como está, e o servidor confere o
 *  conteúdo; a que continua grande é recusada na tela, pelo tamanho.
 *  `sempreRegravar` (os classificados, revisão M1): toda foto é regravada, como o JPEG, para
 *  sair qualquer metadado (PNG e WEBP também podem trazer). Os anexos do M3 seguem sem ele. */
export async function comprimir(
  arquivo: File,
  ferramentas: Ferramentas = ferramentasDoNavegador,
  limite = Infinity,
  sempreRegravar = false,
): Promise<File> {
  if (!arquivo.type.startsWith('image/')) return arquivo
  const semGps = arquivo.type === 'image/jpeg' || sempreRegravar
  try {
    const { largura, altura } = await ferramentas.medir(arquivo)
    const cabe = Math.max(largura, altura) <= LADO_MAXIMO && arquivo.size <= limite
    if (cabe && !semGps) return arquivo
    const novo = dimensoesReduzidas(largura, altura)
    const reduzido =
      (await regravarComo(arquivo, ferramentas, novo.largura, novo.altura, 'image/webp', 0.82)) ??
      (await regravarComo(arquivo, ferramentas, novo.largura, novo.altura, 'image/jpeg', 0.85))
    if (reduzido && semGps) return reduzido
    return reduzido && reduzido.size < arquivo.size ? reduzido : arquivo
  } catch {
    return arquivo
  }
}
