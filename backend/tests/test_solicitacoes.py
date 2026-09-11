from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from werkzeug.datastructures import FileStorage
from app.models.usuarios import Usuarios
from app.models.solicitacao import Solicitacao, SolicitacaoAnexo, SolicitacaoEvento
from app.services import solicitacao_service as svc
from app.services import solicitacao_worker as worker

@pytest.fixture(autouse=True)
def provider_isolado(monkeypatch):
    monkeypatch.setenv("SOLICITACOES_EMAIL_PROVIDER", "smtp")

@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    for table in (Usuarios.__table__, Solicitacao.__table__, SolicitacaoAnexo.__table__, SolicitacaoEvento.__table__):
        table.create(engine)
    with Session(engine) as s:
        yield s

def user(id=1, permissao="assistente"):
    return Usuarios(id=id, username="u"+str(id), email="u"+str(id)+"@example.org", permissao=permissao, ativo=True, desligado=False)

def dados():
    return dict(tipo="Ônus", tipo_onus="Real", endereco="Rua 1", finalidade="Venda", equipe="AGEF", oficio="1", matricula="123")

def item(session):
    u = user(); session.add(u); session.commit()
    return svc.criar(session, u, dados(), [], "12345678-1234-1234")

def test_criacao_idempotente_e_email_do_cadastro(session):
    i = item(session)
    d = dados(); d["email"] = "outro@example.org"
    repetido = svc.criar(session, session.get(Usuarios, 1), d, [], "12345678-1234-1234")
    assert repetido.id == i.id
    assert repetido.email == "u1@example.org"
    assert session.query(Solicitacao).count() == 1

def test_escopo_usuario_e_administrativo(session):
    i = item(session)
    outro = user(2); session.add(outro); session.commit()
    assert svc.escopo(session, outro).count() == 0
    assert svc.escopo(session, user(3, "administrador")).first().id == i.id
    assert not svc.autorizado(user(4, "corretor"))
    outro.ativo = False
    assert not svc.autorizado(outro)

@pytest.mark.parametrize("alteracao", [{"oficio": "10"}, {"finalidade": "Assertiva"}, {"matricula": ""}, {"equipe": "INVENTADA"}, {"tipo": "Outro"}])
def test_validacao_onus(alteracao):
    d = dados(); d.update(alteracao)
    with pytest.raises(ValueError): svc.validar(d, [])

def test_copia_cqc_e_corretor():
    d = dados(); d.update(tipo_onus="Cópia", finalidade="Captação (Apenas para o CQC)", corretor="Nome")
    with pytest.raises(ValueError): svc.validar(d, [])
    d["equipe"] = "Controle de Qualidade"
    assert svc.validar(d, [])[0]["corretor"] == "Nome"
    d["corretor"] = ""
    with pytest.raises(ValueError): svc.validar(d, [])

def test_anexos_obrigatorios_e_validacao_conteudo():
    with pytest.raises(ValueError): svc.validar(dict(tipo="Troca de Titularidade", endereco="Rua"), [])
    with pytest.raises(ValueError): svc.validar(dict(tipo="Celer", codigo_imovel="1", equipe="AGEF"), [FileStorage(stream=BytesIO(b"<script>"), filename="foto.png")])
    foto = FileStorage(stream=BytesIO(bytes.fromhex("89504e470d0a1a0a")+b"image"), filename="foto.png")
    assert svc.validar(dict(tipo="Celer", codigo_imovel="1", equipe="AGEF"), [foto])[1][0][1] == "image/png"

def pronto(session):
    from datetime import datetime
    i = item(session); i.trello_id = "card1"; i.integrado_em = datetime.utcnow(); i.status = "em_atendimento"; session.commit()
    t = Mock()
    def call(method, path, **kw):
        if method == "PUT": raise RuntimeError("Falha ao mover")
        if path.endswith("attachments"): return []
        if path.startswith("lists/"): return {"name": "Enviar"}
        return {"idList": worker.ENVIAR, "desc": "Resultado"}
    t.call.side_effect = call
    return i, t

