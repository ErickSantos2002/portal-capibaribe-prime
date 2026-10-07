// Primeiro acesso (H-01): senha própria e contatos. A sessão é restrita até concluir.
import { startTransition, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { useSessao } from '../casca/contextoSessao'
import { Icone } from '../casca/Icone'
import { Placa } from '../casca/Placa'
import { Tela } from '../casca/Tela'
import { destinoDepoisDoPrimeiroAcesso } from '../notificacoes/ganchos'
import { concluirPrimeiroAcesso } from './api'
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
import { TextoDaPolitica } from './Privacidade'
import './acesso.css'

const PREFIXO = 'pa'

interface Erro {
  campo: string | null
  mensagem: string
  vez: number
}

export function PrimeiroAcesso() {
  const { eu, definir, sair } = useSessao()
  const navegar = useNavigate()
  const [senha, setSenha] = useState('')
  const [repetida, setRepetida] = useState('')
  const [contato, setContato] = useState<ContatoDigitado>({
    responsavel_nome: '',
    celular: '',
    email: '',
  })
  const [erro, setErro] = useState<Erro | null>(null)
  const [enviando, setEnviando] = useState(false)

  if (!eu) return null
  const { unidade } = eu

  function mostrarErro(campo: string | null, mensagem: string) {
    setErro((anterior) => ({ campo, mensagem, vez: (anterior?.vez ?? 0) + 1 }))
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault()
    const problema = validarSenhaNova(senha, repetida) ?? validarContato(contato)
    if (problema) return mostrarErro(problema.campo, problema.mensagem)
    setEnviando(true)
    try {
      const novo = await concluirPrimeiroAcesso({
        senha_nova: senha,
        senha_nova_repetida: repetida,
        ...contatoParaApi(contato),
      })
      // Na mesma transição: senão a guarda (sessão já liberada → /avisos) navega primeiro e o
      // recado se perde.
      startTransition(() => {
        definir(novo)
        // M2: a oferta "Receber os avisos" diz que ativou no próprio texto (o recado flutuante
        // cobria a pergunta dela); o mural continua com o recado.
        const destino = destinoDepoisDoPrimeiroAcesso()
        navegar(destino, {
          replace: true,
          state:
            destino === '/avisos'
              ? { recado: 'Pronto! O apartamento está ativado.' }
              : { ativado: true },
        })
      })
    } catch (falha) {
      setEnviando(false)
      const { campo, mensagem } = erroDaFalha(falha)
      mostrarErro(campo, mensagem)
    }
  }

  async function naoEMeu() {
    try {
      await sair()
      navegar('/entrar', { replace: true })
    } catch (falha) {
      mostrarErro(null, erroDaFalha(falha).mensagem)
    }
  }

  const erroDe = (campo: string) => (erro?.campo === campo ? erro.mensagem : undefined)

  return (
    <Tela titulo="Primeiro acesso">
      <div className="centro">
        <Placa unidade={unidade} grande decorativa />
      </div>
      <div className="aviso-caixa atencao">
        <Icone nome="alerta" />
        <p>
          Esta conta é da família do{' '}
          <b>
            Bloco {unidade.bloco}, apartamento {unidade.apartamento}
          </b>
          . Se você não é desta unidade, não continue. A conta é da família que mora ou vai morar
          aqui.
        </p>
      </div>
      <button type="button" className="botao leve" onClick={() => void naoEMeu()}>
        Não é o meu apartamento, voltar
      </button>
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
        <CamposDeContato prefixo={PREFIXO} contato={contato} aoMudar={setContato} erro={erro} />
        {/* U8: a política vem antes do botão, para ler antes de aceitar. */}
        <p className="ajuda">
          Guardamos só nome, celular e e-mail, para os fins da política de privacidade. Dá para
          corrigir ou apagar depois, em Minha unidade.
        </p>
        <details className="acesso-politica-dobrada">
          <summary className="texto-link">Ler a política de privacidade</summary>
          <TextoDaPolitica />
        </details>
        <button className="botao acesso-enviar" type="submit" disabled={enviando}>
          {enviando ? 'Salvando…' : 'Salvar e entrar'}
        </button>
      </form>
    </Tela>
  )
}
