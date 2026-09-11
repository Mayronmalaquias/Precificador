"""Validação e escopo das solicitações: identidade exclusivamente pelo JWT."""
import re
import unicodedata
from werkzeug.utils import secure_filename
from app.models.solicitacao import Solicitacao, SolicitacaoAnexo, SolicitacaoEvento

# Equipe de verdade tem id no padrao G61xxx (o mesmo que equipes_service.proximo_id_equipe
# gera). A tabela tambem guarda linhas de outra natureza (ex.: "administrativo" e ids C61xxx),
# que nao sao equipe comercial e nao podem virar opcao de solicitacao.
ID_EQUIPE = re.compile(r"G\d+", re.IGNORECASE)
CQC = "Controle de Qualidade"


def equipes_validas():
    """Nomes de equipe aceitos, lidos do cadastro.

    Era uma lista fixa no codigo. Ela envelheceu nos dois sentidos: seguia oferecendo
    PRIME (desativada) e recusava Alpha, Aurea e Legacy, que existem e estao ativas.
    A tela e a validacao agora leem a MESMA fonte, entao equipe nova passa a valer sem
    precisar de deploy.
    """
    from app.services.equipes_service import listar_equipes

    return {
        (e.get("nome") or "").strip()
        for e in listar_equipes()
        if (e.get("nome") or "").strip()
        and ID_EQUIPE.fullmatch(str(e.get("id_equipe") or "").strip())
    }
TIPOS = ["Ônus", "Parecer Jurídico", "Troca de Titularidade", "Celer"]
FINALIDADES = {"Real": ["Venda", "Pós-venda"], "Cópia": ["Captação", "Assertiva", "Pós-Venda", "Imóvel Seguro"]}

def norm(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value or "")) if not unicodedata.combining(c)).strip().lower()

def email_destino(user):
    return (user.email_corporativo or "").strip() or (user.email or "").strip()

def email_valido(email):
    return isinstance(email, str) and len(email) <= 255 and bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email))

def gestor(user):
    return norm(user.permissao) in {"administrador", "administrativo", "diretor"} or norm(user.team) == "administrativo"

def autorizado(user):
    return user and user.ativo and not user.desligado and (gestor(user) or norm(user.permissao) in {"assistente", "estagiario"})

def escopo(session, user):
    q = session.query(Solicitacao)
    return q if gestor(user) else q.filter(Solicitacao.usuario_id == user.id)

def evento(session, item, descricao):
    session.add(SolicitacaoEvento(solicitacao_id=item.id, descricao=descricao))

def validar(dados, arquivos):
    campos = ("tipo", "tipo_onus", "endereco", "finalidade", "equipe", "oficio", "matricula", "corretor", "codigo_imovel", "possui_onus")
    d = {k: str(dados.get(k) or "").strip() for k in campos}
    if any(len(v) > 1000 for v in d.values()):
        raise ValueError("Os campos devem ter no máximo 1000 caracteres.")
    if d["tipo"] not in TIPOS:
        raise ValueError("Tipo de solicitação inválido.")
    required = []
    if d["tipo"] == "Ônus":
        if d["tipo_onus"] not in FINALIDADES:
            raise ValueError("Selecione Ônus Real ou Cópia.")
        required = ["endereco", "finalidade", "equipe", "oficio", "matricula"]
        if d["finalidade"] not in FINALIDADES[d["tipo_onus"]]:
            raise ValueError("Finalidade inválida para o tipo de ônus.")
        if d["oficio"] not in [str(i) for i in range(1, 10)]:
            raise ValueError("Selecione um ofício de 1 a 9.")
        if d["tipo_onus"] == "Cópia":
            required.append("corretor")
    elif d["tipo"] == "Parecer Jurídico":
        required = ["endereco", "codigo_imovel"]
        if d["possui_onus"] not in ("Sim", "Não"):
            raise ValueError("Informe se possui ônus.")
    elif d["tipo"] == "Troca de Titularidade":
        required = ["endereco"]
        if len(arquivos) < 2:
            raise ValueError("Anexe o ônus real atualizado e a ficha cadastral (dois arquivos).")
    else:
        required = ["codigo_imovel", "equipe"]
        if not arquivos:
            raise ValueError("Anexe a foto do Celer.")
        if d["equipe"] == CQC:
            raise ValueError("Equipe não disponível para Celer.")
    if any(not d[k] for k in required):
        raise ValueError("Preencha todos os campos obrigatórios.")
    if "equipe" in required and d["equipe"] not in equipes_validas():
        raise ValueError("Equipe inválida.")
    if len(arquivos) > 5:
        raise ValueError("Envie no máximo 5 arquivos.")
    anexos = []
    total = 0
    for f in arquivos:
        content = f.read(10 * 1024 * 1024 + 1)
        total += len(content)
        if not content or len(content) > 10 * 1024 * 1024 or total > 20 * 1024 * 1024:
            raise ValueError("Limite: 10 MB por arquivo e 20 MB por solicitação.")
        if content.startswith(b"%PDF-"):
            mime = "application/pdf"
        elif content.startswith(bytes.fromhex("89504e470d0a1a0a")):
            mime = "image/png"
        elif content.startswith(bytes.fromhex("ffd8ff")):
            mime = "image/jpeg"
        else:
            raise ValueError("São aceitos somente PDF, PNG e JPEG.")
        if d["tipo"] == "Celer" and not mime.startswith("image/"):
            raise ValueError("Celer exige uma imagem PNG ou JPEG.")
        anexos.append((secure_filename(f.filename or "anexo")[:255] or "anexo", mime, content))
    permitidos = set(required) | {"tipo"}
    if d["tipo"] == "Ônus": permitidos.add("tipo_onus")
    if d["tipo"] == "Parecer Jurídico": permitidos.add("possui_onus")
    return {k: v for k, v in d.items() if k in permitidos}, anexos

def criar(session, user, dados, arquivos, chave):
    if not re.fullmatch(r"[a-zA-Z0-9-]{16,64}", chave or ""):
        raise ValueError("Chave da solicitação inválida. Atualize a página.")
    anterior = escopo(session, user).filter_by(usuario_id=user.id, chave_cliente=chave).first()
    if anterior:
        return anterior
    email = email_destino(user)
    if not email_valido(email):
        raise ValueError("Cadastre um e-mail válido no seu usuário antes de solicitar.")
    d, anexos = validar(dados, arquivos)
    item = Solicitacao(usuario_id=user.id, chave_cliente=chave, email=email, tipo=d["tipo"], dados=d)
    session.add(item)
    session.flush()
    for nome, mime, content in anexos:
        session.add(SolicitacaoAnexo(solicitacao_id=item.id, nome=nome, mime=mime, conteudo=content))
    evento(session, item, "Solicitação registrada. Aguardando integração com o Trello.")
    session.commit()
    return item

def serializar(item):
    d = {k: getattr(item, k) for k in ("id", "tipo", "dados", "status", "email", "trello_url", "lista_nome", "erro", "tentativas", "resultado")}
    for k in ("criado_em", "integrado_em", "concluido_em", "enviado_em", "sincronizado_em"):
        value = getattr(item, k)
        d[k] = value.isoformat() + "Z" if value else None
    d["protocolo"] = "SOL-" + str(item.id).zfill(6)
    return d
