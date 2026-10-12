// H-12 · Publicar aviso (com prévia) e H-15 · Corrigir aviso. Os campos do aviso (título,
// categoria, texto formatado, evento) são de `CamposDoAviso.tsx`.
import { useEffect, useRef, useState, type FormEvent, type RefObject } from 'react'
import { useNavigate } from 'react-router'
import { useSessao } from '../casca/contextoSessao'
import { NaoEncontrado } from '../casca/guardas'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { AnexosDoAviso } from './AnexosDoAviso'
import { idsProntos, progressoDoEnvio, situacaoDosAnexos, type ItemAnexo } from './anexos'
import { abrirAviso, calcularAlcance, corrigirAviso, listarDestinos, publicarAviso } from './api'
import { CamposDoAviso } from './CamposDoAviso'
import { EscolherAnexos } from './EscolherAnexos'
import { comoErroDaApi, useCarga, useIdDoAviso } from './carregar'
import { AvisoFixado, Carregando, CorpoDoAviso, FalhaAoCarregar, ItemAviso } from './componentes'
import { destinoEmTexto } from './formatos'
import { semMarcas } from './formatacao'
import {
  conferir,
  eventoDe,
  mensagemGeral,
  RASCUNHO_VAZIO,
  rascunhoDe,
  semErrosDe,
  type Campo,
  type Erros,
  type Rascunho,
} from './rascunho'
import type { AvisoCompleto, AvisoResumo, CorrigirAviso } from './tipos'
import { PerguntaSairSemPublicar } from './SairSemPublicar'
import { useAnexos } from './useAnexos'
import { useAvisarAoSair } from './useAvisarAoSair'
import './avisos.css'

const CAMPOS: readonly Campo[] = ['titulo', 'texto', 'blocos', 'evento', 'categoria']

/** Erro da API: os campos marcados (422) e a mensagem geral. `evento.quando` marca o evento;
 *  `anexos` (M3) vai para baixo do campo dos anexos. */
function errosDaApi(e: unknown): { geral: string; campos: Erros; anexos: string } {
  const erro = comoErroDaApi(e)
  const campos: Erros = {}
  for (const c of erro.campos) {
    const campo = c.campo?.split('.')[0] as Campo | undefined
    if (campo && CAMPOS.includes(campo)) campos[campo] ??= c.mensagem
  }
  return { geral: erro.mensagem, campos, anexos: erro.doCampo('anexos') ?? '' }
}

/** A conferência antes de enviar: os campos do texto e os anexos (enviando ou com erro). */
function conferirTudo(r: Rascunho, itens: readonly ItemAnexo[]) {
  const erros = conferir(r)
  const anexos = situacaoDosAnexos(itens)
  const geral = [mensagemGeral(erros), anexos.mensagem].filter(Boolean).join(' ')
  return { erros, anexos: anexos.mensagem, geral }
}

/** O rascunho mudou em relação ao de partida (U1: há o que perder ao sair). */
function mudou(r: Rascunho, inicial: Rascunho): boolean {
  return (Object.keys(inicial) as (keyof Rascunho)[]).some((k) => r[k] !== inicial[k])
}

/** U3: o texto do botão de enviar enquanto os arquivos sobem (o botão fica desabilitado). */
function esperandoOsArquivos(itens: readonly ItemAnexo[]): string | null {
  const progresso = progressoDoEnvio(itens)
  return progresso && `Esperando os arquivos… (${progresso.feitos} de ${progresso.total})`
}

