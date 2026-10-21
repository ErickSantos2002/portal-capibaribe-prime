// Classificados · anunciar e editar (spec, seção 3.3): vender, trocar, doar ou procurar (sem padrão), a
// categoria, o título, a descrição, o preço (só na venda; vazio = a combinar), até 4 fotos e o
// WhatsApp ou telefone, que começa com o celular da unidade e aparece para os vizinhos logados.
// Sair com coisa escrita pergunta "Sair sem publicar?".
import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router'
import { buscarMinhaUnidade } from '../acesso/api'
import { comoErroDaApi, useCarga } from '../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../avisos/componentes'
import { formatarCelular } from '../casca/formatar'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { useAvisarAoSair } from '../enquetes/gestao/useAvisarAoSair'
import { ErroGeral } from '../indicacoes/FormOpiniao'
import { digitosDoTelefone, MSG_CONFIRA } from '../indicacoes/formulario'
import { PerguntaSairSemPublicar } from '../indicacoes/SairSemPublicar'
import { abrirAnuncio, anunciar, editarAnuncio, listarCategorias, meusAnuncios } from './api'
import { CAMINHO_CLASSIFICADOS, caminhoAnuncio } from './caminhos'
import { EscolherFotos, type FotoNoFormulario } from './EscolherFotos'
import { centavosDoTexto, precoNoCampo } from './formatos'
import type { Anuncio, NovoAnuncio, TipoAnuncio } from './tipos'
import '../indicacoes/indicacoes.css'
import './classificados.css'

const LIMITE_TITULO = 80
const MIN_TITULO = 3
const LIMITE_DESCRICAO = 1000
const PRECO_MAXIMO = 10_000_000
const TIPOS: { valor: TipoAnuncio; texto: string }[] = [
  { valor: 'venda', texto: 'Vender' },
  { valor: 'troca', texto: 'Trocar' },
  { valor: 'doacao', texto: 'Doar' },
  { valor: 'procura', texto: 'Procurar' },
]

interface Dados {
  tipo: TipoAnuncio | null
  categoria: string
  titulo: string
  descricao: string
  preco: string
  contato: string
}

type Campo = keyof Dados | 'fotos'
type Erros = Partial<Record<Campo, string>>

const VAZIO: Dados = { tipo: null, categoria: '', titulo: '', descricao: '', preco: '', contato: '' }

function conferir(dados: Dados, fotos: FotoNoFormulario[]): Erros {
  const erros: Erros = {}
  if (!dados.tipo) erros.tipo = 'Escolha se você quer vender, trocar, doar ou procurar.'
  if (!dados.categoria) erros.categoria = 'Escolha a categoria.'
  const titulo = dados.titulo.trim()
  if (!titulo) erros.titulo = 'Escreva o que você está anunciando.'
  else if (titulo.length < MIN_TITULO) erros.titulo = `Escreva pelo menos ${MIN_TITULO} letras.`
  if (dados.tipo === 'venda') {
    const preco = centavosDoTexto(dados.preco)
    if (preco !== null && (Number.isNaN(preco) || preco > PRECO_MAXIMO)) {
      erros.preco = 'Escreva o preço em reais, até R$ 100.000, por exemplo 350 ou 1.250,50.'
    }
  }
  if (!dados.contato.trim()) erros.contato = 'Escreva o WhatsApp ou o telefone, com DDD.'
  else if (digitosDoTelefone(dados.contato) === null) {
    erros.contato = 'Escreva o WhatsApp ou o telefone com DDD, por exemplo (81) 9 9999-0001.'
  }
  if (fotos.some((f) => f.situacao === 'enviando')) {
    erros.fotos = 'Espere as fotos terminarem de enviar.'
  } else if (fotos.some((f) => f.situacao === 'erro')) {
    erros.fotos = 'Uma foto não foi enviada. Tire essa foto ou escolha outra.'
  }
  return erros
}

function ErroDoCampo({ id, mensagem }: { id: string; mensagem?: string }) {
  if (!mensagem) return null
  return (
    <p className="ind-erro-campo" id={id}>
      {mensagem}
    </p>
  )
}

