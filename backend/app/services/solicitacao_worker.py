"""Integração Trello e entrega. Executado por um worker, nunca pelos workers HTTP."""
import os
import html
import ssl
import smtplib
from datetime import datetime
from email.message import EmailMessage
from urllib.parse import urlsplit
import requests
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import engine
from app.models.solicitacao import Solicitacao, SolicitacaoAnexo
from app.services.solicitacao_service import evento

BOARD = "66606ddb4ba4a004e29e4f60"
ENTRADA = "66606de4c6a473e8d9363cce"
JURIDICO = "669eaac0457f1e2d386e3be0"
ENVIAR = "66b5097b1c985cff12ceeebc"
ENVIADO = "66b50980554473525e1a8875"
EMAIL_FIELD = "66658555981fe7fad0e4a4e0"
LABELS = {"Ônus": "6663642c38e28c7144cc1ef0", "Parecer Jurídico": "666337cb4cb9f7dbedcad607", "Troca de Titularidade": "666367066ebbb80f495f7b26", "Celer": "68b85c264df89a705b347991", "Real": "66606ddc1dc51400eb69e63e", "Cópia": "6693d831ff0a0c133270126b"}

class Trello:
    def __init__(self):
        self.auth = {"key": os.getenv("TRELLO_SOLICITACOES_KEY") or os.getenv("TRELLO_KEY"), "token": os.getenv("TRELLO_SOLICITACOES_TOKEN") or os.getenv("TRELLO_TOKEN")}
        if not all(self.auth.values()):
            raise RuntimeError("Credenciais do Trello não configuradas.")

    def call(self, method, path, **kwargs):
        try:
            r = requests.request(method, "https://api.trello.com/1/"+path, params={**self.auth, **kwargs.pop("query", {})}, timeout=45, **kwargs)
        except requests.RequestException:
            raise RuntimeError("Falha de comunicação com o Trello.") from None
        if not r.ok:
            raise RuntimeError("Trello retornou HTTP " + str(r.status_code))
        return r.json()

def mudar(session, item, status, descricao):
    item.status = status
    evento(session, item, descricao)
    session.commit()

def integrar(session, item, trello):
    marker = "[61-SOL-"+str(item.id)+"]"
    if not item.trello_id:
        # Reconcilia uma criação cuja resposta pode ter se perdido.
        cards = trello.call("GET", "boards/"+BOARD+"/cards", query={"filter": "all", "fields": "id,desc,url,shortUrl"})
        encontrados = [c for c in cards if marker in c.get("desc", "")]
        if len(encontrados) > 1:
            raise RuntimeError("Mais de um cartão para o protocolo. Revisão administrativa necessária.")
        card = encontrados[0] if encontrados else None
        if not card:
            if item.status == "criacao_incerta":
                raise RuntimeError("Criação anterior sem confirmação. Verifique o Trello antes de criar novamente.")
            d = item.dados
            labels = [LABELS[item.tipo]]
            if item.tipo == "Ônus":
                labels.append(LABELS[d["tipo_onus"]])
            if item.tipo == "Parecer Jurídico" and d["possui_onus"] == "Não":
                labels.append("66606ddc1dc51400eb69e635")
            desc = marker + "\n" + "\n".join(k.replace("_", " ")+": "+v for k,v in d.items() if v)
            if d.get("codigo_imovel"):
                desc += "\nLink do imóvel: https://app.imoview.com.br/Imovel/Detalhes/"+d["codigo_imovel"]
            mudar(session, item, "criacao_incerta", "Iniciada criação do cartão no Trello.")
            card = trello.call("POST", "cards", data={"idList": JURIDICO if item.tipo == "Parecer Jurídico" else ENTRADA,
                "name": (d.get("endereco") or d.get("codigo_imovel"))+" - SOL-"+str(item.id).zfill(6),
                "desc": desc, "idLabels": ",".join(labels)})
        item.trello_id = card["id"]
        item.trello_url = card.get("shortUrl") or card.get("url")
        session.commit()
    trello.call("PUT", "cards/"+item.trello_id+"/customField/"+EMAIL_FIELD+"/item", json={"value": {"text": item.email}})
    attachments = trello.call("GET", "cards/"+item.trello_id+"/attachments")
    for a in session.query(SolicitacaoAnexo).filter_by(solicitacao_id=item.id):
        if a.trello_id:
            continue
        nome = "SOL-"+str(item.id)+"-ANEXO-"+str(a.id)+"-"+a.nome
        existente = next((x for x in attachments if x.get("name") == nome), None)
        enviado = existente or trello.call("POST", "cards/"+item.trello_id+"/attachments", data={"name": nome}, files={"file": (nome, a.conteudo, a.mime)})
        a.trello_id = enviado["id"]
        session.commit()
    item.integrado_em = item.integrado_em or datetime.utcnow()
    item.erro = None
    mudar(session, item, "em_atendimento", "Cartão e anexos registrados no Trello.")

