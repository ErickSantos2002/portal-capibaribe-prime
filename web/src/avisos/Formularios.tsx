// H-12 · Publicar aviso (com prévia) e H-15 · Corrigir aviso.
import { useEffect, useRef, useState, type FormEvent, type RefObject } from 'react'
import { useNavigate } from 'react-router'
import { useSessao } from '../casca/contextoSessao'
import { NaoEncontrado } from '../casca/guardas'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { abrirAviso, calcularAlcance, corrigirAviso, listarDestinos, publicarAviso } from './api'
import { comoErroDaApi, useCarga, useIdDoAviso } from './carregar'
import { AvisoFixado, Carregando, FalhaAoCarregar, ItemAviso, TextoDoAviso } from './componentes'
import { destinoEmTexto } from './formatos'
import type { AvisoCompleto, AvisoResumo } from './tipos'
import './avisos.css'

const LIMITE_TITULO = 120
const LIMITE_TEXTO = 10_000

type Campo = 'titulo' | 'texto' | 'blocos'
type Erros = Partial<Record<Campo, string>>

/** As mesmas regras da API (`app/esquemas/avisos.py`), para avisar antes de enviar. */
function conferir(titulo: string, texto: string): Erros {
  const erros: Erros = {}
  if (!titulo.trim()) erros.titulo = 'Escreva o título do aviso.'
  else if (titulo.trim().length > LIMITE_TITULO) erros.titulo = 'O título pode ter até 120 letras.'
  if (!texto.trim()) erros.texto = 'Escreva o texto do aviso.'
  else if (texto.trim().length > LIMITE_TEXTO) erros.texto = 'O texto pode ter até 10.000 letras.'
  return erros
}

/** Erro da API: os campos marcados (422) e a mensagem geral. */
function errosDaApi(e: unknown): { geral: string; campos: Erros } {
  const erro = comoErroDaApi(e)
  const campos: Erros = {}
  for (const c of erro.campos) {
    if (c.campo === 'titulo' || c.campo === 'texto' || c.campo === 'blocos') {
      campos[c.campo] ??= c.mensagem
    }
  }
  return { geral: erro.mensagem, campos }
}

function ErroGeral({
  mensagem,
  alvo,
}: {
  mensagem: string
  alvo: RefObject<HTMLDivElement | null>
}) {
  return (
    <div className="aviso-caixa erro" role="alert" tabIndex={-1} ref={alvo}>
      <Icone nome="alerta" />
      <p>{mensagem}</p>
    </div>
  )
}

interface PropsCampos {
  titulo: string
  texto: string
  erros: Erros
  mudarTitulo: (v: string) => void
  mudarTexto: (v: string) => void
}

function CamposDoTexto({ titulo, texto, erros, mudarTitulo, mudarTexto }: PropsCampos) {
  return (
    <>
      <label htmlFor="aviso-titulo">Título</label>
      <input
        id="aviso-titulo"
        type="text"
        value={titulo}
        onChange={(e) => mudarTitulo(e.target.value)}
        maxLength={LIMITE_TITULO}
        aria-invalid={!!erros.titulo}
        aria-describedby={erros.titulo ? 'aviso-titulo-erro' : undefined}
        className={erros.titulo ? 'campo-erro' : undefined}
      />
      {erros.titulo && (
        <p className="avisos-erro-campo" id="aviso-titulo-erro">
          {erros.titulo}
        </p>
      )}
      <label htmlFor="aviso-texto">Texto do aviso</label>
      <textarea
        id="aviso-texto"
        value={texto}
        onChange={(e) => mudarTexto(e.target.value)}
        maxLength={LIMITE_TEXTO}
        aria-invalid={!!erros.texto}
        aria-describedby={`aviso-texto-ajuda${erros.texto ? ' aviso-texto-erro' : ''}`}
        className={erros.texto ? 'campo-erro' : undefined}
      />
      <p className="ajuda" id="aviso-texto-ajuda">
        Deixe uma linha em branco para começar outro parágrafo. Endereços que começam com https://
        viram link.
      </p>
      {erros.texto && (
        <p className="avisos-erro-campo" id="aviso-texto-erro">
          {erros.texto}
        </p>
      )}
    </>
  )
}

// --- H-12 · Novo aviso ------------------------------------------------------------------------

