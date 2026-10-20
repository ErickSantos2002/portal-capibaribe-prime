// Indicações · as categorias (spec, seção 4): a administração acrescenta e renomeia. Apagar não
// existe. A nova entra no fim, antes de "Outros" (quem decide a ordem é a API).
import { useState, type FormEvent } from 'react'
import { comoErroDaApi, useCarga } from '../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../avisos/componentes'
import { useRecado } from '../casca/contextoRecado'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { criarCategoria, listarCategorias, renomearCategoria } from './api'
import type { CategoriaServico } from './tipos'
import './indicacoes.css'

const LIMITE_CATEGORIA = 40

/** De onde vêm as categorias: as indicações ou os classificados (a mesma tela, as mesmas regras). */
export interface OrigemDasCategorias {
  titulo: string
  explicacao: string
  listar: () => Promise<{ itens: CategoriaServico[] }>
  criar: (nome: string) => Promise<CategoriaServico>
  renomear: (id: number, nome: string) => Promise<CategoriaServico>
}

const DAS_INDICACOES: OrigemDasCategorias = {
  titulo: 'Categorias das indicações',
  explicacao:
    'As categorias aparecem na faixa da lista de indicações e no formulário de indicar alguém. Uma categoria nova entra antes de “Outros”. Categoria não é apagada.',
  listar: listarCategorias,
  criar: criarCategoria,
  renomear: renomearCategoria,
}

export function PaginaCategorias() {
  return <PaginaDeCategorias origem={DAS_INDICACOES} />
}

export function PaginaDeCategorias({ origem }: { origem: OrigemDasCategorias }) {
  const recado = useRecado()
  const [carga, recarregar] = useCarga(() => origem.listar(), [origem])
  const [nova, setNova] = useState('')
  const [erro, setErro] = useState('')
  const [ocupado, setOcupado] = useState(false)

  async function criar(evento: FormEvent) {
    evento.preventDefault()
    if (nova.trim().length < 2) {
      setErro('Escreva o nome da categoria, com pelo menos 2 letras.')
      return
    }
    setOcupado(true)
    setErro('')
    try {
      const criada = await origem.criar(nova)
      recado(`Categoria “${criada.nome}” criada.`)
      setNova('')
      recarregar()
    } catch (e) {
      const falha = comoErroDaApi(e)
      setErro(falha.doCampo('nome') ?? falha.mensagem)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <Tela titulo={origem.titulo} voltar="/unidades">
      <p className="ajuda">{origem.explicacao}</p>
      {carga.situacao === 'erro' && !carga.dados ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !carga.dados ? (
        <Carregando />
      ) : (
        <ul className="folha ind-categorias" aria-label="Categorias">
          {carga.dados.itens.map((c) => (
            <ItemCategoria
              key={c.id}
              categoria={c}
              recarregar={recarregar}
              renomear={origem.renomear}
            />
          ))}
        </ul>
      )}
      <form className="ind-nova-categoria" onSubmit={criar} noValidate>
        <label htmlFor="ind-categoria-nova">Categoria nova</label>
        <input
          id="ind-categoria-nova"
          type="text"
          value={nova}
          onChange={(e) => setNova(e.target.value)}
          maxLength={LIMITE_CATEGORIA}
          autoComplete="off"
          className={erro ? 'campo-erro' : undefined}
          aria-invalid={erro ? true : undefined}
          aria-describedby={erro ? 'ind-categoria-nova-erro' : undefined}
        />
        {erro && (
          <p className="ind-erro-campo" id="ind-categoria-nova-erro">
            {erro}
          </p>
        )}
        <button type="submit" className="botao" disabled={ocupado}>
          <Icone nome="mais" /> Criar categoria
        </button>
      </form>
    </Tela>
  )
}

interface PropsItem {
  categoria: CategoriaServico
  recarregar: () => void
  renomear: OrigemDasCategorias['renomear']
}

function ItemCategoria({ categoria, recarregar, renomear }: PropsItem) {
  const recado = useRecado()
  const [editando, setEditando] = useState(false)
  const [nome, setNome] = useState(categoria.nome)
  const [erro, setErro] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const id = `ind-renomear-${categoria.id}`

  async function salvar(evento: FormEvent) {
    evento.preventDefault()
    setOcupado(true)
    setErro('')
    try {
      const nova = await renomear(categoria.id, nome)
      recado(`Categoria renomeada para “${nova.nome}”.`)
      setEditando(false)
      recarregar()
    } catch (e) {
      const falha = comoErroDaApi(e)
      setErro(falha.doCampo('nome') ?? falha.mensagem)
    } finally {
      setOcupado(false)
    }
  }

  if (!editando) {
    return (
      <li className="ind-categoria-item">
        <span>{categoria.nome}</span>
        <button
          type="button"
          className="texto-link"
          aria-label={`Renomear ${categoria.nome}`}
          onClick={() => {
            setNome(categoria.nome)
            setEditando(true)
          }}
        >
          <Icone nome="editar" tamanho={20} /> Renomear
        </button>
      </li>
    )
  }
  return (
    <li className="ind-categoria-item editando">
      <form onSubmit={salvar} noValidate>
        <label htmlFor={id}>Novo nome de {categoria.nome}</label>
        <input
          id={id}
          type="text"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          maxLength={LIMITE_CATEGORIA}
          autoComplete="off"
          autoFocus
          className={erro ? 'campo-erro' : undefined}
          aria-invalid={erro ? true : undefined}
          aria-describedby={erro ? `${id}-erro` : undefined}
        />
        {erro && (
          <p className="ind-erro-campo" id={`${id}-erro`}>
            {erro}
          </p>
        )}
        <div className="ind-acoes">
          <button type="submit" className="botao" disabled={ocupado}>
            Salvar o nome
          </button>
          <button type="button" className="botao leve" disabled={ocupado} onClick={() => setEditando(false)}>
            Cancelar
          </button>
        </div>
      </form>
    </li>
  )
}
