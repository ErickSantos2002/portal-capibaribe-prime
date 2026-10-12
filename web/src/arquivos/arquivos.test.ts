// Envio de arquivo no front (spec do M3, seções 4 e 7): limites iguais aos da API, compressão de
// foto e o caminho inteiro de `enviarArquivo` (conferir na tela → comprimir → pedir → PUT no
// bucket → confirmar).
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroDaApi } from '../api/cliente'
import { confirmarEnvio, pedirEnvio } from './api'
import {
  comprimir,
  dimensoesReduzidas,
  ferramentasDoNavegador,
  LADO_MAXIMO,
  nomeComExtensao,
  type Ferramentas,
} from './comprimir'
import { enviarArquivo, MENSAGEM_NAO_CHEGOU, prazoDoEnvio } from './enviar'
import { ACEITAR, LIMITES, mensagemDoLimite, MSG_TIPO, problemaNaTela, TIPOS_ACEITOS } from './limites'
import type { ArquivoEnviado, EnvioAutorizado } from './tipos'

const MB = 1024 * 1024

function arquivo(nome: string, tipo: string, tamanho = 1000): File {
  return new File([new Uint8Array(tamanho)], nome, { type: tipo })
}

/** Ferramentas de imagem de mentira: o jsdom não desenha. */
function ferramentas(largura: number, altura: number, saida: Blob | null): Ferramentas & {
  regravar: ReturnType<typeof vi.fn>
} {
  return {
    medir: vi.fn(async () => ({ largura, altura })),
    regravar: vi.fn(async () => saida),
  }
}

afterEach(() => vi.unstubAllGlobals())

describe('limites (iguais aos da API: app/modelos/arquivos.py)', () => {
  it('quatro tipos, 10 MB no aviso e 20 MB no documento', () => {
    expect([...TIPOS_ACEITOS]).toEqual(['application/pdf', 'image/jpeg', 'image/png', 'image/webp'])
    expect(LIMITES).toEqual({ aviso: 10 * MB, documento: 20 * MB })
    expect(ACEITAR).toBe('application/pdf,image/jpeg,image/png,image/webp')
  })

  it('mensagens iguais às da API', () => {
    expect(MSG_TIPO).toBe('O Portal aceita PDF e fotos (JPEG, PNG ou WEBP).')
    expect(mensagemDoLimite('aviso')).toBe('O arquivo pode ter até 10 MB.')
    expect(mensagemDoLimite('documento')).toBe('O arquivo pode ter até 20 MB.')
  })

  it('problemaNaTela: tipo, vazio e tamanho, no limite exato passa', () => {
    expect(problemaNaTela(arquivo('a.pdf', 'application/pdf'), 'aviso')).toBeNull()
    expect(problemaNaTela(arquivo('a.exe', 'application/x-msdownload'), 'aviso')).toBe(MSG_TIPO)
    expect(problemaNaTela(arquivo('a.gif', 'image/gif'), 'documento')).toBe(MSG_TIPO)
    expect(problemaNaTela(arquivo('a.pdf', 'application/pdf', 0), 'aviso')).toBe(
      'O arquivo está vazio. Escolha outro.',
    )
    const dez = { name: 'a.pdf', type: 'application/pdf', size: 10 * MB }
    expect(problemaNaTela(dez, 'aviso')).toBeNull()
    expect(problemaNaTela({ ...dez, size: 10 * MB + 1 }, 'aviso')).toBe(mensagemDoLimite('aviso'))
    expect(problemaNaTela({ ...dez, size: 10 * MB + 1 }, 'documento')).toBeNull()
  })
})