export function NovoAviso() {
  const navegar = useNavigate()
  const { eu } = useSessao()
  const [destinos, recarregarDestinos] = useCarga(listarDestinos, [])
  const [titulo, setTitulo] = useState('')
  const [texto, setTexto] = useState('')
  const [blocos, setBlocos] = useState<number[]>([])
  const [fixado, setFixado] = useState(false)
  const [erros, setErros] = useState<Erros>({})
  const [geral, setGeral] = useState('')
  const [previa, setPrevia] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const caixaDeErro = useRef<HTMLDivElement>(null)
  const caixaDaPrevia = useRef<HTMLDivElement>(null)
  const paraTodos = blocos.length === 0
  const [alcance] = useCarga(() => calcularAlcance(blocos), [blocos.join(',')])

  useEffect(() => {
    if (geral) caixaDeErro.current?.focus()
  }, [geral])
  useEffect(() => {
    if (previa) caixaDaPrevia.current?.focus()
  }, [previa])

  // Mexeu em qualquer coisa, a prévia some e o botão volta a "Ver prévia" (protótipo).
  function mudou<T>(trocar: (v: T) => void) {
    return (v: T) => {
      trocar(v)
      setPrevia(false)
    }
  }
  const escolherBloco = mudou((numero: number) =>
    setBlocos((atuais) =>
      atuais.includes(numero)
        ? atuais.filter((b) => b !== numero)
        : [...atuais, numero].sort((a, b) => a - b),
    ),
  )

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    const encontrados = conferir(titulo, texto)
    setErros(encontrados)
    if (Object.keys(encontrados).length > 0) {
      setGeral(Object.values(encontrados)[0] ?? '')
      return
    }
    setGeral('')
    if (!previa) {
      setPrevia(true)
      return
    }
    setEnviando(true)
    try {
      await publicarAviso({ titulo, texto, para_todos: paraTodos, blocos, fixado })
      navegar('/avisos', { state: { recado: 'Aviso publicado.' } })
    } catch (e) {
      const { geral: mensagem, campos } = errosDaApi(e)
      setErros(campos)
      setGeral(mensagem)
      setPrevia(false)
      if (campos.blocos) recarregarDestinos()
      setEnviando(false)
    }
  }

  const comoVaiFicar: AvisoResumo = {
    id: 0,
    titulo: titulo.trim(),
    resumo:
      texto
        .trim()
        .split(/\n[ \t]*\n/)[0]
        ?.replace(/\s+/g, ' ')
        .slice(0, 200) ?? '',
    publicado_em: new Date().toISOString(),
    publicado_por: eu?.papeis.includes('comissao') ? 'Comissão' : 'Administração do Portal',
    editado_em: null,
    fixado,
    para_todos: paraTodos,
    blocos,
    arquivado_em: null,
    lido: false,
  }
  const unidades = alcance.situacao === 'pronta' ? alcance.dados.unidades : null

  return (
    <Tela titulo="Novo aviso" voltar="/avisos">
      <form onSubmit={enviar} noValidate>
        {geral && <ErroGeral mensagem={geral} alvo={caixaDeErro} />}
        <CamposDoTexto
          titulo={titulo}
          texto={texto}
          erros={erros}
          mudarTitulo={mudou(setTitulo)}
          mudarTexto={mudou(setTexto)}
        />
        <p className="avisos-rotulo" id="aviso-destino">
          Para quem
        </p>
        {destinos.situacao === 'erro' ? (
          <FalhaAoCarregar mensagem={destinos.erro.mensagem} tentar={recarregarDestinos} />
        ) : (
          <div
            className="chips"
            role="group"
            aria-labelledby="aviso-destino"
            aria-describedby={erros.blocos ? 'aviso-blocos-erro' : undefined}
          >
            <button
              type="button"
              className="chip"
              aria-pressed={paraTodos}
              onClick={mudou(() => setBlocos([]))}
            >
              Todos os blocos
            </button>
            {destinos.dados?.blocos.map((b) => (
              <button
                key={b.numero}
                type="button"
                className="chip"
                aria-pressed={blocos.includes(b.numero)}
                onClick={() => escolherBloco(b.numero)}
              >
                {b.nome}
              </button>
            ))}
          </div>
        )}
        {erros.blocos && (
          <p className="avisos-erro-campo" id="aviso-blocos-erro">
            {erros.blocos}
          </p>
        )}
        <label className="opcao avisos-fixar">
          <input
            type="checkbox"
            checked={fixado}
            onChange={(e) => mudou(setFixado)(e.target.checked)}
          />
          Fixar no topo do mural
        </label>
        <div className="aviso-caixa info" aria-live="polite">
          <Icone nome="info" />
          <p>
            {unidades === null ? (
              'Contando os apartamentos…'
            ) : (
              <>
                Vai aparecer no mural de <b>{unidades}</b> apartamentos (
                {destinoEmTexto(comoVaiFicar)}).
              </>
            )}
          </p>
        </div>
        {previa && (
          <div className="previa" tabIndex={-1} ref={caixaDaPrevia} aria-labelledby="previa-titulo">
            <p className="secao avisos-previa-titulo" id="previa-titulo">
              Prévia: assim vai aparecer no mural
            </p>
            {fixado ? (
              <AvisoFixado aviso={comoVaiFicar} previa />
            ) : (
              <div className="folha">
                <ItemAviso aviso={comoVaiFicar} previa />
              </div>
            )}
            <p className="secao">E assim, quando alguém abrir</p>
            <h2>{comoVaiFicar.titulo}</h2>
            <TextoDoAviso texto={texto} />
          </div>
        )}
        <button className="botao avisos-enviar" type="submit" disabled={enviando}>
          {enviando ? 'Publicando…' : previa ? 'Publicar aviso' : 'Ver prévia'}
        </button>
      </form>
    </Tela>
  )
}

