// Minha unidade (H-06, RNF-12): ver, corrigir e apagar os próprios dados; trocar a senha;
// ver e desconectar aparelhos.
import {
  startTransition,
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from 'react'
import { Link, useNavigate } from 'react-router'
import { ErroDaApi } from '../api/cliente'
import { useRecado } from '../casca/contextoRecado'
import { useSessao } from '../casca/contextoSessao'
import { formatarCelular, formatarDataEHora, nomeDaUnidade, nomeDoPapel } from '../casca/formatar'
import { Icone } from '../casca/Icone'
import { centralizar } from '../casca/rolar'
import { Tela } from '../casca/Tela'
import { SecaoNotificacoes } from '../notificacoes/SecaoNotificacoes'
import { BotaoVersao } from '../sobre/BotaoVersao'
import {
  apagarDados,
  buscarMinhaUnidade,
  desconectarAparelho,
  salvarDados,
  trocarSenha,
} from './api'
import { CaixaDeErro } from './CaixaDeErro'
import { Campo } from './Campo'
import {
  AJUDA_DA_SENHA,
  contatoParaApi,
  erroDaFalha,
  validarContato,
  validarSenhaNova,
  type ContatoDigitado,
} from './campos'
import { CamposDeContato } from './CamposDeContato'
import type { Aparelho, MinhaUnidade as Dados } from './tipos'
import './acesso.css'

type Painel = 'dados' | 'senha' | 'apagar' | null
type Onde = 'topo' | 'aparelhos' | 'privacidade' | 'dados' | 'senha'

interface Erro {
  onde: Onde
  campo: string | null
  mensagem: string
  vez: number
}

const PREFIXO_DADOS = 'md'
const PREFIXO_SENHA = 'ts'
const PREFIXO_APAGAR = 'ap'

export function MinhaUnidade() {
  const { definir, sair, recarregar } = useSessao()
  const recado = useRecado()
  const navegar = useNavigate()
  const [dados, setDados] = useState<Dados | null>(null)
  const [painel, setPainel] = useState<Painel>(null)
  const [erro, setErro] = useState<Erro | null>(null)
  const [ocupado, setOcupado] = useState(false)
  // U7: depois de trocar a senha, o recado fica na tela (não só no aviso que some) e recebe o
  // foco, para quem usa leitor de tela saber que deu certo e onde está.
  const [senhaTrocada, setSenhaTrocada] = useState(false)
  const recadoDaSenha = useRef<HTMLParagraphElement>(null)
  useEffect(() => {
    if (senhaTrocada) recadoDaSenha.current?.focus()
  }, [senhaTrocada])

  const mostrarErro = useCallback((onde: Onde, falha: unknown, campo?: string) => {
    const lido = erroDaFalha(falha)
    setErro((anterior) => ({
      onde,
      campo: campo ?? lido.campo,
      mensagem: lido.mensagem,
      vez: (anterior?.vez ?? 0) + 1,
    }))
  }, [])

  const carregar = useCallback(async () => {
    try {
      setDados(await buscarMinhaUnidade())
    } catch (falha) {
      // Sessão caiu (outro aparelho trocou a senha): a casca leva para a entrada.
      if (falha instanceof ErroDaApi && falha.status === 401) return void recarregar()
      mostrarErro('topo', falha)
    }
  }, [recarregar, mostrarErro])

  useEffect(() => {
    let ativo = true
    buscarMinhaUnidade().then(
      (lidos) => ativo && setDados(lidos),
      (falha) => {
        if (!ativo) return
        if (falha instanceof ErroDaApi && falha.status === 401) return void recarregar()
        mostrarErro('topo', falha)
      },
    )
    return () => {
      ativo = false
    }
  }, [recarregar, mostrarErro])

  function abrirPainel(qual: Painel) {
    setErro(null)
    setSenhaTrocada(false)
    setPainel((atual) => (atual === qual ? null : qual))
  }

  async function aoSair() {
    setOcupado(true)
    try {
      await sair()
      navegar('/entrar', { replace: true })
    } catch (falha) {
      setOcupado(false)
      mostrarErro('aparelhos', falha)
    }
  }

  async function aoDesconectar(aparelho: Aparelho) {
    setOcupado(true)
    try {
      await desconectarAparelho(aparelho.id)
      recado(`${aparelho.descricao} desconectado.`)
      await carregar()
    } catch (falha) {
      mostrarErro('aparelhos', falha)
    } finally {
      setOcupado(false)
    }
  }

  async function aoApagar(senha: string) {
    if (!senha) return mostrarErro('privacidade', new ErroLocal('Escreva a senha atual.'), 'senha')
    setOcupado(true)
    try {
      await apagarDados(senha)
      // Na mesma transição: senão a guarda da tela (sem sessão → /entrar) navega primeiro e o
      // recado se perde.
      startTransition(() => {
        definir(null)
        navegar('/entrar', {
          replace: true,
          state: { recado: 'Seus dados foram apagados. A senha voltou a ser a inicial.' },
        })
      })
    } catch (falha) {
      setOcupado(false)
      mostrarErro('privacidade', falha)
    }
  }

  const caixa = (onde: Onde, prefixo?: string) =>
    erro?.onde === onde && (
      <CaixaDeErro
        vez={erro.vez}
        focar={prefixo && erro.campo ? `${prefixo}-${erro.campo}` : undefined}
      >
        <p>{erro.mensagem}</p>
      </CaixaDeErro>
    )

  return (
    <Tela titulo="Minha unidade">
      {caixa('topo')}
      {!dados ? (
        erro?.onde !== 'topo' && (
          <p className="vazio" role="status">
            Abrindo os dados do apartamento…
          </p>
        )
      ) : (
        <>
          <dl className="ficha">
            <div>
              <dt>Apartamento</dt>
              <dd>{nomeDaUnidade(dados.unidade)}</dd>
            </div>
            <div>
              <dt>Responsável</dt>
              <dd>{dados.responsavel_nome}</dd>
            </div>
            <div>
              <dt>Celular</dt>
              <dd>{formatarCelular(dados.celular)}</dd>
            </div>
            <div>
              <dt>E-mail</dt>
              <dd>{dados.email ?? 'não informado'}</dd>
            </div>
            {dados.papeis.length > 0 && (
              <div>
                <dt>Papel</dt>
                <dd>{dados.papeis.map(nomeDoPapel).join(', ')}</dd>
              </div>
            )}
          </dl>

          <button
            type="button"
            className="botao leve"
            aria-expanded={painel === 'dados'}
            onClick={() => abrirPainel('dados')}
          >
            <Icone nome="editar" /> Mudar meus dados
          </button>
          {painel === 'dados' && (
            <FormularioDeDados
              inicial={dados}
              caixa={caixa('dados', PREFIXO_DADOS)}
              erro={erro?.onde === 'dados' ? erro : null}
              aoErrar={(falha, campo) => mostrarErro('dados', falha, campo)}
              aoSalvar={(novos) => {
                setDados(novos)
                setPainel(null)
                setErro(null)
                recado('Dados salvos.')
              }}
              aoCancelar={() => abrirPainel(null)}
            />
          )}

          <button
            type="button"
            className="botao leve"
            aria-expanded={painel === 'senha'}
            onClick={() => abrirPainel('senha')}
          >
            <Icone nome="cadeado" /> Trocar a senha
          </button>
          {painel === 'senha' && (
            <FormularioDeSenha
              caixa={caixa('senha', PREFIXO_SENHA)}
              erro={erro?.onde === 'senha' ? erro : null}
              aoErrar={(falha, campo) => mostrarErro('senha', falha, campo)}
              aoSalvar={async () => {
                setPainel(null)
                setErro(null)
                setSenhaTrocada(true)
                await carregar()
              }}
              aoCancelar={() => abrirPainel(null)}
            />
          )}

          {senhaTrocada && (
            <p
              className="aviso-caixa info acesso-sucesso"
              ref={recadoDaSenha}
              tabIndex={-1}
              role="status"
            >
              Senha trocada. Os outros aparelhos foram desconectados.
            </p>
          )}

          <SecaoNotificacoes />

          <h2 className="secao">Aparelhos conectados</h2>
          {caixa('aparelhos')}
          <div className="folha">
            {dados.aparelhos.map((aparelho) => (
              <div className="item acesso-aparelho" key={aparelho.id}>
                <h3 className="com-icone">
                  <Icone
                    nome={/^(Android|iPhone|iPad)/.test(aparelho.descricao) ? 'celular' : 'monitor'}
                  />
                  {aparelho.descricao}
                </h3>
                {/* U11: aparelhos de mesmo nome se distinguem por quando entraram e pelo uso. */}
                <span className="linha-meta">
                  {aparelho.este_aparelho ? 'este aparelho · ' : ''}entrou em{' '}
                  {formatarDataEHora(aparelho.criada_em)}
                  {!aparelho.este_aparelho &&
                    ` · último uso em ${formatarDataEHora(aparelho.ultimo_uso_em)}`}
                </span>
                {!aparelho.este_aparelho && (
                  <>
                    <button
                      type="button"
                      className="texto-link"
                      disabled={ocupado}
                      onClick={() => void aoDesconectar(aparelho)}
                      aria-label={`Desconectar ${aparelho.descricao}`}
                    >
                      Desconectar
                    </button>
                  </>
                )}
              </div>
            ))}
          </div>
          <div className="acesso-espaco" />
          <button
            type="button"
            className="botao leve"
            disabled={ocupado}
            onClick={() => void aoSair()}
          >
            <Icone nome="sair" /> Sair deste aparelho
          </button>

          <h2 className="secao">Privacidade</h2>
          <p className="ajuda">
            Apaga nome, celular e e-mail, desconecta todos os aparelhos e volta a senha para a
            inicial. Os votos e as leituras do apartamento continuam valendo.
          </p>
          <p>
            <Link className="texto-link" to="/privacidade">
              Ler a política de privacidade
            </Link>
          </p>
          {painel !== 'apagar' && caixa('privacidade')}
          {painel === 'apagar' ? (
            <ConfirmarApagar
              ocupado={ocupado}
              caixa={caixa('privacidade', PREFIXO_APAGAR)}
              erro={
                erro?.onde === 'privacidade' && erro.campo === 'senha' ? erro.mensagem : undefined
              }
              aoConfirmar={(senha) => void aoApagar(senha)}
              aoCancelar={() => abrirPainel(null)}
            />
          ) : (
            <button type="button" className="botao perigo" onClick={() => abrirPainel('apagar')}>
              Apagar meus dados
            </button>
          )}

          {/* No computador, a versão já está no pé do menu lateral. */}
          <p className="versao-rodape so-cel">
            <BotaoVersao />
          </p>
        </>
      )}
    </Tela>
  )
}

// --- formulários que abrem na própria tela --------------------------------------------------------

interface PropsFormulario<T> {
  caixa: ReactNode
  erro: Erro | null
  aoErrar: (falha: unknown, campo?: string) => void
  aoSalvar: (resultado: T) => void | Promise<void>
  aoCancelar: () => void
}

function FormularioDeDados({
  inicial,
  caixa,
  erro,
  aoErrar,
  aoSalvar,
  aoCancelar,
}: PropsFormulario<Dados> & { inicial: Dados }) {
  const [contato, setContato] = useState<ContatoDigitado>({
    responsavel_nome: inicial.responsavel_nome ?? '',
    celular: formatarCelular(inicial.celular),
    email: inicial.email ?? '',
  })
  const [enviando, setEnviando] = useState(false)

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault()
    const problema = validarContato(contato)
    if (problema) return aoErrar(new ErroLocal(problema.mensagem), problema.campo)
    setEnviando(true)
    try {
      await aoSalvar(await salvarDados(contatoParaApi(contato)))
    } catch (falha) {
      setEnviando(false)
      aoErrar(falha)
    }
  }

  return (
    <form className="acesso-painel" onSubmit={aoEnviar} noValidate aria-label="Mudar meus dados">
      <h2>Mudar meus dados</h2>
      {caixa}
      <CamposDeContato prefixo={PREFIXO_DADOS} contato={contato} aoMudar={setContato} erro={erro} />
      <button className="botao acesso-enviar" type="submit" disabled={enviando}>
        {enviando ? 'Salvando…' : 'Salvar dados'}
      </button>
      <button className="botao leve" type="button" onClick={aoCancelar}>
        Cancelar
      </button>
    </form>
  )
}

