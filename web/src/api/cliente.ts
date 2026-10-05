// Cliente da API (spec do M1, seção 5.5). Arquivo comum: os épicos usam, não editam.
//
// - Mesmo endereço da tela (/api/...), então o cookie de sessão vai sozinho.
// - Toda requisição leva `X-Portal: 1` (CSRF, ADR-0005); a API recusa alteração sem ele.
// - Resposta de erro vira `ErroDaApi`, com `codigo` (para decidir) e `mensagem` (para mostrar).
import type { CampoInvalido, ErroResposta } from './tipos'

export const MENSAGEM_SEM_CONEXAO = 'Sem conexão com o Portal. Confira a internet e tente de novo.'
const MENSAGEM_INESPERADA = 'Algo deu errado no Portal. Tente de novo daqui a pouco.'

export class ErroDaApi extends Error {
  readonly status: number
  readonly codigo: string
  readonly mensagem: string
  readonly campos: CampoInvalido[]
  /** Campos extras do erro, ex.: `bloqueada_ate` e `minutos_restantes`. */
  readonly extras: Record<string, unknown>

  constructor(status: number, corpo: ErroResposta & Record<string, unknown>) {
    super(corpo.mensagem)
    this.name = 'ErroDaApi'
    this.status = status
    this.codigo = corpo.codigo
    this.mensagem = corpo.mensagem
    this.campos = corpo.campos ?? []
    const extras: Record<string, unknown> = { ...corpo }
    delete extras.codigo
    delete extras.mensagem
    delete extras.campos
    this.extras = extras
  }

  /** Mensagem do campo, se a API apontou um problema nele (erro 422). */
  doCampo(campo: string): string | undefined {
    return this.campos.find((c) => c.campo === campo)?.mensagem
  }
}

type Metodo = 'GET' | 'POST' | 'PUT' | 'DELETE'
export type Consulta = Record<string, string | number | boolean | (string | number)[] | undefined>

/** `/api/avisos` + `{ busca: 'obra', blocos: [1, 2] }` → `/api/avisos?busca=obra&blocos=1&blocos=2`. */
export function comConsulta(caminho: string, consulta?: Consulta): string {
  const parametros = new URLSearchParams()
  for (const [chave, valor] of Object.entries(consulta ?? {})) {
    if (valor === undefined) continue
    for (const item of Array.isArray(valor) ? valor : [valor]) parametros.append(chave, String(item))
  }
  const texto = parametros.toString()
  return texto ? `${caminho}?${texto}` : caminho
}

function pareceErro(corpo: unknown): corpo is ErroResposta & Record<string, unknown> {
  return (
    typeof corpo === 'object' &&
    corpo !== null &&
    typeof (corpo as ErroResposta).codigo === 'string' &&
    typeof (corpo as ErroResposta).mensagem === 'string'
  )
}

export async function pedir<T>(metodo: Metodo, caminho: string, corpo?: unknown): Promise<T> {
  const cabecalhos: Record<string, string> = { 'X-Portal': '1', Accept: 'application/json' }
  if (corpo !== undefined) cabecalhos['Content-Type'] = 'application/json'

  let resposta: Response
  try {
    resposta = await fetch(caminho, {
      method: metodo,
      headers: cabecalhos,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      credentials: 'same-origin',
      cache: 'no-store',
    })
  } catch (erro) {
    if (erro instanceof DOMException && erro.name === 'AbortError') throw erro
    throw new ErroDaApi(0, { codigo: 'sem_conexao', mensagem: MENSAGEM_SEM_CONEXAO })
  }

  if (resposta.status === 204) return undefined as T
  const conteudo: unknown = await resposta.json().catch(() => null)
  if (resposta.ok) return conteudo as T
  if (pareceErro(conteudo)) throw new ErroDaApi(resposta.status, conteudo)
  throw new ErroDaApi(resposta.status, { codigo: 'erro_inesperado', mensagem: MENSAGEM_INESPERADA })
}

export const api = {
  get: <T>(caminho: string, consulta?: Consulta) => pedir<T>('GET', comConsulta(caminho, consulta)),
  post: <T>(caminho: string, corpo?: unknown) => pedir<T>('POST', caminho, corpo),
  put: <T>(caminho: string, corpo?: unknown) => pedir<T>('PUT', caminho, corpo),
  delete: <T>(caminho: string) => pedir<T>('DELETE', caminho),
}
