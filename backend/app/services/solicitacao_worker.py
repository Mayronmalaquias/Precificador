"""Integração Trello e entrega. Executado por um worker, nunca pelos workers HTTP."""
import os
import html
import ssl
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
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
        card = None
        # Reconcilia uma criação cuja resposta pode ter se perdido. Só faz sentido quando
        # alguma tentativa já saiu daqui: `integrar` marca `criacao_incerta` ANTES do POST,
        # então um protocolo ainda em `aguardando_trello` nunca chegou a criar cartão e não
        # tem o que reconciliar. Varrer o board inteiro (`filter=all`, todo o histórico) no
        # caminho de criação custava a chamada mais cara do fluxo para nada — e agora ela
        # está dentro do request de quem abriu a solicitação.
        if item.status != "aguardando_trello":
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


def integracao_imediata_ativa():
    """Sem variável própria, segue o worker: onde a integração está ligada, o cartão nasce
    na abertura. Evita que uma máquina de desenvolvimento passe a criar cartões reais no
    board de produção só por levantar a API."""
    valor = os.getenv("SOLICITACOES_INTEGRACAO_IMEDIATA")
    if valor is None:
        valor = os.getenv("SOLICITACOES_WORKER_ENABLED", "false")
    return valor.lower() == "true"


def integrar_imediato(session, item):
    """Cria o cartão ainda dentro do POST, para quem abriu a solicitação já sair com ele.

    A rodada do worker (900s) continua existindo como rede de segurança: aqui NENHUMA falha
    do Trello pode derrubar a abertura, porque a solicitação já está gravada e a integração
    é recuperável. Erro vira `erro`/histórico do protocolo, exatamente como no worker.

    Toma o MESMO advisory lock do worker. Sem ele, uma rodada em curso e este request
    poderiam postar dois cartões para o mesmo protocolo — o marcador só detecta a
    duplicidade depois, e exige revisão manual. Se o lock estiver ocupado, deixa para a
    rodada que já está rodando.

    Devolve o item vigente: um rollback aqui recarrega a linha do banco.
    """
    # `criar` e idempotente por `chave_cliente`: repetir o POST devolve o protocolo que ja
    # existe. Sem esta guarda, cada repeticao gastaria chamadas ao Trello para reconfirmar
    # um cartao pronto.
    if item.integrado_em or not integracao_imediata_ativa():
        return item
    id = item.id
    try:
        if engine.dialect.name != "postgresql":
            item.tentativas += 1
            session.commit()
            integrar(session, item, Trello())
            return item
        with engine.connect() as lock:
            if not lock.execute(text("SELECT pg_try_advisory_lock(610915)")).scalar():
                return item
            try:
                item.tentativas += 1
                session.commit()
                integrar(session, item, Trello())
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(610915)"))
        return item
    except Exception as exc:
        session.rollback()
        item = session.get(Solicitacao, id)
        # Não persistir URLs autenticadas, credenciais ou respostas externas.
        erro = str(exc) if isinstance(exc, RuntimeError) else "Falha no processamento ("+type(exc).__name__+"). Revisão necessária."
        if item.erro != erro:
            evento(session, item, erro)
        item.erro = erro
        session.commit()
        return item


# ── E-mail de conclusão ──────────────────────────────────────────────────────
# Layout em tabela e estilo inline de proposito: Gmail e Outlook descartam <style>
# e nao suportam flex/grid. A logo vai embutida (CID) em vez de URL remota, que a
# maioria dos clientes bloqueia por padrao — a marca simplesmente sumiria.

# 96px (2x do tamanho exibido), nao a arte de 1080px: em base64 a original pesava
# 62 KB por mensagem, e o Gmail corta o corpo acima de ~102 KB — com uma descricao
# longa do juridico o e-mail ficaria truncado. Esta versao custa 5 KB.
LOGO = Path(__file__).resolve().parents[2] / "app/utils/asserts/logo_61_email.png"
LOGO_ORIGINAL = Path(__file__).resolve().parents[2] / "app/utils/asserts/logo_61.png"

MARCA = "#E1005B"      # rosa da 61
TINTA = "#173b58"      # navy da tela de Solicitacoes
TEXTO = "#23364b"
SUAVE = "#62778a"
BORDA = "#dce4eb"
FUNDO = "#eef2f6"

# A descricao do card carrega a chave crua do formulario ("tipo onus", "oficio").
# Sem traduzir, o e-mail sai sem acento e em caixa baixa — metade do problema.
ROTULOS = {
    "tipo": "Tipo", "tipo onus": "Tipo de ônus", "endereco": "Endereço",
    "finalidade": "Finalidade", "equipe": "Equipe", "oficio": "Ofício",
    "matricula": "Matrícula", "corretor": "Corretor",
    "codigo imovel": "Código do imóvel", "possui onus": "Possui ônus",
    "link do imovel": "Link do imóvel",
}


def _partes_descricao(texto):
    """Separa a descricao do card em (campos, texto_livre).

    O marcador `[61-SOL-n]` e controle interno de reconciliacao e nao pode chegar ao
    destinatario. Linha "chave: valor" vira tabela; o resto e o que o juridico
    escreveu a mao e sai como paragrafo, preservado como veio.
    """
    campos, livres = [], []
    for linha in (texto or "").splitlines():
        linha = linha.strip()
        if not linha or (linha.startswith("[61-SOL-") and linha.endswith("]")):
            continue
        chave, sep, valor = linha.partition(":")
        if sep and valor.strip() and len(chave) <= 40:
            rotulo = ROTULOS.get(chave.strip().casefold(), chave.strip().capitalize())
            campos.append((rotulo, valor.strip()))
        else:
            livres.append(linha)
    return campos, livres