function FormularioDeSenha({ caixa, erro, aoErrar, aoSalvar, aoCancelar }: PropsFormulario<void>) {
  const [atual, setAtual] = useState('')
  const [nova, setNova] = useState('')
  const [repetida, setRepetida] = useState('')
  const [enviando, setEnviando] = useState(false)
  const erroDe = (campo: string) => (erro?.campo === campo ? erro.mensagem : undefined)

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault()
    if (!atual) return aoErrar(new ErroLocal('Escreva a senha atual.'), 'senha_atual')
    const problema = validarSenhaNova(nova, repetida, atual)
    if (problema) return aoErrar(new ErroLocal(problema.mensagem), problema.campo)
    setEnviando(true)
    try {
      await trocarSenha({ senha_atual: atual, senha_nova: nova, senha_nova_repetida: repetida })
      await aoSalvar()
    } catch (falha) {
      setEnviando(false)
      aoErrar(falha)
    }
  }

  return (
    <form className="acesso-painel" onSubmit={aoEnviar} noValidate aria-label="Trocar a senha">
      <h2>Trocar a senha</h2>
      <p className="ajuda">
        Os outros aparelhos do apartamento vão precisar entrar de novo, com a senha nova.
      </p>
      {caixa}
      <Campo
        id={`${PREFIXO_SENHA}-senha_atual`}
        rotulo="Senha atual"
        type="password"
        autoComplete="current-password"
        valor={atual}
        aoMudar={setAtual}
        erro={erroDe('senha_atual')}
      />
      <Campo
        id={`${PREFIXO_SENHA}-senha_nova`}
        rotulo="Senha nova"
        type="password"
        autoComplete="new-password"
        valor={nova}
        aoMudar={setNova}
        ajuda={AJUDA_DA_SENHA}
        erro={erroDe('senha_nova')}
      />
      <Campo
        id={`${PREFIXO_SENHA}-senha_nova_repetida`}
        rotulo="Repita a senha nova"
        type="password"
        autoComplete="new-password"
        valor={repetida}
        aoMudar={setRepetida}
        erro={erroDe('senha_nova_repetida')}
      />
      <button className="botao acesso-enviar" type="submit" disabled={enviando}>
        {enviando ? 'Salvando…' : 'Salvar a senha nova'}
      </button>
      <button className="botao leve" type="button" onClick={aoCancelar}>
        Cancelar
      </button>
    </form>
  )
}

