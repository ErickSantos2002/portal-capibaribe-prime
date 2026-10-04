from fastapi.testclient import TestClient

from app.main import app


def test_rota_inexistente_responde_404():
    resposta = TestClient(app).get("/api/rota-que-nao-existe")
    assert resposta.status_code == 404


def test_documentacao_interativa_desligada():
    # O repositório é público, mas a API em produção não precisa exibir /docs.
    cliente = TestClient(app)
    assert cliente.get("/docs").status_code == 404
    assert cliente.get("/api/docs").status_code == 404
