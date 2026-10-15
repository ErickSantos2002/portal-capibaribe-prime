// Épico A do M4 · o formulário da enquete (H-20), o mesmo para criar e editar (spec do épico,
// seção 2). A peça que se destaca é a lista de opções: cada linha leva a marca que o morador vai
// ver na hora de votar (bolinha na escolha única, quadradinho na múltipla), para quem cria
// enxergar a cédula enquanto escreve.
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router'
import { calcularAlcance, listarDestinos } from '../../avisos/api'
import { TextoDoAviso } from '../../avisos/componentes'
import { Icone } from '../../casca/Icone'
import { comoErroDaApi, useCarga } from '../../documentos/carregar'
import { criarEnquete, editarEnquete } from '../api'
import { caminhoEnquete } from '../caminhos'
import type { MostrarResultado } from '../tipos'
import {
  conferir,
  destinoEmTexto,
  limpo,
  MAX_OPCOES,
  MIN_OPCOES,
  opcoesLimpas,
  paraIso,
  textoDoAviso,
  tituloDoAviso,
  type Campo,
  type Erros,
  type Rascunho,
} from './formatos'
import { PerguntaSairSemSalvar } from './SairSemSalvar'
import { useAvisarAoSair } from './useAvisarAoSair'
import '../../avisos/avisos.css'
import './gestao.css'

const RESULTADO: { valor: MostrarResultado; nome: string; explicacao: string }[] = [
  {
    valor: 'durante',
    nome: 'Durante a votação',
    // Revisão do épico B: com a contagem ao vivo, a lista de quem votou entregaria o voto de
    // cada apartamento; por isso ela só aparece no fim (dúvidas do épico A, item 18).
    explicacao:
      'Todos veem a contagem enquanto votam. A lista de quais apartamentos votaram só aparece quando a enquete terminar.',
  },
  {
    valor: 'so_no_fim',
    nome: 'Só quando terminar',
    explicacao:
      'Ninguém vê a contagem antes do fim, nem a Comissão. Enquanto isso, a Comissão acompanha quais apartamentos ainda faltam votar.',
  },
]

// Erros da API que dizem respeito à enquete inteira: a frase e o link para ela.
const SEM_EDICAO = new Set(['enquete_com_voto', 'enquete_encerrada'])
// Revisão, ponto 2: outra pessoa editou depois que a tela abriu.
const MUDOU = 'enquete_mudou'

const CAMPOS_DA_API: Record<string, Campo> = {
  pergunta: 'pergunta',
  opcoes: 'opcoes',
  encerra_em: 'termino',
  blocos: 'blocos',
}

function ErroDoCampo({ id, mensagem }: { id: string; mensagem?: string }) {
  if (!mensagem) return null
  return (
    <p className="enq-erro-campo" id={id}>
      {mensagem}
    </p>
  )
}

function ErroGeral({ mensagem, children }: { mensagem: string; children?: ReactNode }) {
  const caixa = useRef<HTMLDivElement>(null)
  useEffect(() => caixa.current?.focus(), [mensagem])
  return (
    <div className="aviso-caixa erro" role="alert" tabIndex={-1} ref={caixa}>
      <Icone nome="alerta" />
      <div>
        <p>{mensagem}</p>
        {children}
      </div>
    </div>
  )
}

/** Uma chave por caixa de opção, para tirar a do meio sem confundir as outras. */
function useChaves(quantas: number) {
  const proxima = useRef(quantas)
  const [chaves, setChaves] = useState(() => Array.from({ length: quantas }, (_, i) => i))
  return {
    chaves,
    mais() {
      setChaves((atuais) => [...atuais, proxima.current++])
    },
    tirar(indice: number) {
      setChaves((atuais) => atuais.filter((_, i) => i !== indice))
    },
  }
}