export function PaginaNovoAnuncio() {
  const [unidade] = useCarga(() => buscarMinhaUnidade(), [])
  if (unidade.situacao === 'carregando') {
    return (
      <Tela titulo="Anunciar" voltar={CAMINHO_CLASSIFICADOS}>
        <Carregando />
      </Tela>
    )
  }
  // Sem o celular (ou se Minha unidade falhar), o campo começa vazio.
  const celular = unidade.dados?.celular ?? ''
  return <Formulario inicial={{ ...VAZIO, contato: formatarCelular(celular) }} />
}

export function PaginaEditarAnuncio() {
  const { id } = useParams()
  const numero = id && /^\d{1,15}$/.test(id) ? Number(id) : null
  const [carga, recarregar] = useCarga(
    () => (numero === null ? Promise.reject(new Error('link quebrado')) : abrirAnuncio(numero)),
    [numero],
  )
  const anuncio = carga.dados
  if (!anuncio || !anuncio.meu) {
    return (
      <Tela titulo="Editar o anúncio" voltar={CAMINHO_CLASSIFICADOS}>
        {carga.situacao === 'erro' ? (
          <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
        ) : anuncio ? (
          <div className="aviso-caixa erro" role="alert">
            <Icone nome="alerta" />
            <p>Só o apartamento que anunciou pode mudar este anúncio.</p>
          </div>
        ) : (
          <Carregando />
        )}
      </Tela>
    )
  }
  return <Formulario anuncio={anuncio} inicial={dadosDoAnuncio(anuncio)} />
}

function dadosDoAnuncio(a: Anuncio): Dados {
  return {
    tipo: a.tipo,
    categoria: String(a.categoria.id),
    titulo: a.titulo,
    descricao: a.descricao ?? '',
    preco: precoNoCampo(a.preco_centavos),
    contato: formatarCelular(a.contato),
  }
}

interface PropsFormulario {
  inicial: Dados
  /** Editar: o anúncio que já existe. */
  anuncio?: Anuncio
}

