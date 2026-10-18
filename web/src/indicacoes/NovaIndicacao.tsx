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
import { CamposDaOpiniao, MSG_ESCOLHA } from './FormOpiniao'
import { conferirPrestador, errosDaApi, type DadosDoPrestador, type ErrosDoPrestador } from './formulario'
import { PerguntaSairSemPublicar } from './SairSemPublicar'
import type { PrestadorRef } from './tipos'
import { useAtrasado } from './useAtrasado'
import './indicacoes.css'

const ESPERA_DOS_PARECIDOS_MS = 400
const MIN_LETRAS_PARECIDOS = 3
const VAZIO: DadosDoPrestador = { categoria: '', nome: '', telefone: '', instagram: '' }

export function PaginaNovaIndicacao() {
  const navegar = useNavigate()
  const [dados, setDados] = useState<DadosDoPrestador>(VAZIO)
  const [recomenda, setRecomenda] = useState<boolean | null>(null)
  const [comentario, setComentario] = useState('')
  const [erros, setErros] = useState<ErrosDoPrestador & { recomenda?: string; comentario?: string }>({})
  const [geral, setGeral] = useState('')
  const [ocupado, setOcupado] = useState(false)

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
    setGeral('')
    if (Object.values(novos).some(Boolean) || recomenda === null) return
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
          state: { recado: 'Esse telefone já está na lista. Dê a sua opinião aqui.' },
        })
        return
      }
      setErros({ ...errosDaApi(erro), comentario: erro.doCampo('comentario') })
      setGeral(erro.mensagem)
    } finally {
      setOcupado(false)
    }
  }

  const listaDeParecidos =
    procurar && achados.dados && achados.dados.itens.length > 0 ? (
      <div className="aviso-caixa atencao ind-parecidos" aria-live="polite">
        <Icone nome="info" />
        <div>
          {achados.dados.itens.map((p) => (
            <p key={p.id}>
              Já tem uma <strong>{p.nome}</strong> na lista. É a mesma?{' '}
              <Link className="texto-link" to={caminhoIndicacao(p.id, true)}>
                Dar minha opinião lá
              </Link>
            </p>
          ))}
        </div>
      </div>
    ) : null

  return (
    <Tela titulo="Indicar alguém" voltar={CAMINHO_INDICACOES}>
      <PerguntaSairSemPublicar blocker={blocker} />
      <form className="ind-nova" onSubmit={publicar} noValidate>
        <p className="ajuda">
          Indique um prestador que atendeu bem (ou mal) o seu apartamento. A sua opinião aparece com
          o bloco e o apartamento, nunca com o seu nome.
        </p>
        {geral && (
          <div className="aviso-caixa erro" role="alert">
            <Icone nome="alerta" />
            <p>{geral}</p>
          </div>
        )}
        <CamposDoPrestador
          id="nova"
          dados={dados}
          mudar={(campo, valor) => setDados((antes) => ({ ...antes, [campo]: valor }))}
          erros={erros}
          depoisDoNome={listaDeParecidos}
        />
        <CamposDaOpiniao
          id="nova"
          recomenda={recomenda}
          setRecomenda={setRecomenda}
          comentario={comentario}
          setComentario={setComentario}
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