/** Os anexos prontos, como a prévia e o aviso aberto mostram. */
function paraMostrar(itens: readonly ItemAnexo[]) {
  return itens.flatMap((i) =>
    i.situacao === 'pronto' && i.arquivo ? [{ arquivo: i.arquivo, previa: i.previa }] : [],
  )
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
  const anexos = useAnexos()
  const [erroAnexos, setErroAnexos] = useState('')
  const caixaDeErro = useRef<HTMLDivElement>(null)
  const caixaDaPrevia = useRef<HTMLDivElement>(null)
  const paraTodos = blocos.length === 0
  const [alcance] = useCarga(() => calcularAlcance(blocos), [blocos.join(',')])
  const esperando = esperandoOsArquivos(anexos.itens)
  const { blocker, liberar } = useAvisarAoSair(
    mudou(rascunho, RASCUNHO_VAZIO) || anexos.itens.length > 0 || blocos.length > 0 || fixado,
  )

  useEffect(() => {
    if (geral) caixaDeErro.current?.focus()
  }, [geral])
  useEffect(() => {
    if (previa) caixaDaPrevia.current?.focus()
  }, [previa])

  // Mexeu em qualquer coisa, a prévia some e o botão volta a "Ver prévia" (protótipo).
  function mudar(mudanca: Partial<Rascunho>) {
    setRascunho((atual) => ({ ...atual, ...mudanca }))
    setErros((atuais) => semErrosDe(atuais, mudanca))
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
    // U2/U3: enquanto os arquivos sobem, o botão espera (nenhuma mensagem fica para trás).
    if (esperando) return
    const conferido = conferirTudo(rascunho, anexos.itens)
    setErros(conferido.erros)
    setErroAnexos(conferido.anexos)
    if (conferido.geral) {
      setGeral(conferido.geral)
      setPrevia(false)
      return
    }
    setGeral('')
    if (!previa) {
      setPrevia(true)
      return
    }
    setEnviando(true)
    try {
      await publicarAviso({
        ...corpoDe(rascunho),
        para_todos: paraTodos,
        blocos,
        fixado,
        anexos: idsProntos(anexos.itens),
      })
      liberar()
      navegar('/avisos', { state: { recado: 'Aviso publicado.' } })
    } catch (e) {
      const { geral: mensagem, campos, anexos: doCampo } = errosDaApi(e)
      setErros(campos)
      setErroAnexos(doCampo)
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
    quantidade_anexos: idsProntos(anexos.itens).length,
  }
  const unidades = alcance.situacao === 'pronta' ? alcance.dados.unidades : null

  return (
    <Tela titulo="Novo aviso" voltar="/avisos">
      <form onSubmit={enviar} noValidate>
        {geral && <ErroGeral mensagem={geral} alvo={caixaDeErro} />}
        <CamposDoAviso rascunho={rascunho} erros={erros} mudar={mudar} />
        <EscolherAnexos
          anexos={anexos}
          erro={erroAnexos}
          aoMudar={() => {
            setErroAnexos('')
            setPrevia(false)
          }}
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
              <AnexosDoAviso anexos={paraMostrar(anexos.itens)} />
            </div>
          </div>
        )}
        <button className="botao avisos-enviar" type="submit" disabled={enviando || !!esperando}>
          {esperando ?? (enviando ? 'Publicando…' : previa ? 'Publicar aviso' : 'Ver prévia')}
        </button>
      </form>
      <PerguntaSairSemPublicar blocker={blocker} />
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
        // A chave é a versão: "Abrir a versão nova" (C2) recomeça o formulário com ela.
        <FormularioCorrigir
          key={carga.dados.versoes_anteriores.length}
          aviso={carga.dados}
          recarregar={recarregar}
        />
      )}
    </Tela>
  )
}

function FormularioCorrigir({
  aviso,
  recarregar,
}: {
  aviso: AvisoCompleto
  recarregar: () => void
}) {
  const navegar = useNavigate()
  const [rascunho, setRascunho] = useState<Rascunho>(() => rascunhoDe(aviso))
  const [erros, setErros] = useState<Erros>({})
  const [geral, setGeral] = useState('')
  const [enviando, setEnviando] = useState(false)
  const anexos = useAnexos(aviso.anexos)
  const [erroAnexos, setErroAnexos] = useState('')
  // C2: outra pessoa corrigiu depois que este formulário abriu.
  const [corrigidoAgora, setCorrigidoAgora] = useState(false)
  const caixaDeErro = useRef<HTMLDivElement>(null)
  const [inicial] = useState(() => rascunhoDe(aviso))
  const esperando = esperandoOsArquivos(anexos.itens)
  const idsDoAviso = aviso.anexos.map((a) => a.id).join(',')
  const { blocker, liberar } = useAvisarAoSair(
    mudou(rascunho, inicial) ||
      idsProntos(anexos.itens).join(',') !== idsDoAviso ||
      anexos.itens.some((i) => i.situacao !== 'pronto'),
  )

  useEffect(() => {
    if (geral) caixaDeErro.current?.focus()
  }, [geral])

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (esperando) return
    setCorrigidoAgora(false)
    const conferido = conferirTudo(rascunho, anexos.itens)
    setErros(conferido.erros)
    setErroAnexos(conferido.anexos)
    if (conferido.geral) {
      setGeral(conferido.geral)
      return
    }
    setEnviando(true)
    setGeral('')
    try {
      // A lista sempre explícita: o que está na tela é o que a versão nova vai ter.
      await corrigirAviso(aviso.id, {
        ...corpoDe(rascunho),
        anexos: idsProntos(anexos.itens),
        // A versão em vigor quando o formulário abriu (as versões são 1, 2, 3…).
        versao_base: aviso.versoes_anteriores.length + 1,
      })
      liberar()
      navegar(`/avisos/${aviso.id}`, { replace: true, state: { recado: 'Aviso corrigido.' } })
    } catch (e) {
      const { geral: mensagem, campos, anexos: doCampo } = errosDaApi(e)
      setErros(campos)
      setErroAnexos(doCampo)
      setGeral(mensagem)
      setCorrigidoAgora(comoErroDaApi(e).codigo === 'aviso_corrigido_agora')
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
      {corrigidoAgora && (
        <button type="button" className="botao leve" onClick={recarregar}>
          Abrir a versão nova
        </button>
      )}
      <CamposDoAviso
        rascunho={rascunho}
        erros={erros}
        mudar={(mudanca) => {
          setRascunho((atual) => ({ ...atual, ...mudanca }))
          setErros((atuais) => semErrosDe(atuais, mudanca))
        }}
      />
      <EscolherAnexos
        anexos={anexos}
        avisoId={aviso.id}
        erro={erroAnexos}
        aoMudar={() => setErroAnexos('')}
      />
      <button className="botao avisos-enviar" type="submit" disabled={enviando || !!esperando}>
        {esperando ?? (enviando ? 'Salvando…' : 'Salvar correção')}
      </button>
      <PerguntaSairSemPublicar blocker={blocker} />
    </form>
  )
}