/** Os botões "Para quem" e quantos apartamentos isso alcança (só ao criar). */
function EscolherDestino({
  blocos,
  setBlocos,
  erro,
}: {
  blocos: number[]
  setBlocos: (b: number[]) => void
  erro?: string
}) {
  const [destinos, recarregar] = useCarga(listarDestinos, [])
  const [alcance] = useCarga(() => calcularAlcance(blocos), [blocos.join(',')])
  const unidades = alcance.situacao === 'pronta' ? alcance.dados.unidades : null
  function alternar(numero: number) {
    setBlocos(
      blocos.includes(numero)
        ? blocos.filter((b) => b !== numero)
        : [...blocos, numero].sort((a, b) => a - b),
    )
  }
  return (
    <>
      <p className="enq-rotulo" id="enq-destino">
        Para quem
      </p>
      {destinos.situacao === 'erro' ? (
        <div className="aviso-caixa erro" role="alert">
          <Icone nome="alerta" />
          <div>
            <p>{destinos.erro.mensagem}</p>
            <button type="button" className="texto-link" onClick={recarregar}>
              Tentar de novo
            </button>
          </div>
        </div>
      ) : (
        <div
          className="chips"
          role="group"
          aria-labelledby="enq-destino"
          aria-describedby={erro ? 'enq-blocos-erro' : undefined}
        >
          <button
            type="button"
            className="chip"
            aria-pressed={blocos.length === 0}
            onClick={() => setBlocos([])}
          >
            Todos os blocos
          </button>
          {destinos.dados?.blocos.map((b) => (
            <button
              key={b.numero}
              type="button"
              className="chip"
              aria-pressed={blocos.includes(b.numero)}
              onClick={() => alternar(b.numero)}
            >
              {b.nome}
            </button>
          ))}
        </div>
      )}
      <ErroDoCampo id="enq-blocos-erro" mensagem={erro} />
      <div className="aviso-caixa info enq-alcance" aria-live="polite">
        <Icone nome="sino" />
        <p>
          {unidades === null ? (
            'Contando os apartamentos…'
          ) : (
            <>
              A enquete e o aviso dela vão para <b>{unidades}</b> apartamentos (
              {destinoEmTexto(blocos.length === 0, blocos)}), com notificação, e por e-mail para
              quem cadastrou.
            </>
          )}
        </p>
      </div>
    </>
  )
}

function PreviaDoAviso({ rascunho, editando }: { rascunho: Rascunho; editando: boolean }) {
  const pronta =
    !!rascunho.pergunta.trim() &&
    opcoesLimpas(rascunho.opcoes).length >= MIN_OPCOES &&
    !!rascunho.dia &&
    !!rascunho.hora
  return (
    <section className="enq-previa" aria-label="Como o aviso vai ficar">
      <p className="enq-previa-rotulo">
        {editando ? 'Como o aviso vai ficar depois de salvar' : 'Como o aviso vai ficar no mural'}
      </p>
      {pronta ? (
        <>
          <p className="enq-previa-categoria">Geral</p>
          <p className="enq-previa-titulo">{tituloDoAviso(rascunho.pergunta)}</p>
          <TextoDoAviso texto={textoDoAviso(rascunho)} nivel={3} />
        </>
      ) : (
        <p className="suave">
          Aparece aqui quando a pergunta, duas opções e o término estiverem preenchidos.
        </p>
      )}
      <p className="ajuda">
        {editando
          ? 'Ao salvar, o aviso é corrigido (aparece “Editado em”), sem tocar o celular de ninguém de novo.'
          : 'O aviso sai sozinho junto com a enquete, com o botão “Ir para a enquete”.'}
      </p>
    </section>
  )
}

type Modo =
  | { tipo: 'nova' }
  | {
      tipo: 'editar'
      id: number
      paraTodos: boolean
      blocos: number[]
      /** O `editada_em` da enquete carregada: vai como `editada_em_base` (revisão, ponto 2). */
      editadaEm: string | null
      /** Carrega a versão nova, quando outra pessoa editou antes (409 `enquete_mudou`). */
      recarregar: () => void
    }