function Formulario({ inicial, anuncio }: PropsFormulario) {
  const navegar = useNavigate()
  const [dados, setDados] = useState<Dados>(inicial)
  const [fotos, setFotos] = useState<FotoNoFormulario[]>(
    () =>
      anuncio?.fotos.map((f) => ({ chave: `ja-${f.id}`, id: f.id, url: f.url, situacao: 'pronta' as const })) ??
      [],
  )
  const [erros, setErros] = useState<Erros>({})
  const [geral, setGeral] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [categorias, recarregarCategorias] = useCarga(() => listarCategorias(), [])
  const [meus] = useCarga(
    () => (anuncio ? Promise.resolve(null) : meusAnuncios()),
    [anuncio?.id ?? 0],
  )
  const limite = meus.dados?.limite ?? null

  const fotosMudaram =
    JSON.stringify(fotos.map((f) => f.chave)) !==
    JSON.stringify(anuncio?.fotos.map((f) => `ja-${f.id}`) ?? [])
  const sujo = JSON.stringify(dados) !== JSON.stringify(inicial) || fotosMudaram
  const { blocker, liberar } = useAvisarAoSair(sujo)

  function limparErro(campo: Campo) {
    if (!erros[campo]) return
    const resto = { ...erros, [campo]: undefined }
    setErros(resto)
    const doCampo = geral === MSG_CONFIRA || geral === erros[campo]
    if (doCampo && !Object.values(resto).some(Boolean)) setGeral('')
  }

  function mudar<K extends keyof Dados>(campo: K, valor: Dados[K]) {
    setDados((antes) => ({ ...antes, [campo]: valor }))
    limparErro(campo)
  }

  const descrito = (campo: Campo, ajuda?: string) =>
    [ajuda, erros[campo] && `cla-${campo}-erro`].filter(Boolean).join(' ') || undefined

  async function publicar(evento: FormEvent) {
    evento.preventDefault()
    const novos = conferir(dados, fotos)
    setErros(novos)
    const mensagens = Object.values(novos).filter(Boolean) as string[]
    setGeral(mensagens.length === 0 ? '' : mensagens.length === 1 ? mensagens[0] : MSG_CONFIRA)
    if (mensagens.length > 0 || !dados.tipo) return
    const corpo: NovoAnuncio = {
      tipo: dados.tipo,
      categoria_id: Number(dados.categoria),
      titulo: dados.titulo,
      descricao: dados.descricao.trim() ? dados.descricao : null,
      preco_centavos: dados.tipo === 'venda' ? centavosDoTexto(dados.preco) : null,
      contato: dados.contato,
      fotos: fotos.map((f) => f.id).filter((id): id is number => id !== undefined),
    }
    setOcupado(true)
    try {
      const id = anuncio ? (await editarAnuncio(anuncio.id, corpo)).id : (await anunciar(corpo)).id
      liberar()
      navegar(caminhoAnuncio(id), {
        replace: true,
        state: { recado: anuncio ? 'As mudanças foram salvas.' : 'Anúncio publicado. Boa sorte!' },
      })
    } catch (e) {
      const erro = comoErroDaApi(e)
      const daApi: Erros = {
        tipo: erro.doCampo('tipo'),
        categoria: erro.doCampo('categoria_id'),
        titulo: erro.doCampo('titulo'),
        descricao: erro.doCampo('descricao'),
        preco: erro.doCampo('preco_centavos'),
        contato: erro.doCampo('contato'),
        fotos: erro.doCampo('fotos'),
      }
      setErros(daApi)
      const deCampo = Object.values(daApi).filter(Boolean) as string[]
      setGeral(deCampo.length === 1 ? deCampo[0] : deCampo.length > 1 ? MSG_CONFIRA : erro.mensagem)
    } finally {
      setOcupado(false)
    }
  }

  const titulo = anuncio ? 'Editar o anúncio' : 'Anunciar'
  return (
    <Tela titulo={titulo} voltar={anuncio ? caminhoAnuncio(anuncio.id) : CAMINHO_CLASSIFICADOS}>
      <PerguntaSairSemPublicar
        blocker={blocker}
        texto={
          anuncio
            ? 'As mudanças que você fez no anúncio vão se perder.'
            : 'O que você escreveu e as fotos que escolheu vão se perder.'
        }
      />
      <form className="ind-nova cla-form" onSubmit={publicar} noValidate>
        {!anuncio && (
          <p className="ajuda">
            Anuncie o que sobrou da obra, o móvel que não coube ou o que vai trocar. O anúncio fica
            na lista por 30 dias, com o bloco e o apartamento, nunca com o seu nome.
          </p>
        )}
        {/* Já no limite (5 por dia, 10 abertos): avisa logo, não só no Publicar (revisão UX 11). */}
        {limite && (
          <div className="aviso-caixa atencao" role="status">
            <Icone nome="alerta" />
            <p>{limite}</p>
          </div>
        )}
        {geral && <ErroGeral mensagem={geral} />}

        <fieldset
          className="ind-recomenda"
          aria-invalid={erros.tipo ? true : undefined}
          aria-describedby={erros.tipo ? 'cla-tipo-erro' : undefined}
        >
          <legend>O que você quer fazer?</legend>
          {TIPOS.map((t) => (
            <label key={t.valor} className={dados.tipo === t.valor ? 'ind-voto marcado' : 'ind-voto'}>
              <input
                type="radio"
                name="cla-tipo"
                checked={dados.tipo === t.valor}
                onChange={() => mudar('tipo', t.valor)}
              />
              <span className="ind-voto-texto">{t.texto}</span>
            </label>
          ))}
        </fieldset>
        <ErroDoCampo id="cla-tipo-erro" mensagem={erros.tipo} />

        <label htmlFor="cla-categoria">Categoria</label>
        {categorias.situacao === 'erro' && !categorias.dados ? (
          <div className="aviso-caixa erro" role="alert">
            <Icone nome="alerta" />
            <div>
              <p>{categorias.erro.mensagem}</p>
              <button type="button" className="texto-link" onClick={recarregarCategorias}>
                Tentar de novo
              </button>
            </div>
          </div>
        ) : (
          <select
            id="cla-categoria"
            value={dados.categoria}
            onChange={(e) => mudar('categoria', e.target.value)}
            className={erros.categoria ? 'campo-erro' : undefined}
            aria-invalid={erros.categoria ? true : undefined}
            aria-describedby={descrito('categoria')}
          >
            <option value="">Escolha</option>
            {categorias.dados?.itens.map((c) => (
              <option key={c.id} value={String(c.id)}>
                {c.nome}
              </option>
            ))}
          </select>
        )}
        <ErroDoCampo id="cla-categoria-erro" mensagem={erros.categoria} />

        <label htmlFor="cla-titulo">Título</label>
        <input
          id="cla-titulo"
          type="text"
          value={dados.titulo}
          onChange={(e) => mudar('titulo', e.target.value)}
          maxLength={LIMITE_TITULO}
          autoComplete="off"
          placeholder="Ex.: Berço usado"
          className={erros.titulo ? 'campo-erro' : undefined}
          aria-invalid={erros.titulo ? true : undefined}
          aria-describedby={descrito('titulo')}
        />
        <ErroDoCampo id="cla-titulo-erro" mensagem={erros.titulo} />

        <label htmlFor="cla-descricao">Descrição (opcional)</label>
        <textarea
          id="cla-descricao"
          rows={4}
          value={dados.descricao}
          onChange={(e) => mudar('descricao', e.target.value)}
          maxLength={LIMITE_DESCRICAO}
          className={erros.descricao ? 'campo-erro' : undefined}
          aria-invalid={erros.descricao ? true : undefined}
          aria-describedby={descrito('descricao', 'cla-descricao-contador')}
        />
        <p className="ajuda" id="cla-descricao-contador">
          {dados.descricao.length} de {LIMITE_DESCRICAO} letras
        </p>
        <ErroDoCampo id="cla-descricao-erro" mensagem={erros.descricao} />

        {dados.tipo === 'venda' && (
          <>
            <label htmlFor="cla-preco">Preço (opcional)</label>
            <div className="cla-preco">
              <span aria-hidden="true">R$</span>
              <input
                id="cla-preco"
                type="text"
                inputMode="decimal"
                value={dados.preco}
                onChange={(e) => mudar('preco', e.target.value)}
                maxLength={14}
                autoComplete="off"
                className={erros.preco ? 'campo-erro' : undefined}
                aria-invalid={erros.preco ? true : undefined}
                aria-describedby={descrito('preco', 'cla-preco-ajuda')}
              />
            </div>
            <p className="ajuda" id="cla-preco-ajuda">
              Em reais. Em branco, aparece “a combinar”.
            </p>
            <ErroDoCampo id="cla-preco-erro" mensagem={erros.preco} />
          </>
        )}

        <EscolherFotos
          fotos={fotos}
          mudar={(atualizar) => {
            setFotos(atualizar)
            limparErro('fotos')
          }}
          erro={erros.fotos}
        />

        <label htmlFor="cla-contato">WhatsApp ou telefone para contato</label>
        <input
          id="cla-contato"
          type="tel"
          inputMode="tel"
          value={dados.contato}
          onChange={(e) => mudar('contato', e.target.value)}
          maxLength={25}
          autoComplete="off"
          className={erros.contato ? 'campo-erro' : undefined}
          aria-invalid={erros.contato ? true : undefined}
          aria-describedby={descrito('contato', 'cla-contato-ajuda')}
        />
        <p className="ajuda" id="cla-contato-ajuda">
          Aparece para os vizinhos logados neste anúncio.
        </p>
        <ErroDoCampo id="cla-contato-erro" mensagem={erros.contato} />

        <div className="ind-acoes">
          <button type="submit" className="botao" disabled={ocupado}>
            {anuncio ? 'Salvar as mudanças' : 'Publicar anúncio'}
          </button>
        </div>
      </form>
    </Tela>
  )
}