def _corpo_html(item, campos, livres, links):
    protocolo = "SOL-" + str(item.id).zfill(6)
    e = html.escape

    linhas = "".join(
        '<tr>'
        f'<td style="padding:10px 0;border-bottom:1px solid {BORDA};color:{SUAVE};'
        f'font-size:13px;width:38%;vertical-align:top;">{e(rotulo)}</td>'
        f'<td style="padding:10px 0;border-bottom:1px solid {BORDA};color:{TEXTO};'
        f'font-size:14px;font-weight:600;vertical-align:top;">{e(valor)}</td>'
        '</tr>'
        for rotulo, valor in campos
    )
    tabela = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;">{linhas}</table>'
    ) if campos else ""

    observacoes = ""
    if livres:
        corpo = "<br>".join(e(l) for l in livres)
        observacoes = (
            f'<div style="margin:20px 0 0;padding:14px 16px;background:{FUNDO};'
            f'border-left:3px solid {MARCA};border-radius:4px;color:{TEXTO};'
            f'font-size:14px;line-height:1.6;">{corpo}</div>'
        )

    anexos = ""
    if links:
        itens = "".join(
            '<tr><td style="padding:7px 0;">'
            f'<a href="{e(a["url"], quote=True)}" '
            f'style="color:{MARCA};font-size:14px;font-weight:600;text-decoration:none;">'
            f'&#128206;&nbsp;{e(a.get("nome") or "Anexo")}</a>'
            '</td></tr>'
            for a in links
        )
        anexos = (
            '<div style="margin:24px 0 0;">'
            f'<div style="color:{SUAVE};font-size:12px;letter-spacing:.08em;'
            'text-transform:uppercase;margin:0 0 4px;">Anexos</div>'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            f'{itens}</table></div>'
        )

    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only">
<title>{protocolo}</title></head>
<body style="margin:0;padding:0;background:{FUNDO};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{FUNDO};">
<tr><td align="center" style="padding:32px 16px;">

<table role="presentation" width="600" cellpadding="0" cellspacing="0"
       style="max-width:600px;width:100%;background:#ffffff;border-radius:10px;
              border:1px solid {BORDA};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">

  <tr><td style="background:{TINTA};padding:22px 28px;border-radius:10px 10px 0 0;">
    <table role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:middle;padding-right:14px;">
        <img src="cid:logo61" width="44" height="44" alt="61 Imóveis"
             style="display:block;border-radius:6px;background:#ffffff;">
      </td>
      <td style="vertical-align:middle;">
        <div style="color:#ffffff;font-size:16px;font-weight:700;line-height:1.2;">61 Imóveis</div>
        <div style="color:#b9c9d7;font-size:12px;line-height:1.5;">Solicitações</div>
      </td>
    </tr></table>
  </td></tr>

  <tr><td style="padding:28px 28px 4px;">
    <div style="display:inline-block;background:{MARCA};color:#ffffff;font-size:12px;
                font-weight:700;letter-spacing:.06em;padding:5px 11px;border-radius:99px;">
      {protocolo}
    </div>
    <h1 style="margin:16px 0 6px;color:{TINTA};font-size:22px;line-height:1.3;font-weight:700;">
      Sua solicitação foi concluída
    </h1>
    <p style="margin:0 0 18px;color:{SUAVE};font-size:14px;line-height:1.6;">
      Abaixo estão os dados do pedido e os anexos disponíveis para download.
    </p>
  </td></tr>

  <tr><td style="padding:0 28px 28px;">
    {tabela}
    {observacoes}
    {anexos}
  </td></tr>

  <tr><td style="background:{FUNDO};padding:18px 28px;border-top:1px solid {BORDA};
                 border-radius:0 0 10px 10px;">
    <p style="margin:0;color:{SUAVE};font-size:12px;line-height:1.6;">
      Mensagem automática do sistema de solicitações da 61 Imóveis.<br>
      Não é necessário responder a este e-mail.
    </p>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""


def _corpo_texto(item, campos, livres, links):
    """Alternativa em texto puro: cliente sem HTML ve o mesmo conteudo."""
    linhas = ["Sua solicitação foi concluída.", "",
              "Protocolo: SOL-" + str(item.id).zfill(6), ""]
    linhas += [rotulo + ": " + valor for rotulo, valor in campos]
    if livres:
        linhas += [""] + livres
    if links:
        linhas += ["", "Anexos:"]
        linhas += ["- " + (a.get("nome") or "Anexo") + ": " + a["url"] for a in links]
    linhas += ["", "61 Imóveis — mensagem automática, não é necessário responder."]
    return "\n".join(linhas)


def _anexar_logo(msg):
    """Embute a logo na parte HTML.

    Falha de leitura NAO pode derrubar o envio: a mensagem ficaria presa em
    `envio_incerto`, que so sai com reconciliacao manual. Sem logo e melhor que sem
    e-mail — o `alt` cobre a ausencia.
    """
    try:
        dados = LOGO.read_bytes()
    except OSError:
        try:
            dados = LOGO_ORIGINAL.read_bytes()
        except OSError:
            return
    partes = msg.get_payload()
    if len(partes) < 2:
        return
    partes[1].add_related(dados, maintype="image", subtype="png", cid="<logo61>")


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
    campos, livres = _partes_descricao(resultado.get("descricao", ""))
    msg.set_content(_corpo_texto(item, campos, livres, links))
    msg.add_alternative(_corpo_html(item, campos, livres, links), subtype="html")
    _anexar_logo(msg)
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
