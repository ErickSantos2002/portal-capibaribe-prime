// "Criar senha nova" (H-04): a tela que o link do e-mail abre. O token vem depois do `#` (não
// vai ao servidor nem fica em log); a tela o lê uma vez, apaga da barra e o manda no corpo do
// POST. Senha com as mesmas regras e mensagens do primeiro acesso.
import { startTransition, useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { ErroDaApi } from '../api/cliente'
import type { UnidadeRef } from '../api/tipos'
import { CaixaDeErro } from '../acesso/CaixaDeErro'
import { Campo } from '../acesso/Campo'
import { AJUDA_DA_SENHA, erroDaFalha, validarSenhaNova } from '../acesso/campos'
import { useSessao } from '../casca/contextoSessao'
import { Icone } from '../casca/Icone'
import { Placa } from '../casca/Placa'
import { Tela } from '../casca/Tela'
import { conferirLink, redefinirSenha } from './api'
import '../acesso/acesso.css'
import './recuperacao.css'

const PREFIXO = 'rs'
const RECADO_SENHA_NOVA =
  'Senha nova criada. Os outros aparelhos foram desconectados. Avise a família da senha nova.'
const MSG_SEM_TOKEN = 'Este link está incompleto. Peça outro em "Esqueci minha senha".'

type Estado =
  | { situacao: 'conferindo' }
  | { situacao: 'invalido'; mensagem: string }
  | { situacao: 'sem_conexao'; mensagem: string }
  | { situacao: 'valido'; unidade: UnidadeRef }

/** `#token=abc` → `abc`. */
function tokenDoEndereco(hash: string): string | null {
  return new URLSearchParams(hash.replace(/^#/, '')).get('token') || null
}

interface Erro {
  campo: string | null
  mensagem: string
  vez: number
}

export function RedefinirSenha() {
  const local = useLocation()
  const navegar = useNavigate()
  const { eu, definir } = useSessao()
  // Lido uma vez: logo depois o `#` sai da barra.
  const [token] = useState(() => tokenDoEndereco(local.hash))
  const [estado, setEstado] = useState<Estado>(
    token ? { situacao: 'conferindo' } : { situacao: 'invalido', mensagem: MSG_SEM_TOKEN },
  )
  const [tentativa, setTentativa] = useState(0)
  const [senha, setSenha] = useState('')
  const [repetida, setRepetida] = useState('')
  const [erro, setErro] = useState<Erro | null>(null)
  const [enviando, setEnviando] = useState(false)

  // Tira o token da barra (e do histórico): quem olhar a tela ou o histórico não o vê.
  useEffect(() => {
    if (local.hash) {
      navegar({ pathname: local.pathname, search: local.search }, { replace: true })
    }
  }, [local.hash, local.pathname, local.search, navegar])

  useEffect(() => {
    if (!token) return
    let valendo = true
    conferirLink(token).then(
      ({ unidade }) => valendo && setEstado({ situacao: 'valido', unidade }),
      (falha: unknown) => {
        if (!valendo) return
        if (falha instanceof ErroDaApi && falha.status === 410) {
          setEstado({ situacao: 'invalido', mensagem: falha.mensagem })
        } else {
          setEstado({ situacao: 'sem_conexao', mensagem: erroDaFalha(falha).mensagem })
        }
      },
    )
    return () => {
      valendo = false
    }
  }, [token, tentativa])

  function mostrarErro(campo: string | null, mensagem: string) {
    setErro((anterior) => ({ campo, mensagem, vez: (anterior?.vez ?? 0) + 1 }))
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault()
    const problema = validarSenhaNova(senha, repetida)
    if (problema) return mostrarErro(problema.campo, problema.mensagem)
    if (!token) return
    setEnviando(true)
    try {
      const eu = await redefinirSenha({
        token,
        senha_nova: senha,
        senha_nova_repetida: repetida,
      })
      startTransition(() => {
        definir(eu)
        navegar('/avisos', { replace: true, state: { recado: RECADO_SENHA_NOVA } })
      })
    } catch (falha) {
      setEnviando(false)
      if (falha instanceof ErroDaApi && falha.status === 410) {
        return setEstado({ situacao: 'invalido', mensagem: falha.mensagem })
      }
      const { campo, mensagem } = erroDaFalha(falha)
      mostrarErro(campo, mensagem)
    }
  }

  const erroDe = (campo: string) => (erro?.campo === campo ? erro.mensagem : undefined)

  return (
    <Tela titulo="Criar senha nova" voltar="/entrar">
      {estado.situacao === 'conferindo' && (
        <p className="vazio" role="status">
          Conferindo o link…
        </p>
      )}

      {estado.situacao === 'invalido' && eu && (
        // Link já usado com o aparelho entrado (quase sempre: acabou de criar a senha e voltou
        // ao link). "Pedir outro link" cairia no mural sem explicar nada.
        <>
          <div className="aviso-caixa info" role="status">
            <Icone nome="info" />
            <p>Você já está no Portal. Para trocar a senha de novo, vá em Minha unidade.</p>
          </div>
          <Link className="botao" to="/avisos">
            Ir para os avisos
          </Link>
        </>
      )}

      {estado.situacao === 'invalido' && !eu && (
        <>
          <div className="aviso-caixa atencao" role="alert">
            <Icone nome="relogio" />
            <p>{estado.mensagem}</p>
          </div>
          <p>O link do e-mail vale por 1 hora e só uma vez.</p>
          <Link className="botao" to="/esqueci-a-senha">
            Pedir outro link
          </Link>
          <Link className="botao leve" to="/entrar">
            Voltar para a entrada
          </Link>
        </>
      )}

      {estado.situacao === 'sem_conexao' && (
        <>
          <div className="aviso-caixa erro" role="alert">
            <Icone nome="alerta" />
            <p>{estado.mensagem}</p>
          </div>
          <button
            type="button"
            className="botao"
            onClick={() => {
              setEstado({ situacao: 'conferindo' })
              setTentativa((n) => n + 1)
            }}
          >
            Tentar de novo
          </button>
        </>
      )}

      {estado.situacao === 'valido' && (
        <>
          <div className="centro">
            <Placa unidade={estado.unidade} grande decorativa />
          </div>
          <p className="centro recuperacao-para">
            Senha nova para o{' '}
            <b>
              Bloco {estado.unidade.bloco}, apartamento {estado.unidade.apartamento}
            </b>
            .
          </p>
          {erro && (
            <CaixaDeErro vez={erro.vez} focar={erro.campo ? `${PREFIXO}-${erro.campo}` : undefined}>
              <p>{erro.mensagem}</p>
            </CaixaDeErro>
          )}
          <form onSubmit={aoEnviar} noValidate>
            <div className="lado">
              <div>
                <Campo
                  id={`${PREFIXO}-senha_nova`}
                  rotulo="Senha nova"
                  type="password"
                  autoComplete="new-password"
                  valor={senha}
                  aoMudar={setSenha}
                  ajuda={`${AJUDA_DA_SENHA} A família toda vai usar.`}
                  erro={erroDe('senha_nova')}
                />
              </div>
              <div>
                <Campo
                  id={`${PREFIXO}-senha_nova_repetida`}
                  rotulo="Repita a senha nova"
                  type="password"
                  autoComplete="new-password"
                  valor={repetida}
                  aoMudar={setRepetida}
                  erro={erroDe('senha_nova_repetida')}
                />
              </div>
            </div>
            <p className="ajuda">
              Ao salvar, este aparelho entra no Portal e os outros aparelhos da família saem.
              Eles entram de novo com a senha nova.
            </p>
            <button className="botao acesso-enviar" type="submit" disabled={enviando}>
              {enviando ? 'Salvando…' : 'Salvar senha nova'}
            </button>
          </form>
        </>
      )}
    </Tela>
  )
}