describe('compressão de foto (ADR-0004)', () => {
  it('reduz o lado maior a 1920 px, mantendo a proporção', () => {
    expect(LADO_MAXIMO).toBe(1920)
    expect(dimensoesReduzidas(4000, 3000)).toEqual({ largura: 1920, altura: 1440 })
    expect(dimensoesReduzidas(3000, 4000)).toEqual({ largura: 1440, altura: 1920 })
    expect(dimensoesReduzidas(3001, 1001)).toEqual({ largura: 1920, altura: 640 })
  })

  it('nunca aumenta a foto', () => {
    expect(dimensoesReduzidas(1920, 1080)).toEqual({ largura: 1920, altura: 1080 })
    expect(dimensoesReduzidas(800, 600)).toEqual({ largura: 800, altura: 600 })
  })

  it('troca a extensão pela do tipo novo', () => {
    expect(nomeComExtensao('foto.jpg', 'image/webp')).toBe('foto.webp')
    expect(nomeComExtensao('Reunião 03.JPEG', 'image/jpeg')).toBe('Reunião 03.jpg')
    expect(nomeComExtensao('sem-extensao', 'image/webp')).toBe('sem-extensao.webp')
    expect(nomeComExtensao('.oculto', 'image/webp')).toBe('.oculto.webp')
  })

  it('PDF vai como está, sem nem medir', async () => {
    const pdf = arquivo('ata.pdf', 'application/pdf')
    const f = ferramentas(4000, 3000, new Blob(['x'], { type: 'image/webp' }))
    await expect(comprimir(pdf, f)).resolves.toBe(pdf)
    expect(f.medir).not.toHaveBeenCalled()
  })

  it('foto pequena vai como está', async () => {
    const foto = arquivo('foto.jpg', 'image/jpeg')
    const f = ferramentas(1600, 1200, new Blob(['x'], { type: 'image/webp' }))
    await expect(comprimir(foto, f)).resolves.toBe(foto)
    expect(f.regravar).not.toHaveBeenCalled()
  })

  it('foto grande vira WEBP 0,82 em 1920 px, com o nome novo', async () => {
    const foto = arquivo('foto.jpg', 'image/jpeg', 5000)
    const f = ferramentas(4000, 3000, new Blob([new Uint8Array(900)], { type: 'image/webp' }))
    const saida = await comprimir(foto, f)
    expect(f.regravar).toHaveBeenCalledWith(foto, 1920, 1440, 'image/webp', 0.82)
    expect([saida.name, saida.type, saida.size]).toEqual(['foto.webp', 'image/webp', 900])
  })

  it('navegador que não grava WEBP: JPEG 0,85', async () => {
    const foto = arquivo('foto.png', 'image/png', 5000)
    const f = ferramentas(4000, 3000, null)
    f.regravar
      .mockResolvedValueOnce(new Blob([new Uint8Array(10)], { type: 'image/png' }))
      .mockResolvedValueOnce(new Blob([new Uint8Array(700)], { type: 'image/jpeg' }))
    const saida = await comprimir(foto, f)
    expect(f.regravar).toHaveBeenLastCalledWith(foto, 1920, 1440, 'image/jpeg', 0.85)
    expect([saida.name, saida.type, saida.size]).toEqual(['foto.jpg', 'image/jpeg', 700])
  })

  it('resultado maior que o original: vai o original', async () => {
    const foto = arquivo('foto.webp', 'image/webp', 500)
    const f = ferramentas(4000, 3000, new Blob([new Uint8Array(800)], { type: 'image/webp' }))
    await expect(comprimir(foto, f)).resolves.toBe(foto)
  })

  it('foto pequena acima do limite do destino é regravada em WEBP, com as mesmas dimensões', async () => {
    // Um print PNG de 1900 px e 12 MB não passa no aviso (10 MB) como está.
    const foto = arquivo('print.png', 'image/png', 12 * MB)
    const f = ferramentas(1900, 1000, new Blob([new Uint8Array(2 * MB)], { type: 'image/webp' }))
    const saida = await comprimir(foto, f, LIMITES.aviso)
    expect(f.regravar).toHaveBeenCalledWith(foto, 1900, 1000, 'image/webp', 0.82)
    expect([saida.name, saida.type, saida.size]).toEqual(['print.webp', 'image/webp', 2 * MB])
  })

  it('foto pequena acima do limite que não diminui ao regravar: vai a original', async () => {
    const foto = arquivo('print.png', 'image/png', 12 * MB)
    const f = ferramentas(1900, 1000, new Blob([new Uint8Array(13 * MB)], { type: 'image/webp' }))
    await expect(comprimir(foto, f, LIMITES.aviso)).resolves.toBe(foto)
  })

  it('foto pequena dentro do limite continua indo como está', async () => {
    const foto = arquivo('foto.jpg', 'image/jpeg', 2 * MB)
    const f = ferramentas(1600, 1200, new Blob(['x'], { type: 'image/webp' }))
    await expect(comprimir(foto, f, LIMITES.aviso)).resolves.toBe(foto)
    expect(f.regravar).not.toHaveBeenCalled()
  })

  it('regravar em JPEG pinta o fundo de branco antes (PNG transparente não fica preto)', async () => {
    const passos: string[] = []
    const contexto = {
      set fillStyle(cor: string) {
        passos.push(`cor ${cor}`)
      },
      fillRect: vi.fn(() => passos.push('fundo')),
      drawImage: vi.fn(() => passos.push('imagem')),
    }
    vi.stubGlobal(
      'createImageBitmap',
      vi.fn(async () => ({ width: 10, height: 10, close: vi.fn() })),
    )
    const getContext = vi
      .spyOn(HTMLCanvasElement.prototype, 'getContext')
      .mockReturnValue(contexto as unknown as CanvasRenderingContext2D)
    const toBlob = vi
      .spyOn(HTMLCanvasElement.prototype, 'toBlob')
      .mockImplementation((pronto, tipo) => pronto(new Blob(['x'], { type: tipo })))
    try {
      const png = arquivo('logo.png', 'image/png')
      await ferramentasDoNavegador.regravar(png, 10, 10, 'image/jpeg', 0.85)
      expect(passos).toEqual(['cor #ffffff', 'fundo', 'imagem'])
      passos.length = 0
      await ferramentasDoNavegador.regravar(png, 10, 10, 'image/webp', 0.82)
      expect(passos).toEqual(['imagem'])
    } finally {
      getContext.mockRestore()
      toBlob.mockRestore()
    }
  })

  it('foto que o navegador não consegue abrir vai como está (o servidor confere)', async () => {
    const foto = arquivo('foto.jpg', 'image/jpeg')
    const f: Ferramentas = {
      medir: vi.fn(async () => {
        throw new Error('imagem quebrada')
      }),
      regravar: vi.fn(),
    }
    await expect(comprimir(foto, f)).resolves.toBe(foto)
  })
})

