# ADR-0005 · Login por unidade com senha própria e sessão em cookie

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 02/10/2026 |

## Contexto
Decisão do autor (02/10/2026): uma conta por unidade, login = bloco + apartamento (`1101`),
senha inicial `mudar123` igual para todos, troca obrigatória no primeiro acesso. Nenhum serviço
de autenticação pronto tem esse modelo, e todos pedem e-mail, que aqui é opcional.

## Decisão
- **Senha:** hash Argon2id (`argon2-cffi`, parâmetros padrão da biblioteca).
- **Sessão:** token aleatório de 32 bytes num cookie `HttpOnly`, `Secure`, `SameSite=Lax`.
  O banco guarda só o hash (SHA-256) do token. Validade de **180 dias**, renovada a cada uso,
  para a Dona Socorro não precisar entrar de novo.
- **Sessão restrita** no primeiro acesso: enquanto `precisa_trocar_senha = true`, a sessão só
  pode concluir o primeiro acesso.
- **CSRF:** além do `SameSite=Lax`, toda requisição que altera dados exige o cabeçalho
  `X-Portal: 1`, que um site de terceiros não consegue mandar sem CORS.
- **Limite por IP:** a única regra de limite do firewall da Vercel (plano Hobby) fica no
  `POST /api/acesso/entrar`: **20 requisições por IP a cada 10 minutos**. Bloqueio por unidade
  (5 erros, 15 min) fica no banco.
  Desde o M2 (06/10/2026) a mesma regra cobre também o `POST /api/acesso/recuperacao` ("esqueci
  a senha"), protegendo a cota diária do Gmail: as duas rotas dividem o contador de 20, porque o
  Hobby só permite uma regra de limite.
- **Recuperação:** link por e-mail com token de uso único, válido por 1 hora; sem e-mail, o
  administrador reseta.

## Consequências
- Controle total do fluxo, que é simples e coberto por testes.
- Risco aceito pelo autor: quem conhece o padrão pode ativar a conta de uma unidade antes do
  dono. O limite por IP impede que isso aconteça em massa; o painel de ativação e o reset
  resolvem os casos isolados.
- Escrever autenticação própria exige cuidado: os testes cobrem bloqueio, sessão restrita,
  expiração e CSRF.

## Alternativas consideradas
- **Auth pronta (Supabase Auth, Clerk, Auth0):** pensada para uma pessoa por e-mail; não
  encaixa em conta compartilhada por unidade nem em senha padrão.
- **Link mágico por e-mail (sem senha):** descartado junto com a obrigatoriedade de e-mail.
