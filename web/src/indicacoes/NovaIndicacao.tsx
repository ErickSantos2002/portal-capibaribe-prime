// Indicações · indicar alguém (spec, seção 3.3): o prestador e a primeira opinião, publicados
// juntos. Enquanto a pessoa digita o nome, o Portal mostra os nomes parecidos que já estão na
// lista ("É a mesma? Dar minha opinião lá"). Telefone que já está na lista: a API recusa (409) e
// a tela leva para o prestador, com o formulário de opinião aberto.
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { comoErroDaApi, useCarga } from '../avisos/carregar'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { useAvisarAoSair } from '../enquetes/gestao/useAvisarAoSair'
import { indicar, parecidos } from './api'
import { CAMINHO_INDICACOES, caminhoIndicacao } from './caminhos'
import { CamposDoPrestador } from './CorrigirPrestador'
import { CamposDaOpiniao, ErroGeral, MSG_ESCOLHA } from './FormOpiniao'
import {
  conferirPrestador,
  errosDaApi,
  MSG_CONFIRA,
  type DadosDoPrestador,
  type ErrosDoPrestador,
  type RascunhoDaOpiniao,
} from './formulario'
import { PerguntaSairSemPublicar } from './SairSemPublicar'
import type { PrestadorRef } from './tipos'
import { useAtrasado } from './useAtrasado'
import './indicacoes.css'

const ESPERA_DOS_PARECIDOS_MS = 400
const MIN_LETRAS_PARECIDOS = 3
const VAZIO: DadosDoPrestador = { categoria: '', nome: '', telefone: '', instagram: '' }

type Erros = ErrosDoPrestador & { recomenda?: string; comentario?: string }

export function PaginaNovaIndicacao() {
  const navegar = useNavigate()
  const [dados, setDados] = useState<DadosDoPrestador>(VAZIO)
  const [recomenda, setRecomenda] = useState<boolean | null>(null)
  const [comentario, setComentario] = useState('')
  const [erros, setErros] = useState<Erros>({})
  const [geral, setGeral] = useState('')
  const [ocupado, setOcupado] = useState(false)
  // O que já foi escrito da opinião vai junto para o prestador que já estava na lista.
  const rascunho: RascunhoDaOpiniao = { recomenda, comentario }

  /** Mexeu no campo: o erro dele some, e o do topo também quando ele vinha dos campos e não
   *  sobra nenhum (como em `enquetes/gestao/Formulario.tsx`). */
  function limparErro(campo: keyof Erros) {
    if (!erros[campo]) return
    const resto = { ...erros, [campo]: undefined }
    setErros(resto)
    const doCampo = geral === MSG_CONFIRA || geral === erros[campo]
    if (doCampo && !Object.values(resto).some(Boolean)) setGeral('')
  }

  const sujo =
    Object.values(dados).some((v) => v.trim() !== '') || recomenda !== null || comentario.trim() !== ''
  const { blocker, liberar } = useAvisarAoSair(sujo)

  const nome = useAtrasado(dados.nome.trim(), ESPERA_DOS_PARECIDOS_MS)
  const procurar = nome.length >= MIN_LETRAS_PARECIDOS
  const [achados] = useCarga(
    () => (procurar ? parecidos(nome) : Promise.resolve({ itens: [] as PrestadorRef[] })),
    [procurar ? nome : ''],
  )

  async function publicar(evento: FormEvent) {
    evento.preventDefault()
    const novos = {
      ...conferirPrestador(dados),
      recomenda: recomenda === null ? MSG_ESCOLHA : undefined,
    }
    setErros(novos)
    const mensagens = Object.values(novos).filter(Boolean) as string[]
    // Erro de campo: a caixa do topo leva o foco e diz o que fazer (o erro de baixo da tela
    // não aparecia para quem tocou em Publicar).
    setGeral(mensagens.length === 0 ? '' : mensagens.length === 1 ? mensagens[0] : MSG_CONFIRA)
    if (mensagens.length > 0 || recomenda === null) return
    setOcupado(true)
    try {
      const { id } = await indicar({
        categoria_id: Number(dados.categoria),
        nome: dados.nome,
        telefone: dados.telefone,
        instagram: dados.instagram.trim() ? dados.instagram : null,
        recomenda,
        comentario: comentario.trim() ? comentario : null,
      })
      liberar()
      navegar(caminhoIndicacao(id), {
        replace: true,
        state: { recado: 'Indicação publicada. Obrigado!' },
      })
    } catch (e) {
      const erro = comoErroDaApi(e)
      const outro = erro.extras.id
      if (erro.codigo === 'prestador_ja_existe' && typeof outro === 'number') {
        liberar()
        navegar(caminhoIndicacao(outro, true), {
          replace: true,
          state: { recado: 'Esse telefone já está na lista. Dê a sua opinião aqui.', opiniao: rascunho },
        })
        return
      }
      const daApi = { ...errosDaApi(erro), comentario: erro.doCampo('comentario') }
      setErros(daApi)
      const deCampo = Object.values(daApi).filter(Boolean) as string[]
      setGeral(deCampo.length === 1 ? deCampo[0] : deCampo.length > 1 ? MSG_CONFIRA : erro.mensagem)
    } finally {
      setOcupado(false)
    }
  }

  const itensParecidos = procurar ? (achados.dados?.itens ?? []) : []
  // O contêiner do aviso fica sempre montado e só o conteúdo muda: região `aria-live` que
  // nasce junto com o texto pode não ser lida.
  const listaDeParecidos = (
    <div aria-live="polite">
      {itensParecidos.length > 0 && (
        <div className="aviso-caixa atencao ind-parecidos">
          <Icone nome="info" />
          <div>
            {itensParecidos.map((p) => (
              <p key={p.id}>
                Já tem “{p.nome}” na lista. É o mesmo prestador?{' '}
                <Link
                  className="texto-link"
                  to={caminhoIndicacao(p.id, true)}
                  state={{ opiniao: rascunho }}
                >
                  Dar minha opinião lá
                </Link>
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  return (
    <Tela titulo="Indicar alguém" voltar={CAMINHO_INDICACOES}>
      <PerguntaSairSemPublicar blocker={blocker} />
      <form className="ind-nova" onSubmit={publicar} noValidate>
        <p className="ajuda">
          Indique um prestador que atendeu bem (ou mal) o seu apartamento. A sua opinião aparece com
          o bloco e o apartamento, nunca com o seu nome.
        </p>
        {geral && <ErroGeral mensagem={geral} />}
        <CamposDoPrestador
          id="nova"
          dados={dados}
          mudar={(campo, valor) => {
            setDados((antes) => ({ ...antes, [campo]: valor }))
            limparErro(campo)
          }}
          erros={erros}
          depoisDoNome={listaDeParecidos}
        />
        <CamposDaOpiniao
          id="nova"
          recomenda={recomenda}
          setRecomenda={(valor) => {
            setRecomenda(valor)
            limparErro('recomenda')
          }}
          comentario={comentario}
          setComentario={(valor) => {
            setComentario(valor)
            limparErro('comentario')
          }}
          erroRecomenda={erros.recomenda}
          erroComentario={erros.comentario}
        />
        <div className="ind-acoes">
          <button type="submit" className="botao" disabled={ocupado}>
            Publicar indicação
          </button>
        </div>
      </form>
    </Tela>
  )
}