// --- envio ------------------------------------------------------------------------------------

const AUTORIZADO: EnvioAutorizado = {
  arquivo_id: 42,
  url: 'https://conta.r2.cloudflarestorage.com/portal-capibaribe-arquivos/envios/abc?X-Amz-Signature=x',
  content_type: 'application/pdf',
  expira_em: '2026-11-03T12:10:00Z',
}
const ENVIADO: ArquivoEnviado = { id: 42, nome: 'ata.pdf', tipo: 'application/pdf', tamanho_bytes: 1000 }

function json(status: number, corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/** API e bucket de mentira; `put` decide o que o bucket responde. */
function rede(put: () => Promise<Response> = async () => new Response(null, { status: 200 })) {
  const fetch = vi.fn(async (caminho: string, opcoes: RequestInit = {}) => {
    if (caminho === '/api/arquivos') return json(201, AUTORIZADO)
    if (caminho === '/api/arquivos/42/confirmar') return json(200, ENVIADO)
    if (caminho === AUTORIZADO.url && opcoes.method === 'PUT') return put()
    return json(404, { codigo: 'nao_encontrado', mensagem: 'Não achamos.' })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function chamadas(fetch: ReturnType<typeof rede>) {
  return fetch.mock.calls.map(([caminho, opcoes]) => ({
    caminho,
    opcoes: (opcoes ?? {}) as RequestInit,
  }))
}

const SEM_IMAGEM = ferramentas(0, 0, null)

describe('funções de API do envio', () => {
  it('pedir é POST /api/arquivos com o corpo do contrato; confirmar é POST sem corpo', async () => {
    const fetch = rede()
    const dados = { nome: 'a.pdf', tipo: 'application/pdf', finalidade: 'aviso', tamanho_bytes: 3 } as const
    await expect(pedirEnvio(dados)).resolves.toEqual(AUTORIZADO)
    await expect(confirmarEnvio(42)).resolves.toEqual(ENVIADO)
    const [pedido, confirmacao] = chamadas(fetch)
    expect(pedido.opcoes.method).toBe('POST')
    expect(JSON.parse(String(pedido.opcoes.body))).toEqual(dados)
    expect(pedido.opcoes.headers).toMatchObject({ 'X-Portal': '1' })
    expect([confirmacao.caminho, confirmacao.opcoes.method, confirmacao.opcoes.body]).toEqual([
      '/api/arquivos/42/confirmar',
      'POST',
      undefined,
    ])
  })
})

describe('enviarArquivo', () => {
  it('pede, faz o PUT sem X-Portal e sem cookie com o Content-Type devolvido, e confirma', async () => {
    const fetch = rede()
    const pdf = arquivo('ata.pdf', 'application/pdf')
    await expect(enviarArquivo(pdf, 'documento', SEM_IMAGEM)).resolves.toEqual(ENVIADO)

    const [pedido, put, confirmacao] = chamadas(fetch)
    expect(JSON.parse(String(pedido.opcoes.body))).toEqual({
      nome: 'ata.pdf',
      tipo: 'application/pdf',
      finalidade: 'documento',
      tamanho_bytes: 1000,
    })
    expect(put.caminho).toBe(AUTORIZADO.url)
    expect(put.opcoes.method).toBe('PUT')
    expect(put.opcoes.credentials).toBe('omit')
    expect(put.opcoes.headers).toEqual({ 'Content-Type': 'application/pdf' })
    expect(put.opcoes.body).toBe(pdf)
    expect(confirmacao.caminho).toBe('/api/arquivos/42/confirmar')
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it('o Content-Type do PUT é o que a API devolveu, mesmo diferente do arquivo', async () => {
    const fetch = rede()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (caminho: string, opcoes?: RequestInit) =>
        caminho === '/api/arquivos'
          ? json(201, { ...AUTORIZADO, content_type: 'image/jpeg' })
          : fetch(caminho, opcoes),
      ),
    )
    await enviarArquivo(arquivo('foto.jpg', 'image/jpeg'), 'aviso', ferramentas(800, 600, null))
    const put = chamadas(fetch).find((c) => c.opcoes.method === 'PUT')
    expect(put?.opcoes.headers).toEqual({ 'Content-Type': 'image/jpeg' })
  })

  it('foto grande: comprime antes de pedir, e o tamanho declarado é o comprimido', async () => {
    const fetch = rede()
    const foto = arquivo('foto.jpg', 'image/jpeg', 30 * MB)
    const menor = new Blob([new Uint8Array(2000)], { type: 'image/webp' })
    await enviarArquivo(foto, 'aviso', ferramentas(4000, 3000, menor))
    const [pedido, put] = chamadas(fetch)
    expect(JSON.parse(String(pedido.opcoes.body))).toMatchObject({
      nome: 'foto.webp',
      tipo: 'image/webp',
      tamanho_bytes: 2000,
    })
    expect((put.opcoes.body as File).size).toBe(2000)
  })

  it('print pequeno e pesado: regravado para caber no limite do destino', async () => {
    const fetch = rede()
    const foto = arquivo('print.png', 'image/png', 12 * MB)
    const menor = new Blob([new Uint8Array(3000)], { type: 'image/webp' })
    await enviarArquivo(foto, 'aviso', ferramentas(1900, 1000, menor))
    const [pedido] = chamadas(fetch)
    expect(JSON.parse(String(pedido.opcoes.body))).toMatchObject({
      nome: 'print.webp',
      tamanho_bytes: 3000,
    })
  })

  it('tipo fora da lista: recusa na tela, sem chamar a API', async () => {
    const fetch = rede()
    const erro = await enviarArquivo(arquivo('a.exe', 'application/x-msdownload'), 'aviso', SEM_IMAGEM).catch(
      (e: unknown) => e,
    )
    expect(erro).toBeInstanceOf(ErroDaApi)
    expect((erro as ErroDaApi).mensagem).toBe(MSG_TIPO)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('grande demais mesmo depois de comprimir: recusa na tela, sem chamar a API', async () => {
    const fetch = rede()
    const pdf = { ...arquivo('a.pdf', 'application/pdf'), name: 'a.pdf', type: 'application/pdf' }
    Object.defineProperty(pdf, 'size', { value: 10 * MB + 1 })
    const erro = (await enviarArquivo(pdf as File, 'aviso', SEM_IMAGEM).catch((e: unknown) => e)) as ErroDaApi
    expect([erro.codigo, erro.mensagem]).toEqual(['dados_invalidos', 'O arquivo pode ter até 10 MB.'])
    expect(fetch).not.toHaveBeenCalled()
  })

  it('o bucket recusou o PUT: arquivo_nao_chegou, sem confirmar', async () => {
    const fetch = rede(async () => new Response('<Error>SignatureDoesNotMatch</Error>', { status: 403 }))
    const erro = (await enviarArquivo(arquivo('a.pdf', 'application/pdf'), 'aviso', SEM_IMAGEM).catch(
      (e: unknown) => e,
    )) as ErroDaApi
    expect(erro).toBeInstanceOf(ErroDaApi)
    expect([erro.codigo, erro.mensagem]).toEqual(['arquivo_nao_chegou', MENSAGEM_NAO_CHEGOU])
    expect(chamadas(fetch).map((c) => c.caminho)).not.toContain('/api/arquivos/42/confirmar')
  })

  it('a internet caiu no PUT: arquivo_nao_chegou', async () => {
    rede(async () => {
      throw new TypeError('Failed to fetch')
    })
    const erro = (await enviarArquivo(arquivo('a.pdf', 'application/pdf'), 'aviso', SEM_IMAGEM).catch(
      (e: unknown) => e,
    )) as ErroDaApi
    expect(erro.codigo).toBe('arquivo_nao_chegou')
    expect(MENSAGEM_NAO_CHEGOU).toBe('O arquivo não chegou ao Portal. Confira a internet e envie de novo.')
  })

  it('o PUT tem tempo limite, proporcional ao tamanho, de 2 a 10 minutos', async () => {
    expect(prazoDoEnvio(1000)).toBe(2 * 60_000 + 20)
    expect(prazoDoEnvio(20 * MB)).toBe(2 * 60_000 + Math.ceil((20 * MB) / 50))
    expect(prazoDoEnvio(200 * MB)).toBe(10 * 60_000)
    const timeout = vi.spyOn(AbortSignal, 'timeout')
    const fetch = rede()
    await enviarArquivo(arquivo('a.pdf', 'application/pdf'), 'aviso', SEM_IMAGEM)
    const put = chamadas(fetch).find((c) => c.opcoes.method === 'PUT')
    expect(put?.opcoes.signal).toBeInstanceOf(AbortSignal)
    expect(timeout).toHaveBeenCalledWith(prazoDoEnvio(1000))
    timeout.mockRestore()
  })

  it('o PUT passou do tempo: arquivo_nao_chegou, sem confirmar', async () => {
    const fetch = rede(async () => {
      throw new DOMException('signal timed out', 'TimeoutError')
    })
    const erro = (await enviarArquivo(arquivo('a.pdf', 'application/pdf'), 'aviso', SEM_IMAGEM).catch(
      (e: unknown) => e,
    )) as ErroDaApi
    expect([erro.codigo, erro.mensagem]).toEqual(['arquivo_nao_chegou', MENSAGEM_NAO_CHEGOU])
    expect(chamadas(fetch).map((c) => c.caminho)).not.toContain('/api/arquivos/42/confirmar')
  })

  it('erro da API (no pedido ou na confirmação) chega como veio', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        json(409, { codigo: 'muitos_arquivos', mensagem: 'Muitos arquivos enviados hoje. Tente de novo amanhã.' }),
      ),
    )
    const erro = (await enviarArquivo(arquivo('a.pdf', 'application/pdf'), 'aviso', SEM_IMAGEM).catch(
      (e: unknown) => e,
    )) as ErroDaApi
    expect([erro.status, erro.codigo]).toEqual([409, 'muitos_arquivos'])
  })
})
