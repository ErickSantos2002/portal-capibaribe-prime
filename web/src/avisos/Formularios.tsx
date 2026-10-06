// H-12 · Publicar aviso (com prévia) e H-15 · Corrigir aviso. Os campos do aviso (título,
// categoria, texto formatado, evento) são de `CamposDoAviso.tsx`.
import { useEffect, useRef, useState, type FormEvent, type RefObject } from 'react'
import { useNavigate } from 'react-router'
import { useSessao } from '../casca/contextoSessao'
import { NaoEncontrado } from '../casca/guardas'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { abrirAviso, calcularAlcance, corrigirAviso, listarDestinos, publicarAviso } from './api'
import { CamposDoAviso } from './CamposDoAviso'
import { comoErroDaApi, useCarga, useIdDoAviso } from './carregar'
import { AvisoFixado, Carregando, CorpoDoAviso, FalhaAoCarregar, ItemAviso } from './componentes'
import { destinoEmTexto } from './formatos'
import { semMarcas } from './formatacao'
import {
  conferir,
  eventoDe,
  RASCUNHO_VAZIO,
  rascunhoDe,
  type Campo,
  type Erros,
  type Rascunho,
} from './rascunho'
import type { AvisoCompleto, AvisoResumo, CorrigirAviso } from './tipos'
import './avisos.css'

const CAMPOS: readonly Campo[] = ['titulo', 'texto', 'blocos', 'evento', 'categoria']

/** Erro da API: os campos marcados (422) e a mensagem geral. `evento.quando` marca o evento. */
function errosDaApi(e: unknown): { geral: string; campos: Erros } {
  const erro = comoErroDaApi(e)
  const campos: Erros = {}
  for (const c of erro.campos) {
    const campo = c.campo?.split('.')[0] as Campo | undefined
    if (campo && CAMPOS.includes(campo)) campos[campo] ??= c.mensagem
  }
  return { geral: erro.mensagem, campos }
}

/** O corpo que a API recebe, a partir do rascunho. */
function corpoDe(r: Rascunho): CorrigirAviso {
  return { titulo: r.titulo, texto: r.texto, categoria: r.categoria, evento: eventoDe(r) }
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

/** O resumo do mural como a API vai fazer: primeiro parágrafo, sem marcas, até 200 letras. */
function resumoDe(texto: string): string {
  const primeiro = texto.trim().split(/\n[ \t]*\n/)[0] ?? ''
  const linha = semMarcas(primeiro).replace(/\s+/g, ' ').trim()
  return linha.length <= 200 ? linha : linha.slice(0, 199).trimEnd() + '…'
}

// --- H-12 · Novo aviso ------------------------------------------------------------------------

export function NovoAviso() {
  const navegar = useNavigate()
  const { eu } = useSessao()
  const [destinos, recarregarDestinos] = useCarga(listarDestinos, [])
  const [rascunho, setRascunho] = useState<Rascunho>(RASCUNHO_VAZIO)
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
  function mudar(mudanca: Partial<Rascunho>) {
    setRascunho((atual) => ({ ...atual, ...mudanca }))
    setPrevia(false)
  }
  function escolherBloco(numero: number) {
    setBlocos((atuais) =>
      atuais.includes(numero)
        ? atuais.filter((b) => b !== numero)
        : [...atuais, numero].sort((a, b) => a - b),
    )
    setPrevia(false)
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    const encontrados = conferir(rascunho)
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
      await publicarAviso({ ...corpoDe(rascunho), para_todos: paraTodos, blocos, fixado })
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

  const eventoNaPrevia = eventoDe(rascunho)
  const comoVaiFicar: AvisoResumo = {
    id: 0,
    titulo: rascunho.titulo.trim(),
    resumo: resumoDe(rascunho.texto),
    publicado_em: new Date().toISOString(),
    publicado_por: eu?.papeis.includes('comissao') ? 'Comissão' : 'Administração do Portal',
    editado_em: null,
    fixado,
    para_todos: paraTodos,
    blocos,
    arquivado_em: null,
    lido: false,
    corrigido_desde_a_leitura: false,
    categoria: rascunho.categoria,
    evento_quando: eventoNaPrevia?.quando ?? null,
  }
  const unidades = alcance.situacao === 'pronta' ? alcance.dados.unidades : null

  return (
    <Tela titulo="Novo aviso" voltar="/avisos">
      <form onSubmit={enviar} noValidate>
        {geral && <ErroGeral mensagem={geral} alvo={caixaDeErro} />}
        <CamposDoAviso rascunho={rascunho} erros={erros} mudar={mudar} />
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
              onClick={() => {
                setBlocos([])
                setPrevia(false)
              }}
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
            onChange={(e) => {
              setFixado(e.target.checked)
              setPrevia(false)
            }}
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
              <ItemAviso aviso={comoVaiFicar} previa />
            )}
            <p className="secao">E assim, quando alguém abrir</p>
            <div className={`aviso-aberto cat-${comoVaiFicar.categoria}`}>
              <h2>{comoVaiFicar.titulo}</h2>
              <CorpoDoAviso
                aviso={comoVaiFicar}
                evento={eventoNaPrevia}
                texto={rascunho.texto}
                nivel={3}
              />
            </div>
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
  const [rascunho, setRascunho] = useState<Rascunho>(() => rascunhoDe(aviso))
  const [erros, setErros] = useState<Erros>({})
  const [geral, setGeral] = useState('')
  const [enviando, setEnviando] = useState(false)
  const caixaDeErro = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (geral) caixaDeErro.current?.focus()
  }, [geral])

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    const encontrados = conferir(rascunho)
    setErros(encontrados)
    if (Object.keys(encontrados).length > 0) {
      setGeral(Object.values(encontrados)[0] ?? '')
      return
    }
    setEnviando(true)
    setGeral('')
    try {
      await corrigirAviso(aviso.id, corpoDe(rascunho))
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
      <CamposDoAviso
        rascunho={rascunho}
        erros={erros}
        mudar={(mudanca) => setRascunho((atual) => ({ ...atual, ...mudanca }))}
      />
      <button className="botao avisos-enviar" type="submit" disabled={enviando}>
        {enviando ? 'Salvando…' : 'Salvar correção'}
      </button>
    </form>
  )
}
