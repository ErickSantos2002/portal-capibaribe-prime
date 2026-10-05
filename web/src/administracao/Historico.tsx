// H-11 · Histórico de ações (como `telaHistorico` do protótipo). Pertence ao épico B.
// Mais novo primeiro; "Carregar mais" pede a página seguinte com `antes_de = proximo`.
import { useEffect, useState } from 'react'
import { ErroDaApi } from '../api/cliente'
import { Tela } from '../casca/Tela'
import { formatarDataEHora } from '../casca/formatar'
import './administracao.css'
import { buscarHistorico } from './api'
import { oQueFez, quemFez } from './frases'
import type { ItemHistorico } from './tipos'

function mensagemDe(erro: unknown): string {
  return erro instanceof ErroDaApi ? erro.mensagem : 'Não deu para abrir o histórico.'
}

export function Historico() {
  const [itens, setItens] = useState<ItemHistorico[]>([])
  const [proximo, setProximo] = useState<number | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')

  useEffect(() => {
    let vale = true
    buscarHistorico().then(
      (pagina) => {
        if (!vale) return
        setItens(pagina.itens)
        setProximo(pagina.proximo)
        setCarregando(false)
      },
      (falha: unknown) => {
        if (!vale) return
        setErro(mensagemDe(falha))
        setCarregando(false)
      },
    )
    return () => {
      vale = false
    }
  }, [])

  async function carregarMais() {
    if (proximo === null) return
    setCarregando(true)
    setErro('')
    try {
      const pagina = await buscarHistorico({ antes_de: proximo })
      setItens((anteriores) => [...anteriores, ...pagina.itens])
      setProximo(pagina.proximo)
    } catch (falha) {
      setErro(mensagemDe(falha))
    } finally {
      setCarregando(false)
    }
  }

  return (
    <Tela titulo="Histórico" voltar="/unidades">
      <p className="suave">Só o administrador vê. Ninguém consegue apagar.</p>
      {itens.length > 0 && (
        <div className="folha historico">
          {itens.map((item) => (
            <div key={item.id} className="item">
              <h3>
                <b>{quemFez(item)}</b> {oQueFez(item)}
              </h3>
              <span className="linha-meta">
                <time dateTime={item.ocorrido_em}>{formatarDataEHora(item.ocorrido_em)}</time>
              </span>
            </div>
          ))}
        </div>
      )}
      {!carregando && !erro && itens.length === 0 && (
        <p className="vazio">Nenhuma ação registrada ainda.</p>
      )}
      {erro && (
        <div className="aviso-caixa erro" role="alert">
          <p>{erro}</p>
        </div>
      )}
      {carregando && (
        <p className="vazio" role="status">
          Abrindo o histórico…
        </p>
      )}
      {!carregando && proximo !== null && (
        <button type="button" className="botao leve carregar-mais" onClick={carregarMais}>
          Carregar mais
        </button>
      )}
    </Tela>
  )
}
