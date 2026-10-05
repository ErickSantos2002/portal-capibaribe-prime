// Épico B · Administração: o histórico (H-11) em frases, como no protótipo:
// "Bloco 1, 101 resetou o Bloco 1, 106". Pertence ao épico B.
import type { Papel } from '../api/tipos'
import { nomeDaUnidade } from '../casca/formatar'
import type { ItemHistorico } from './tipos'

const PAPEL_NA_FRASE: Record<Papel, string> = {
  admin: 'administrador',
  comissao: 'Comissão',
  sindico: 'síndico',
  conselho: 'conselho',
}

/** Quem fez: a unidade, ou "Portal" quando foi o próprio sistema (ex.: bloqueio automático). */
export function quemFez(item: ItemHistorico): string {
  return item.unidade ? nomeDaUnidade(item.unidade) : 'Portal'
}

/** A unidade afetada com a preposição certa: "o/ao/do Bloco 1, 106" ou "uma/a uma/de uma
 *  unidade" (quando o registro não aponta a unidade). */
function alvo(item: ItemHistorico, preposicao: '' | 'a' | 'de' = ''): string {
  if (!item.unidade_afetada) return `${preposicao ? `${preposicao} ` : ''}uma unidade`
  const artigo = { '': 'o', a: 'ao', de: 'do' }[preposicao]
  return `${artigo} ${nomeDaUnidade(item.unidade_afetada)}`
}

function aviso(item: ItemHistorico): string {
  return item.aviso_titulo ? `o aviso “${item.aviso_titulo}”` : 'um aviso'
}

function papel(item: ItemHistorico): string {
  const valor = item.detalhes.papel
  return typeof valor === 'string' && valor in PAPEL_NA_FRASE
    ? PAPEL_NA_FRASE[valor as Papel]
    : 'gestão'
}

function origem(item: ItemHistorico): string {
  switch (item.detalhes.origem) {
    case 'reset':
      return ', no reset'
    case 'promover_admin':
      return ', pelo comando de instalação'
    case 'migracao_0002':
      return ', na atualização do Portal'
    default:
      return ''
  }
}

/** O que foi feito, sem o sujeito: "resetou o Bloco 1, 106". */
export function oQueFez(item: ItemHistorico): string {
  switch (item.acao) {
    case 'primeiro_acesso':
      return 'entrou pela primeira vez'
    case 'unidade_bloqueada':
      return `bloqueou a entrada ${alvo(item, 'de')} por 15 minutos, depois de várias senhas erradas`
    case 'senha_trocada':
      return 'trocou a senha'
    case 'dados_apagados':
      return 'apagou os próprios dados'
    case 'aparelho_desconectado':
      return 'desconectou um aparelho'
    case 'unidade_resetada':
      return `resetou ${alvo(item)}`
    case 'papel_concedido':
      return `deu papel de ${papel(item)} ${alvo(item, 'a')}${origem(item)}`
    case 'papel_retirado':
      return `tirou o papel de ${papel(item)} ${alvo(item, 'de')}${origem(item)}`
    case 'aviso_publicado':
      return `publicou ${aviso(item)}`
    case 'aviso_corrigido': {
      const versao = item.detalhes.versao
      return `corrigiu ${aviso(item)}${typeof versao === 'number' ? ` (versão ${versao})` : ''}`
    }
    case 'aviso_arquivado':
      return `arquivou ${aviso(item)}`
    case 'aviso_fixado':
      return `fixou no topo ${aviso(item)}`
    case 'aviso_desafixado':
      return `tirou do topo ${aviso(item)}`
    case 'carga_inicial':
      return 'criou os blocos e as unidades'
    case 'dados_ficticios':
      return 'carregou os dados de exemplo'
    default:
      return item.acao.replaceAll('_', ' ')
  }
}
