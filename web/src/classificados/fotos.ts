// Classificados · enviar uma foto (spec, seção 3.3; ADR-0012): o mesmo caminho do M3
// (`arquivos/enviar.ts`): conferir na tela → comprimir (a mesma compressão, que regrava o JPEG e
// tira o GPS) → pedir a URL → PUT direto no bucket → confirmar. As rotas são as dos classificados
// (qualquer unidade logada), e só imagem passa.
import { ErroDaApi } from '../api/cliente'
import { comprimir, ferramentasDoNavegador, type Ferramentas } from '../arquivos/comprimir'
import { prazoDoEnvio } from '../arquivos/enviar'
import { confirmarFoto, pedirFoto } from './api'
import type { TipoFoto } from './tipos'

const MB = 1024 * 1024
export const LIMITE_FOTO = 10 * MB
export const FOTOS_POR_ANUNCIO = 4
export const TIPOS_DE_FOTO: readonly TipoFoto[] = ['image/jpeg', 'image/png', 'image/webp']
export const ACEITAR_FOTOS = TIPOS_DE_FOTO.join(',')
export const MSG_TIPO_FOTO = 'O Portal aceita fotos em JPEG, PNG ou WEBP.'
export const MSG_TAMANHO_FOTO = 'A foto pode ter até 10 MB.'
export const MSG_FOTO_NAO_CHEGOU = 'A foto não chegou ao Portal. Confira a internet e envie de novo.'

function ehFoto(tipo: string): tipo is TipoFoto {
  return (TIPOS_DE_FOTO as readonly string[]).includes(tipo)
}

function recusada(mensagem: string): ErroDaApi {
  return new ErroDaApi(422, { codigo: 'dados_invalidos', mensagem })
}

/** O problema da foto na tela, ou `null`. */
export function problemaDaFoto(foto: Pick<File, 'type' | 'size'>): string | null {
  if (!ehFoto(foto.type)) return MSG_TIPO_FOTO
  if (foto.size < 1) return 'A foto está vazia. Escolha outra.'
  if (foto.size > LIMITE_FOTO) return MSG_TAMANHO_FOTO
  return null
}

/** Manda a foto e devolve a id dela (vai no anúncio), ou lança `ErroDaApi` com a frase pronta. */
export async function enviarFoto(
  escolhida: File,
  ferramentas: Ferramentas = ferramentasDoNavegador,
): Promise<number> {
  if (!ehFoto(escolhida.type)) throw recusada(MSG_TIPO_FOTO)
  const foto = await comprimir(escolhida, ferramentas, LIMITE_FOTO)
  const problema = problemaDaFoto(foto)
  if (problema) throw recusada(problema)

  const envio = await pedirFoto({ tipo: foto.type as TipoFoto, tamanho_bytes: foto.size })
  // Direto para o bucket, como no M3: sem `X-Portal`, sem cookie e com o Content-Type assinado.
  const resposta = await fetch(envio.url, {
    method: 'PUT',
    headers: { 'Content-Type': envio.content_type },
    body: foto,
    credentials: 'omit',
    cache: 'no-store',
    signal: AbortSignal.timeout(prazoDoEnvio(foto.size)),
  }).catch(() => null)
  if (!resposta?.ok) {
    throw new ErroDaApi(resposta?.status ?? 0, {
      codigo: 'arquivo_nao_chegou',
      mensagem: MSG_FOTO_NAO_CHEGOU,
    })
  }
  return (await confirmarFoto(envio.foto_id)).id
}
