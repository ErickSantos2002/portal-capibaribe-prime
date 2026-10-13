"""Comum · Envio de arquivo (spec do M3, seção 5.1). Arquivo comum: pronto desde o contrato.

- `POST /api/arquivos`                      → 201 `EnvioAutorizado` (`Gestao`): a URL para o
  navegador mandar o arquivo direto ao bucket (10 minutos)
- `POST /api/arquivos/{arquivo_id}/confirmar` → `ArquivoEnviado` (`Gestao`, só quem pediu): o
  servidor confere tamanho e conteúdo; recusado (422 `arquivo_recusado`) é apagado

503 `arquivos_desligados` sem a configuração do bucket; 503 `armazenamento_indisponivel` se o
bucket falhar na confirmação (o arquivo continua pendente). Regras em `app/servicos/arquivos.py`.
"""

from fastapi import APIRouter, Depends

from app.esquemas.arquivos import ArquivoEnviado, EnvioAutorizado, PedirEnvio
from app.esquemas.comum import IdBanco
from app.seguranca.dependencias import Banco, Gestao, exige_cabecalho_portal
from app.servicos import arquivos as servico
from app.servicos.armazenamento import Armazenado

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/arquivos", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.post("", status_code=201)
def pedir(dados: PedirEnvio, logado: Gestao, db: Banco, bucket: Armazenado) -> EnvioAutorizado:
    return servico.pedir_envio(db, logado, dados, bucket)


@rotas.post("/{arquivo_id}/confirmar")
def confirmar(arquivo_id: IdBanco, logado: Gestao, db: Banco, bucket: Armazenado) -> ArquivoEnviado:
    return servico.confirmar_envio(db, logado, arquivo_id, bucket)
