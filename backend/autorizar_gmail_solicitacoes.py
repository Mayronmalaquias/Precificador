"""Autoriza somente envio Gmail e identificação da conta, sem alterar o token de visitas."""
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
load_dotenv()
from app.services.solicitacao_gmail import BASE, SCOPES, DEFAULT_FROM, token_path, validar_conta

def main():
    expected = os.getenv("SOLICITACOES_EMAIL_FROM") or DEFAULT_FROM
    client = os.getenv("SOLICITACOES_GMAIL_CLIENT") or str(BASE / "app/utils/asserts/oauth.json")
    flow = InstalledAppFlow.from_client_secrets_file(client, SCOPES)
    try:
        creds = flow.run_local_server(host="localhost", port=0, timeout_seconds=300,
            login_hint=expected, prompt="consent", access_type="offline",
            authorization_prompt_message="Autorize o envio na janela do Google aberta no navegador.",
            success_message="Autorização recebida. Pode fechar esta janela.")
    except Warning as warning:
        # Google pode devolver escopos equivalentes/adicionais já concedidos.
        # OAuthlib inclui o token recebido no aviso; validar o grant efetivo.
        token = getattr(warning, "token", None)
        granted = set(getattr(warning, "new_scope", []) or [])
        if not token or not set(SCOPES).issubset(granted):
            raise RuntimeError("Google não concedeu a permissão de envio e identificação da conta.") from None
        flow.oauth2session.token = dict(token)
        flow.oauth2session.scope = list(granted)
        creds = flow.credentials
    validar_conta(creds, expected)
    if not creds.refresh_token or not creds.has_scopes(SCOPES):
        raise RuntimeError("A autorização não concedeu todas as permissões necessárias.")
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(creds.to_json(), encoding="utf-8")
    print("Gmail autorizado para " + expected + ". Nenhum e-mail foi enviado.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Autorização não concluída (" + type(e).__name__ + "). Verifique a conta, o consentimento e se a Gmail API está habilitada no projeto Google.")
        raise SystemExit(1)