def enviar_email(item):
    host = os.getenv("SOLICITACOES_SMTP_HOST", "")
    remetente = os.getenv("SOLICITACOES_EMAIL_FROM", "")
    provider = os.getenv("SOLICITACOES_EMAIL_PROVIDER", "smtp")
    if not remetente or (provider == "smtp" and not host):
        raise RuntimeError("Remetente/provedor das solicitações não configurado.")
    resultado = item.resultado or {}
    msg = EmailMessage()
    msg["Subject"] = "Solicitação SOL-"+str(item.id).zfill(6)+" finalizada"
    msg["From"] = remetente
    msg["To"] = item.email
    msg["Message-ID"] = "<solicitacao-"+str(item.id)+"@"+remetente.split("@")[-1]+">"
    links = [a for a in resultado.get("anexos", []) if urlsplit(a.get("url", "")).scheme == "https"]
    texto = resultado.get("descricao", "")
    msg.set_content("Sua solicitação foi concluída.\n"+texto+"\n"+"\n".join(a["url"] for a in links))
    lista = "".join('<li><a href="'+html.escape(a["url"], quote=True)+'">'+html.escape(a.get("nome") or "Anexo")+'</a></li>' for a in links)
    msg.add_alternative("<h2>Sua solicitação foi concluída!</h2><p>Protocolo SOL-"+str(item.id).zfill(6)+"</p><pre>"+html.escape(texto)+"</pre><ul>"+lista+"</ul><p>Atenciosamente, 61 Imóveis</p>", subtype="html")
    if provider == "gmail":
        from app.services.solicitacao_gmail import enviar
        enviar(msg)
        return
    if provider != "smtp":
        raise RuntimeError("Provedor de e-mail inválido.")
    mode = os.getenv("SOLICITACOES_SMTP_MODE", "starttls")
    if mode not in ("ssl", "starttls"):
        raise RuntimeError("SMTP requer ssl ou starttls.")
    cls = smtplib.SMTP_SSL if mode == "ssl" else smtplib.SMTP
    kwargs = {"context": ssl.create_default_context()} if mode == "ssl" else {}
    with cls(host, int(os.getenv("SOLICITACOES_SMTP_PORT", "465" if mode == "ssl" else "587")), timeout=45, **kwargs) as smtp:
        if mode == "starttls":
            smtp.starttls(context=ssl.create_default_context())
        user = os.getenv("SOLICITACOES_SMTP_USER")
        if user:
            smtp.login(user, os.getenv("SOLICITACOES_SMTP_PASSWORD", ""))
        recusados = smtp.send_message(msg)
        if recusados:
            raise RuntimeError("Destinatário recusado pelo SMTP.")

