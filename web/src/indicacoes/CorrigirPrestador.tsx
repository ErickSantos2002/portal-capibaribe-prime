// Indicações · corrigir os dados do prestador (spec, seção 3.2): quem indicou, ou a gestão,
// corrige o nome, a categoria e os contatos. `CamposDoPrestador` é a mesma parte em "Indicar
// alguém" (seção 3.3), com os mesmos rótulos.
import { useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router'
import { comoErroDaApi, useCarga } from '../avisos/carregar'
import { useRecado } from '../casca/contextoRecado'
import { Icone } from '../casca/Icone'
import { corrigir, listarCategorias } from './api'
import { caminhoIndicacao } from './caminhos'
import { telefoneNaTela } from './formatos'
import {
  conferirPrestador,
  LIMITE_NOME,
  errosDaApi,
  type DadosDoPrestador,
  type ErrosDoPrestador,
} from './formulario'
import type { Prestador } from './tipos'

function ErroDoCampo({ id, mensagem }: { id: string; mensagem?: string }) {
  if (!mensagem) return null
  return (
    <p className="ind-erro-campo" id={id}>
      {mensagem}
    </p>
  )
}

interface PropsCampos {
  id: string
  dados: DadosDoPrestador
  mudar: (campo: keyof DadosDoPrestador, valor: string) => void
  erros: ErrosDoPrestador
  /** Debaixo do nome: o aviso de nome parecido, em "Indicar alguém". */
  depoisDoNome?: ReactNode
}

export function CamposDoPrestador({ id, dados, mudar, erros, depoisDoNome }: PropsCampos) {
  const [categorias, recarregar] = useCarga(() => listarCategorias(), [])
  const descrito = (campo: keyof DadosDoPrestador, ajuda?: string) =>
    [ajuda, erros[campo] && `${id}-${campo}-erro`].filter(Boolean).join(' ') || undefined
  return (
    <>
      <label htmlFor={`${id}-categoria`}>Que serviço?</label>
      {categorias.situacao === 'erro' && !categorias.dados ? (
        <div className="aviso-caixa erro" role="alert">
          <Icone nome="alerta" />
          <div>
            <p>{categorias.erro.mensagem}</p>
            <button type="button" className="texto-link" onClick={recarregar}>
              Tentar de novo
            </button>
          </div>
        </div>
      ) : (
        <select
          id={`${id}-categoria`}
          value={dados.categoria}
          onChange={(e) => mudar('categoria', e.target.value)}
          className={erros.categoria ? 'campo-erro' : undefined}
          aria-invalid={erros.categoria ? true : undefined}
          aria-describedby={descrito('categoria')}
        >
          <option value="">Escolha</option>
          {categorias.dados?.itens.map((c) => (
            <option key={c.id} value={String(c.id)}>
              {c.nome}
            </option>
          ))}
        </select>
      )}
      <ErroDoCampo id={`${id}-categoria-erro`} mensagem={erros.categoria} />

      <label htmlFor={`${id}-nome`}>Nome do prestador ou da empresa</label>
      <input
        id={`${id}-nome`}
        type="text"
        value={dados.nome}
        onChange={(e) => mudar('nome', e.target.value)}
        maxLength={LIMITE_NOME}
        autoComplete="off"
        className={erros.nome ? 'campo-erro' : undefined}
        aria-invalid={erros.nome ? true : undefined}
        aria-describedby={descrito('nome')}
      />
      <ErroDoCampo id={`${id}-nome-erro`} mensagem={erros.nome} />
      {depoisDoNome}

      <label htmlFor={`${id}-telefone`}>WhatsApp ou telefone</label>
      <input
        id={`${id}-telefone`}
        type="tel"
        inputMode="tel"
        value={dados.telefone}
        onChange={(e) => mudar('telefone', e.target.value)}
        maxLength={25}
        autoComplete="off"
        className={erros.telefone ? 'campo-erro' : undefined}
        aria-invalid={erros.telefone ? true : undefined}
        aria-describedby={descrito('telefone', `${id}-telefone-ajuda`)}
      />
      <p className="ajuda" id={`${id}-telefone-ajuda`}>
        Com DDD, por exemplo (81) 9 9999-0001.
      </p>
      <ErroDoCampo id={`${id}-telefone-erro`} mensagem={erros.telefone} />

      <label htmlFor={`${id}-instagram`}>Instagram (opcional)</label>
      <input
        id={`${id}-instagram`}
        type="text"
        value={dados.instagram}
        onChange={(e) => mudar('instagram', e.target.value)}
        maxLength={31}
        autoComplete="off"
        autoCapitalize="none"
        spellCheck={false}
        placeholder="@usuario"
        className={erros.instagram ? 'campo-erro' : undefined}
        aria-invalid={erros.instagram ? true : undefined}
        aria-describedby={descrito('instagram')}
      />
      <ErroDoCampo id={`${id}-instagram-erro`} mensagem={erros.instagram} />
    </>
  )
}

/** O erro de telefone repetido, com o link para o prestador que já tem o número. */
export function TelefoneRepetido({ mensagem, id }: { mensagem: string; id?: number }) {
  return (
    <div className="aviso-caixa erro" role="alert">
      <Icone nome="alerta" />
      <div>
        <p>{mensagem}</p>
        {id !== undefined && (
          <p>
            <Link className="texto-link" to={caminhoIndicacao(id)}>
              Abrir o prestador que já tem esse telefone
            </Link>
          </p>
        )}
      </div>
    </div>
  )
}

interface Props {
  prestador: Prestador
  aoCorrigir: (prestador: Prestador) => void
  aoCancelar: () => void
}

export function CorrigirPrestador({ prestador, aoCorrigir, aoCancelar }: Props) {
  const recado = useRecado()
  const [dados, setDados] = useState<DadosDoPrestador>({
    categoria: String(prestador.categoria.id),
    nome: prestador.nome,
    telefone: telefoneNaTela(prestador.telefone),
    instagram: prestador.instagram ? `@${prestador.instagram}` : '',
  })
  const [erros, setErros] = useState<ErrosDoPrestador>({})
  const [geral, setGeral] = useState<{ mensagem: string; id?: number } | null>(null)
  const [ocupado, setOcupado] = useState(false)

  async function salvar(evento: FormEvent) {
    evento.preventDefault()
    const achados = conferirPrestador(dados)
    setErros(achados)
    setGeral(null)
    if (Object.values(achados).some(Boolean)) return
    setOcupado(true)
    try {
      const corrigido = await corrigir(prestador.id, {
        categoria_id: Number(dados.categoria),
        nome: dados.nome,
        telefone: dados.telefone,
        instagram: dados.instagram.trim() ? dados.instagram : null,
      })
      recado('Os dados do prestador foram corrigidos.')
      aoCorrigir(corrigido)
    } catch (e) {
      const erro = comoErroDaApi(e)
      setErros(errosDaApi(erro))
      const outro = erro.extras.id
      setGeral({ mensagem: erro.mensagem, id: typeof outro === 'number' ? outro : undefined })
    } finally {
      setOcupado(false)
    }
  }

  return (
    <form className="ind-form-corrigir" onSubmit={salvar} noValidate>
      <h3>Corrigir os dados</h3>
      {geral && <TelefoneRepetido mensagem={geral.mensagem} id={geral.id} />}
      <CamposDoPrestador
        id="corrigir"
        dados={dados}
        mudar={(campo, valor) => setDados((antes) => ({ ...antes, [campo]: valor }))}
        erros={erros}
      />
      <div className="ind-acoes">
        <button type="submit" className="botao" disabled={ocupado}>
          Salvar as correções
        </button>
        <button type="button" className="botao leve" disabled={ocupado} onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}