// --- H-15 · Corrigir aviso --------------------------------------------------------------------

export function PaginaCorrigir() {
  const id = useIdDoAviso()
  return id === null ? <NaoEncontrado /> : <Corrigir key={id} id={id} />
}

function Corrigir({ id }: { id: number }) {
  const [carga, recarregar] = useCarga(() => abrirAviso(id), [id])
  if (carga.situacao === 'erro' && carga.erro.status === 404) return <NaoEncontrado />
  return (
    <Tela titulo="Corrigir aviso" voltar={`/avisos/${id}`}>
      {carga.situacao === 'erro' ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : carga.situacao === 'carregando' ? (
        <Carregando />
      ) : carga.dados.arquivado_em ? (
        <div className="aviso-caixa atencao" role="alert">
          <Icone nome="arquivar" />
          <p>Aviso arquivado não pode ser corrigido.</p>
        </div>
      ) : (
        <FormularioCorrigir aviso={carga.dados} />
      )}
    </Tela>
  )
}

function FormularioCorrigir({ aviso }: { aviso: AvisoCompleto }) {
  const navegar = useNavigate()
  const [titulo, setTitulo] = useState(aviso.titulo)
  const [texto, setTexto] = useState(aviso.texto)
  const [erros, setErros] = useState<Erros>({})
  const [geral, setGeral] = useState('')
  const [enviando, setEnviando] = useState(false)
  const caixaDeErro = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (geral) caixaDeErro.current?.focus()
  }, [geral])

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    const encontrados = conferir(titulo, texto)
    setErros(encontrados)
    if (Object.keys(encontrados).length > 0) {
      setGeral(Object.values(encontrados)[0] ?? '')
      return
    }
    setEnviando(true)
    setGeral('')
    try {
      await corrigirAviso(aviso.id, { titulo, texto })
      navegar(`/avisos/${aviso.id}`, { replace: true, state: { recado: 'Aviso corrigido.' } })
    } catch (e) {
      const { geral: mensagem, campos } = errosDaApi(e)
      setErros(campos)
      setGeral(mensagem)
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={enviar} noValidate>
      <div className="aviso-caixa info">
        <Icone nome="editar" />
        <p>
          A versão de antes fica guardada. Todos vão ver “Corrigido em” e poderão abrir como era
          antes.
        </p>
      </div>
      {geral && <ErroGeral mensagem={geral} alvo={caixaDeErro} />}
      <CamposDoTexto
        titulo={titulo}
        texto={texto}
        erros={erros}
        mudarTitulo={setTitulo}
        mudarTexto={setTexto}
      />
      <button className="botao avisos-enviar" type="submit" disabled={enviando}>
        {enviando ? 'Salvando…' : 'Salvar correção'}
      </button>
    </form>
  )
}