def test_email_confirmado_nao_repete_se_mover_falhar(session, monkeypatch):
    monkeypatch.setenv("SOLICITACOES_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SOLICITACOES_SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("SOLICITACOES_EMAIL_FROM", "61@example.org")
    i, t = pronto(session)
    with patch.object(worker, "enviar_email") as send:
        with pytest.raises(RuntimeError): worker.processar(session, i, t)
        assert i.enviado_em and i.status == "enviado_pendente_trello"
        with pytest.raises(RuntimeError): worker.processar(session, i, t)
        send.assert_called_once()

def test_falha_smtp_ambigua_nao_reenvia(session, monkeypatch):
    monkeypatch.setenv("SOLICITACOES_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SOLICITACOES_SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("SOLICITACOES_EMAIL_FROM", "61@example.org")
    i, t = pronto(session)
    with patch.object(worker, "enviar_email", side_effect=TimeoutError) as send:
        with pytest.raises(TimeoutError): worker.processar(session, i, t)
        assert i.status == "envio_incerto" and not i.enviado_em
        worker.processar(session, i, t)
        send.assert_called_once()

def test_envio_desativado_nao_envia(session, monkeypatch):
    monkeypatch.setenv("SOLICITACOES_EMAIL_ENABLED", "false")
    i, t = pronto(session)
    with patch.object(worker, "enviar_email") as send:
        worker.processar(session, i, t)
        send.assert_not_called()
        assert i.status == "pronto" and i.concluido_em

def test_criacao_ambigua_reconcilia_sem_duplicar(session):
    i = item(session); i.status = "criacao_incerta"; session.commit()
    t = Mock(); t.call.return_value = []
    with pytest.raises(RuntimeError): worker.integrar(session, i, t)
    assert all(c.args[0] == "GET" for c in t.call.call_args_list)
    t.call.side_effect = [[{"id":"card1", "desc": "[61-SOL-1]", "shortUrl":"https://trello.com/c/x"}], {}, []]
    worker.integrar(session, i, t)
    assert i.trello_id == "card1" and i.integrado_em
    assert not any(c.args[:2] == ("POST", "cards") for c in t.call.call_args_list)


def test_rotas_jwt_escopo_e_download(session):
    from flask import Flask
    from flask_restx import Api
    from app.routes import solicitacao_routes as routes
    from app.utils.auth_middleware import gerar_jwt
    i = item(session)
    session.add(user(2)); session.commit()
    app = Flask(__name__)
    app.config.update(TESTING=True, JWT_SECRET="test-only-secret", JWT_ALGORITHM="HS256", JWT_EXPIRES_SECONDS=3600)
    Api(app).add_namespace(routes.solicitacao_ns, path="/api/v1")
    with app.app_context():
        token = gerar_jwt("u2", {"username": "u2", "permissao": "administrador"})
    # A permissão do JWT não substitui a permissão atual do cadastro.
    headers = {"Authorization": "Bearer "+token}
    with patch.object(routes, "SessionLocal", return_value=session):
        client = app.test_client()
        assert client.get("/api/v1/solicitacoes", headers={"X-API-KEY":"shared"}).status_code == 401
        response = client.get("/api/v1/solicitacoes?usuario_id=1", headers=headers)
        assert response.status_code == 200 and response.json["total"] == 0
        assert client.get("/api/v1/solicitacoes/1", headers=headers).status_code == 404
        assert client.get("/api/v1/solicitacoes/1/anexos/1", headers=headers).status_code == 404
        session.get(Usuarios, 2).ativo = False; session.commit()
        assert client.get("/api/v1/solicitacoes", headers=headers).status_code == 403


def test_gmail_envia_sem_smtp_e_sem_retry(monkeypatch):
    from email.message import EmailMessage
    from app.services import solicitacao_gmail as gmail
    msg = EmailMessage(); msg["From"] = gmail.DEFAULT_FROM; msg["To"] = "teste@example.org"; msg.set_content("Teste")
    http = Mock(); http.post.return_value.ok = True; http.post.return_value.json.return_value = {"id":"123"}
    with patch.object(gmail, "credenciais", return_value=Mock()), patch.object(gmail, "AuthorizedSession", return_value=http) as factory:
        gmail.enviar(msg)
        assert factory.call_args.kwargs["max_refresh_attempts"] == 0
        assert http.post.call_count == 1
        assert "raw" in http.post.call_args.kwargs["json"]

def test_gmail_recusa_conta_diferente():
    from app.services import solicitacao_gmail as gmail
    http = Mock(); http.get.return_value.ok = True
    http.get.return_value.json.return_value = {"email":"outra@gmail.com", "verified_email":True}
    with patch.object(gmail, "AuthorizedSession", return_value=http):
        with pytest.raises(RuntimeError, match="não corresponde"):
            gmail.validar_conta(Mock(), gmail.DEFAULT_FROM)

def test_token_gmail_ausente_nao_marca_envio_incerto(session, monkeypatch):
    from app.services import solicitacao_gmail as gmail
    monkeypatch.setenv("SOLICITACOES_EMAIL_PROVIDER", "gmail")
    monkeypatch.setenv("SOLICITACOES_EMAIL_ENABLED", "true")
    i, t = pronto(session)
    with patch.object(gmail, "credenciais", side_effect=RuntimeError("Autorize Gmail")), patch.object(worker, "enviar_email") as send:
        with pytest.raises(RuntimeError, match="Autorize"):
            worker.processar(session, i, t)
        assert i.status == "pronto" and not i.enviado_em
        send.assert_not_called()


@pytest.mark.parametrize("completo", [True, False])
def test_autorizacao_google_confere_escopos_retornados(tmp_path, completo):
    import autorizar_gmail_solicitacoes as auth
    warning = Warning("Scope has changed")
    warning.token = {"access_token": "fake-test", "scope": "test"}
    warning.new_scope = auth.SCOPES + ["openid"] if completo else [auth.SCOPES[1]]
    flow = Mock()
    flow.run_local_server.side_effect = warning
    flow.credentials.refresh_token = "fake-test"
    flow.credentials.has_scopes.return_value = True
    flow.credentials.to_json.return_value = '{"test": true}'
    destino = tmp_path / "test-token.json"
    with patch.object(auth.InstalledAppFlow, "from_client_secrets_file", return_value=flow), patch.object(auth, "validar_conta") as validar, patch.object(auth, "token_path", return_value=destino):
        if completo:
            auth.main()
            assert destino.exists()
            validar.assert_called_once()
        else:
            with pytest.raises(RuntimeError, match="não concedeu"):
                auth.main()
            assert not destino.exists()
            validar.assert_not_called()


@pytest.mark.parametrize("corporativo", [None, "invalido"])
def test_cadastrar_email_proprio_e_usar_no_pedido(session, corporativo):
    from flask import Flask
    from flask_restx import Api
    from app.routes import solicitacao_routes as routes
    from app.utils.auth_middleware import gerar_jwt
    u = user(); u.email = None; u.email_corporativo = corporativo
    outro = user(2)
    session.add_all([u, outro]); session.commit()
    app = Flask(__name__)
    app.config.update(TESTING=True, JWT_SECRET="test-only-secret", JWT_ALGORITHM="HS256", JWT_EXPIRES_SECONDS=3600)
    Api(app).add_namespace(routes.solicitacao_ns, path="/api/v1")
    with app.app_context():
        token = gerar_jwt("u1", {"username":"u1"})
    h = {"Authorization":"Bearer "+token}
    with patch.object(routes, "SessionLocal", return_value=session):
        c = app.test_client()
        assert c.get("/api/v1/solicitacoes", headers=h).json["precisa_email"]
        assert c.put("/api/v1/solicitacoes/meu-email", json={"email":"novo@example.org"}).status_code == 401
        for email in [None, [], "errado", "a"*256+"@example.org", "a@example.org\r\nBcc: b@example.org"]:
            assert c.put("/api/v1/solicitacoes/meu-email", headers=h, json={"email":email}).status_code == 400
        r = c.put("/api/v1/solicitacoes/meu-email", headers=h, json={"email":" novo@example.org ", "usuario_id":2})
        assert r.status_code == 200 and r.json == {"email":"novo@example.org", "precisa_email":False}
        assert session.get(Usuarios, 2).email == "u2@example.org"
        assert not c.get("/api/v1/solicitacoes", headers=h).json["precisa_email"]
        d = dados(); d["chave_cliente"] = "email-test-12345678"
        r = c.post("/api/v1/solicitacoes", headers=h, data=d)
        assert r.status_code == 201 and r.json["email"] == "novo@example.org"
        assert c.put("/api/v1/solicitacoes/meu-email", headers=h, json={"email":"outra@example.org"}).status_code == 409
