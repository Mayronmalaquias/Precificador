"""Envio Gmail OAuth separado dos tokens de Drive/Visitas."""
import base64
import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request, AuthorizedSession

SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/userinfo.email"]
DEFAULT_FROM = "inteligencia.61imoveis@gmail.com"
BASE = Path(__file__).resolve().parents[2]

def token_path():
    return Path(os.getenv("SOLICITACOES_GMAIL_TOKEN") or BASE / "app/utils/asserts/gmail_solicitacoes_token.json")

def validar_conta(creds, expected):
    r = AuthorizedSession(creds).get("https://www.googleapis.com/oauth2/v2/userinfo", timeout=20)
    if not r.ok:
        raise RuntimeError("Não foi possível confirmar a conta Google autorizada.")
    d = r.json()
    if not d.get("verified_email") or str(d.get("email", "")).lower() != expected.lower():
        raise RuntimeError("A conta Google autorizada não corresponde ao remetente das solicitações.")

def credenciais():
    if not token_path().is_file():
        raise RuntimeError("Autorize o Gmail executando python autorizar_gmail_solicitacoes.py no backend.")
    c = Credentials.from_authorized_user_file(str(token_path()))
    if not c.has_scopes(SCOPES):
        raise RuntimeError("O token Google ainda não possui permissão de envio Gmail. Reautorize as solicitações.")
    if not c.valid:
        c.refresh(Request())
    validar_conta(c, os.getenv("SOLICITACOES_EMAIL_FROM") or DEFAULT_FROM)
    return c

def enviar(msg):
    c = credenciais()
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    # Sem retries de POST: resposta perdida pode significar mensagem já enviada.
    r = AuthorizedSession(c, max_refresh_attempts=0).post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send", json={"raw": raw}, timeout=45)
    if not r.ok:
        raise RuntimeError("Gmail retornou HTTP " + str(r.status_code) + ". Confira o envio antes de tentar novamente.")
    if not r.json().get("id"):
        raise RuntimeError("Gmail não confirmou o identificador da mensagem.")