export function FormularioEnquete({ modo, inicial }: { modo: Modo; inicial: Rascunho }) {
  const navegar = useNavigate()
  const editando = modo.tipo === 'editar'
  const [rascunho, setRascunho] = useState<Rascunho>(inicial)
  const opcoes = useChaves(inicial.opcoes.length)
  const [blocos, setBlocos] = useState<number[]>([])
  const [erros, setErros] = useState<Erros>({})
  const [geral, setGeral] = useState<{
    mensagem: string
    semEdicao: boolean
    mudou: boolean
  } | null>(null)
  const [enviando, setEnviando] = useState(false)
  const focarNaUltima = useRef(false)
  const lista = useRef<HTMLOListElement>(null)
  const sujo =
    JSON.stringify(rascunho) !== JSON.stringify(inicial) || blocos.length > 0 || enviando
  const { blocker, liberar } = useAvisarAoSair(sujo)

  useEffect(() => {
    if (!focarNaUltima.current) return
    focarNaUltima.current = false
    const caixas = lista.current?.querySelectorAll('input')
    caixas?.[caixas.length - 1]?.focus()
  }, [opcoes.chaves])

  function mudar(mudanca: Partial<Rascunho>, campo?: Campo) {
    setRascunho((atual) => ({ ...atual, ...mudanca }))
    if (campo) {
      setErros((atuais) => {
        const resto = { ...atuais }
        delete resto[campo]
        return resto
      })
    }
  }

  function mudarOpcao(indice: number, texto: string) {
    mudar({ opcoes: rascunho.opcoes.map((o, i) => (i === indice ? texto : o)) }, 'opcoes')
  }

  function maisOpcao() {
    if (rascunho.opcoes.length >= MAX_OPCOES) return
    focarNaUltima.current = true
    opcoes.mais()
    mudar({ opcoes: [...rascunho.opcoes, ''] }, 'opcoes')
  }

  function tirarOpcao(indice: number) {
    opcoes.tirar(indice)
    mudar({ opcoes: rascunho.opcoes.filter((_, i) => i !== indice) }, 'opcoes')
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (enviando) return
    // Na edição, o término que já estava gravado não pede de novo "pelo menos 1 hora".
    const encontrados = conferir(
      rascunho,
      new Date(),
      editando ? { dia: inicial.dia, hora: inicial.hora } : undefined,
    )
    setErros(encontrados)
    const mensagens = Object.values(encontrados)
    if (mensagens.length > 0) {
      setGeral({
        mensagem: mensagens.length === 1 ? mensagens[0] : 'Confira os campos marcados.',
        semEdicao: false,
        mudou: false,
      })
      return
    }
    setGeral(null)
    setEnviando(true)
    const corpo = {
      pergunta: limpo(rascunho.pergunta),
      opcoes: opcoesLimpas(rascunho.opcoes),
      multipla_escolha: rascunho.multipla,
      encerra_em: paraIso(rascunho.dia, rascunho.hora),
      mostrar_resultado: rascunho.mostrar,
    }
    try {
      const gravada =
        modo.tipo === 'editar'
          ? await editarEnquete(modo.id, { ...corpo, editada_em_base: modo.editadaEm })
          : await criarEnquete({ ...corpo, para_todos: blocos.length === 0, blocos })
      liberar()
      navegar(caminhoEnquete(gravada.id), {
        replace: true,
        state: {
          recado: editando
            ? 'Enquete atualizada. O aviso foi corrigido.'
            : 'Enquete publicada. O aviso saiu no mural.',
        },
      })
    } catch (e) {
      const erro = comoErroDaApi(e)
      const campos: Erros = {}
      for (const c of erro.campos) {
        const campo = CAMPOS_DA_API[c.campo?.split('.')[0] ?? '']
        if (campo) campos[campo] ??= c.mensagem
      }
      if (erro.codigo === 'bloco_inexistente') campos.blocos ??= erro.mensagem
      setErros(campos)
      setGeral({
        mensagem: erro.mensagem,
        semEdicao: SEM_EDICAO.has(erro.codigo),
        mudou: erro.codigo === MUDOU,
      })
      setEnviando(false)
    }
  }

  const marca = rascunho.multipla ? 'enq-marca quadrada' : 'enq-marca'
  const cheia = rascunho.opcoes.length >= MAX_OPCOES

  return (
    <>
      <form onSubmit={enviar} noValidate className="enq-form">
        {geral && (
          <ErroGeral mensagem={geral.mensagem}>
            {geral.semEdicao && modo.tipo === 'editar' && (
              <Link className="texto-link" to={caminhoEnquete(modo.id)}>
                Ver a enquete
              </Link>
            )}
            {geral.mudou && modo.tipo === 'editar' && (
              <button type="button" className="texto-link" onClick={modo.recarregar}>
                Abrir a versão nova
              </button>
            )}
          </ErroGeral>
        )}

        <label htmlFor="enq-pergunta">Pergunta</label>
        {/* Caixa de 2 linhas: a pergunta inteira aparece no celular. Enter não quebra a linha
            (a pergunta é uma frase só). */}
        <textarea
          id="enq-pergunta"
          rows={2}
          value={rascunho.pergunta}
          onKeyDown={(e) => {
            if (e.key === 'Enter') e.preventDefault()
          }}
          onChange={(e) => mudar({ pergunta: e.target.value.replace(/\s*\n\s*/g, ' ') }, 'pergunta')}
          aria-invalid={!!erros.pergunta}
          aria-describedby={erros.pergunta ? 'enq-pergunta-erro' : 'enq-pergunta-ajuda'}
          className={erros.pergunta ? 'enq-pergunta campo-erro' : 'enq-pergunta'}
        />
        <ErroDoCampo id="enq-pergunta-erro" mensagem={erros.pergunta} />
        <p className="ajuda" id="enq-pergunta-ajuda">
          Ex.: Qual o melhor dia para a reunião com a construtora?
        </p>

        <fieldset
          className="enq-cedula"
          aria-describedby={erros.opcoes ? 'enq-opcoes-erro' : 'enq-opcoes-ajuda'}
        >
          <legend>Opções de resposta</legend>
          <ol className="enq-opcoes" ref={lista}>
            {opcoes.chaves.map((chave, i) => (
              <li key={chave}>
                <span className={marca} aria-hidden="true" />
                <input
                  type="text"
                  aria-label={`Opção ${i + 1}`}
                  value={rascunho.opcoes[i] ?? ''}
                  onChange={(e) => mudarOpcao(i, e.target.value)}
                  aria-invalid={!!erros.opcoes}
                  className={erros.opcoes ? 'campo-erro' : undefined}
                />
                {i >= MIN_OPCOES && (
                  <button
                    type="button"
                    className="enq-tirar"
                    aria-label={`Tirar a opção ${i + 1}`}
                    onClick={() => tirarOpcao(i)}
                  >
                    Tirar
                  </button>
                )}
              </li>
            ))}
          </ol>
          {!cheia && (
            <button type="button" className="texto-link enq-mais" onClick={maisOpcao}>
              <Icone nome="mais" />
              Adicionar opção
            </button>
          )}
          <ErroDoCampo id="enq-opcoes-erro" mensagem={erros.opcoes} />
          <p className="ajuda" id="enq-opcoes-ajuda">
            {cheia ? 'O limite é de 10 opções.' : 'De 2 a 10 opções. As caixas em branco ficam de fora.'}
          </p>
        </fieldset>

        <label className="opcao enq-multipla">
          <input
            type="checkbox"
            checked={rascunho.multipla}
            onChange={(e) => mudar({ multipla: e.target.checked })}
          />
          Pode marcar mais de uma opção
        </label>

        <fieldset
          className="enq-termino"
          aria-describedby={erros.termino ? 'enq-termino-erro' : 'enq-termino-ajuda'}
        >
          <legend className="oculto">Quando a enquete termina</legend>
          <div className="enq-lado">
            <div>
              <label htmlFor="enq-dia">Dia do término</label>
              <input
                id="enq-dia"
                type="date"
                value={rascunho.dia}
                onChange={(e) => mudar({ dia: e.target.value }, 'termino')}
                aria-invalid={!!erros.termino}
                className={erros.termino ? 'campo-erro' : undefined}
              />
            </div>
            <div>
              <label htmlFor="enq-hora">Hora do término</label>
              <input
                id="enq-hora"
                type="time"
                value={rascunho.hora}
                onChange={(e) => mudar({ hora: e.target.value }, 'termino')}
                aria-invalid={!!erros.termino}
                className={erros.termino ? 'campo-erro' : undefined}
              />
            </div>
          </div>
          <ErroDoCampo id="enq-termino-erro" mensagem={erros.termino} />
          <p className="ajuda" id="enq-termino-ajuda">
            Horário de Recife. Depois disso ninguém vota nem troca o voto. Até 1 ano.
          </p>
        </fieldset>

        <fieldset className="enq-resultado">
          <legend>Quando mostrar o resultado</legend>
          {RESULTADO.map((r) => (
            <label key={r.valor} className="opcao enq-resultado-op">
              <input
                type="radio"
                name="enq-resultado"
                value={r.valor}
                checked={rascunho.mostrar === r.valor}
                onChange={() => mudar({ mostrar: r.valor })}
              />
              <span>
                <b>{r.nome}</b>
                <span className="suave">{r.explicacao}</span>
              </span>
            </label>
          ))}
        </fieldset>

        {modo.tipo === 'editar' ? (
          <>
            <p className="enq-rotulo">Para quem</p>
            <p className="enq-destino-fixo">
              <b>{destinoEmTexto(modo.paraTodos, modo.blocos)}</b>
              <span className="ajuda">O destino não muda depois de publicada.</span>
            </p>
          </>
        ) : (
          <EscolherDestino
            blocos={blocos}
            setBlocos={(b) => {
              setBlocos(b)
              setErros((atuais) => ({ ...atuais, blocos: undefined }))
            }}
            erro={erros.blocos}
          />
        )}

        <div className="aviso-caixa atencao">
          <Icone nome="alerta" />
          <p>Depois do primeiro voto, a pergunta e as opções não podem mais mudar.</p>
        </div>

        <PreviaDoAviso rascunho={rascunho} editando={editando} />

        {editando && (
          // Revisão, ponto 3: a enquete é a fonte da verdade; uma correção feita à mão no aviso
          // fica só nas versões anteriores dele.
          <p className="ajuda enq-reescreve">Salvar reescreve o texto do aviso desta enquete.</p>
        )}

        <button className="botao enq-enviar" type="submit" disabled={enviando}>
          {editando
            ? enviando
              ? 'Salvando…'
              : 'Salvar alterações'
            : enviando
              ? 'Publicando…'
              : 'Publicar enquete'}
        </button>
      </form>
      <PerguntaSairSemSalvar
        blocker={blocker}
        titulo={editando ? 'Sair sem salvar?' : 'Sair sem publicar?'}
      />
    </>
  )
}
