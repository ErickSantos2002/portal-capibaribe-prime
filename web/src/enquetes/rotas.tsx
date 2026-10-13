// M4 · Junta as rotas dos dois épicos das enquetes (spec do M4, seção 4). Comum: cada épico
// mexe só no próprio `rotas.tsx` (`votar/` do B, `gestao/` do A). As da gestão vêm primeiro
// porque `/enquetes/nova` não pode cair em `/enquetes/:id`.
import type { RouteObject } from 'react-router'
import { rotasGestaoEnquetes } from './gestao/rotas'
import { rotasVotar } from './votar/rotas'

export const rotasEnquetes: RouteObject[] = [...rotasGestaoEnquetes, ...rotasVotar]
