// Tela de entrar (H-01, H-02, H-03). Bloco em 5 botões e apartamento num campo à parte: ninguém
// precisa saber que "Bloco 1, apto 101" vira 1101. A tela junta os dois e manda o login.
import { startTransition, useState, type ClipboardEvent, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { ErroDaApi, MENSAGEM_SEM_CONEXAO } from '../api/cliente'
import { useSessao } from '../casca/contextoSessao'
import { formatarHora } from '../casca/formatar'
import { Marca } from '../casca/Placa'
import { Tela } from '../casca/Tela'
import { entrar } from './api'
import { CaixaDeErro } from './CaixaDeErro'
import { Campo } from './Campo'
import { limparApartamento, montarLogin } from './campos'
import './acesso.css'

const BLOCOS = ['1', '2', '3', '4', '5']
// O mesmo formato que a API aceita (RF-03): bloco 1 a 9, andar 0 a 7, dois dígitos.
const LOGIN_POSSIVEL = /^[1-9][0-7][0-9]{2}$/
const MSG_CREDENCIAIS = 'Bloco, apartamento ou senha incorretos. Confira e tente de novo.'

/** H-03 (revisão do M1, U3): o horário em que dá para tentar de novo, no fuso de Recife. */
function mensagemDeBloqueio(falha: ErroDaApi): string {
  const ate = falha.extras.bloqueada_ate
  if (typeof ate !== 'string') return falha.mensagem
  return (
    `Entrada bloqueada depois de várias senhas erradas. Tente de novo às ${formatarHora(ate)}. ` +
    'Se não foi você, avise a administração do Portal no grupo do WhatsApp.'
  )
}

interface Erro {
  mensagem: string
  bloqueio: boolean
  vez: number
}

export function Entrar() {
  const { definir } = useSessao()
  const navegar = useNavigate()
  const local = useLocation()
  const [bloco, setBloco] = useState('')
  const [apartamento, setApartamento] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState<Erro | null>(null)
  const [enviando, setEnviando] = useState(false)

  function mostrarErro(mensagem: string, bloqueio = false) {
    setErro((anterior) => ({ mensagem, bloqueio, vez: (anterior?.vez ?? 0) + 1 }))
  }

  function aoColar(evento: ClipboardEvent<HTMLInputElement>) {
    const { apartamento: limpo, bloco: doLogin } = limparApartamento(
      evento.clipboardData.getData('text'),
      true,
    )
    if (doLogin) {
      evento.preventDefault()
      setBloco(doLogin)
      setApartamento(limpo)
    }
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault()
    const login = montarLogin(bloco, apartamento)
    if (!bloco) return mostrarErro('Escolha o bloco nos botões de 1 a 5.')
    if (!login) return mostrarErro('Escreva o número do apartamento, como 101.')
    if (!senha) return mostrarErro('Escreva a senha.')
    // Apartamento que não pode existir (andar 8 ou 9): a mesma resposta de qualquer erro.
    if (!LOGIN_POSSIVEL.test(login)) return mostrarErro(MSG_CREDENCIAIS)
    setEnviando(true)
    try {
      const eu = await entrar({ login, senha })
      const de = (local.state as { de?: unknown } | null)?.de
      const destino = eu.precisa_trocar_senha
        ? '/primeiro-acesso'
        : typeof de === 'string' && de.startsWith('/')
          ? de
          : '/avisos'
      // Na mesma transição, para a guarda da entrada não mandar para o mural antes.
      startTransition(() => {
        definir(eu)
        navegar(destino, { replace: true })
      })
    } catch (falha) {
      setEnviando(false)
      if (falha instanceof ErroDaApi && falha.codigo === 'unidade_bloqueada') {
        return mostrarErro(mensagemDeBloqueio(falha), true)
      }
      mostrarErro(falha instanceof ErroDaApi ? falha.mensagem : MENSAGEM_SEM_CONEXAO)
    }
  }

  return (
    <Tela titulo="Portal Capibaribe Prime" entrada>
      <div className="entrada">
        <Marca />
        <h1 className="titulo">Portal Capibaribe Prime</h1>
        <p className="suave">Os avisos oficiais do condomínio, num lugar só.</p>
      </div>
      {erro && (
        <CaixaDeErro icone={erro.bloqueio ? 'cadeado' : 'alerta'} vez={erro.vez}>
          <p>{erro.mensagem}</p>
        </CaixaDeErro>
      )}
      <form onSubmit={aoEnviar} noValidate>
        <fieldset className="blocos">
          <legend>Bloco</legend>
          <div className="blocos-op">
            {BLOCOS.map((numero) => (
              <label key={numero}>
                <input
                  type="radio"
                  name="bloco"
                  value={numero}
                  checked={bloco === numero}
                  onChange={() => setBloco(numero)}
                  aria-label={`Bloco ${numero}`}
                />
                <span aria-hidden="true">{numero}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <label htmlFor="apartamento">Apartamento</label>
        <input
          id="apartamento"
          className="apto"
          type="text"
          inputMode="numeric"
          autoComplete="off"
          value={apartamento}
          onChange={(e) => setApartamento(limparApartamento(e.target.value, false).apartamento)}
          onPaste={aoColar}
          aria-describedby="ajuda-apartamento"
        />
        <p className="ajuda" id="ajuda-apartamento">
          O número da porta, como 101. No térreo, 007 ou só 7.
        </p>
        <Campo
          id="senha"
          rotulo="Senha"
          type="password"
          autoComplete="current-password"
          valor={senha}
          aoMudar={setSenha}
          ajuda="Primeira vez aqui? Use a senha que a Comissão mandou no grupo."
        />
        <button className="botao acesso-enviar" type="submit" disabled={enviando}>
          {enviando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
      <details className="acesso-esqueci">
        <summary className="texto-link">Esqueci minha senha</summary>
        <p>
          Fale com a administração do Portal no grupo do WhatsApp. Ela volta a senha do seu
          apartamento para a inicial, e você escolhe uma nova ao entrar.
        </p>
      </details>
      <p className="centro">
        <Link className="texto-link" to="/privacidade">
          Como o Portal usa seus dados (política de privacidade)
        </Link>
      </p>
    </Tela>
  )
}