function ConfirmarApagar({
  ocupado,
  caixa,
  erro,
  aoConfirmar,
  aoCancelar,
}: {
  ocupado: boolean
  caixa: ReactNode
  erro?: string
  aoConfirmar: (senha: string) => void
  aoCancelar: () => void
}) {
  const [senha, setSenha] = useState('')
  const bloco = useRef<HTMLFormElement>(null)
  const titulo = useRef<HTMLHeadingElement>(null)
  // U2: o bloco inteiro vai para o meio da tela, longe das abas de baixo.
  useEffect(() => centralizar(bloco.current, titulo.current), [])
  return (
    <form
      ref={bloco}
      className="acesso-painel acesso-confirmar"
      role="group"
      aria-labelledby="confirmar-apagar"
      noValidate
      onSubmit={(evento) => {
        evento.preventDefault()
        aoConfirmar(senha)
      }}
    >
      <h2 id="confirmar-apagar" ref={titulo} tabIndex={-1}>
        Apagar os dados do apartamento?
      </h2>
      <p>
        Nome, celular e e-mail somem, todos os aparelhos saem e a senha volta a ser a inicial. O
        apartamento vai precisar fazer o primeiro acesso de novo.
      </p>
      {/* C1: o risco de a senha voltar a ser a inicial, em destaque. */}
      <div className="aviso-caixa atencao acesso-risco" role="note">
        <Icone nome="alerta" />
        <p>
          <strong>Depois de apagar, qualquer pessoa com a senha inicial pode entrar.</strong>
          Quem chegar primeiro faz o primeiro acesso e fica com a conta do apartamento. Logo depois
          de apagar, faça o primeiro acesso de novo ou avise a administração do Portal no grupo do
          WhatsApp.
        </p>
      </div>
      {caixa}
      <Campo
        id={`${PREFIXO_APAGAR}-senha`}
        rotulo="Senha atual"
        type="password"
        autoComplete="current-password"
        valor={senha}
        aoMudar={setSenha}
        ajuda="Para confirmar que é você."
        erro={erro}
      />
      <button type="submit" className="botao perigo" disabled={ocupado}>
        {ocupado ? 'Apagando…' : 'Sim, apagar meus dados'}
      </button>
      <button type="button" className="botao leve" onClick={aoCancelar}>
        Cancelar
      </button>
    </form>
  )
}

/** Erro da própria tela (antes de chamar a API), no mesmo formato que `erroDaFalha` entende. */
class ErroLocal extends ErroDaApi {
  constructor(mensagem: string) {
    super(0, { codigo: 'dados_invalidos', mensagem })
  }
}