def processar(session, item, trello):
    if not item.integrado_em:
        integrar(session, item, trello)
    if item.enviado_em:
        # Se mover falhou, apenas tenta mover novamente. Nunca reenvia e-mail.
        trello.call("PUT", "cards/"+item.trello_id, data={"idList": ENVIADO})
        item.erro = None
        mudar(session, item, "enviado", "Cartão movido para Enviado.")
        return
    card = trello.call("GET", "cards/"+item.trello_id)
    lista = trello.call("GET", "lists/"+card["idList"])
    item.sincronizado_em = datetime.utcnow()
    if item.lista_nome != lista.get("name"):
        item.lista_nome = lista.get("name")
        evento(session, item, "Trello: "+(item.lista_nome or "lista atualizada"))
    session.commit()
    if item.status == "envio_incerto":
        return
    if card["idList"] == ENVIADO:
        item.erro = "Cartão marcado como Enviado externamente; o sistema não possui confirmação do e-mail."
        mudar(session, item, "envio_incerto", item.erro)
        return
    if card["idList"] != ENVIAR:
        if item.status == "pronto":
            mudar(session, item, "em_atendimento", "Cartão retornou ao atendimento antes do envio.")
        item.erro = None
        session.commit()
        return
    anexos = trello.call("GET", "cards/"+item.trello_id+"/attachments")
    item.resultado = {"descricao": card.get("desc", ""), "anexos": [{"nome": a.get("name"), "url": a["url"]} for a in anexos]}
    item.concluido_em = item.concluido_em or datetime.utcnow()
    if item.status != "pronto":
        mudar(session, item, "pronto", "Conclusão identificada na lista Enviar.")
    if os.getenv("SOLICITACOES_EMAIL_ENABLED", "false").lower() != "true":
        item.erro = "Envio automático de e-mail ainda não ativado."
        session.commit()
        return
    provider = os.getenv("SOLICITACOES_EMAIL_PROVIDER", "smtp")
    if provider == "gmail":
        from app.services.solicitacao_gmail import credenciais
        credenciais()  # Falhas de configuração ocorrem antes de iniciar a tentativa de envio.
    if not os.getenv("SOLICITACOES_EMAIL_FROM") or (provider == "smtp" and not os.getenv("SOLICITACOES_SMTP_HOST")):
        raise RuntimeError("Configure SMTP e remetente antes de ativar os envios.")
    # SMTP não oferece idempotência: falhas ambíguas exigem reconciliação, nunca retry cego.
    mudar(session, item, "envio_incerto", "Tentativa de envio iniciada; aguardando confirmação do provedor.")
    enviar_email(item)
    item.enviado_em = datetime.utcnow()
    item.erro = None
    mudar(session, item, "enviado_pendente_trello", "E-mail aceito pelo provedor. Aguardando movimentação do cartão.")
    trello.call("PUT", "cards/"+item.trello_id, data={"idList": ENVIADO})
    mudar(session, item, "enviado", "Cartão movido para Enviado.")

def executar():
    if os.getenv("SOLICITACOES_WORKER_ENABLED", "false").lower() != "true":
        return {"ativo": False}
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Worker requer PostgreSQL para o bloqueio entre processos.")
    with engine.connect() as lock:
        if not lock.execute(text("SELECT pg_try_advisory_lock(610915)" )).scalar():
            return {"ocupado": True}
        try:
            trello = Trello()
            with Session(engine) as session:
                ids = [i[0] for i in session.query(Solicitacao.id).filter(Solicitacao.status != "enviado").order_by(Solicitacao.id).all()]
                for id in ids:
                    item = session.get(Solicitacao, id)
                    try:
                        item.tentativas += 1
                        session.commit()
                        processar(session, item, trello)
                    except Exception as exc:
                        session.rollback()
                        item = session.get(Solicitacao, id)
                        # Não persistir URLs autenticadas, credenciais ou respostas externas.
                        erro = str(exc) if isinstance(exc, RuntimeError) else "Falha no processamento ("+type(exc).__name__+"). Revisão necessária."
                        if item.erro != erro:
                            evento(session, item, erro)
                        item.erro = erro
                        session.commit()
            return {"processados": len(ids)}
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(610915)"))
