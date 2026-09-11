from io import BytesIO
from flask import request, g, send_file, abort
from flask_restx import Namespace, Resource
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from app.database import SessionLocal
from app.models.usuarios import Usuarios
from app.models.solicitacao import Solicitacao, SolicitacaoAnexo, SolicitacaoEvento
from app.services import solicitacao_service as svc
from app.utils.auth_middleware import _check_bearer_jwt

solicitacao_ns = Namespace("solicitacoes", description="Solicitações operacionais e acompanhamento")

def usuario(session):
    # O middleware global pode aceitar a API key antes de decodificar o JWT.
    if not _check_bearer_jwt():
        abort(401, description="Faça login para acessar suas solicitações.")
    username = (g.jwt_payload or {}).get("username")
    user = session.query(Usuarios).filter(Usuarios.username == username).one_or_none() if username else None
    if not svc.autorizado(user):
        abort(403, description="Sem permissão para solicitações.")
    return user

def item_autorizado(session, user, id):
    item = svc.escopo(session, user).filter(Solicitacao.id == id).first()
    if not item:
        abort(404)
    return item

@solicitacao_ns.route("/solicitacoes")
class Solicitacoes(Resource):
    def get(self):
        session = SessionLocal()
        user = usuario(session)
        q = svc.escopo(session, user)
        if request.args.get("tipo"):
            q = q.filter(Solicitacao.tipo == request.args["tipo"])
        if request.args.get("busca"):
            termo = "%" + request.args["busca"][:100].removeprefix("SOL-").lstrip("0") + "%"
            from sqlalchemy import cast, String, or_
            q = q.filter(or_(cast(Solicitacao.id, String).ilike(termo), cast(Solicitacao.dados, String).ilike(termo)))
        resumo = dict(q.with_entities(Solicitacao.status, func.count(Solicitacao.id)).group_by(Solicitacao.status).all())
        if request.args.get("status"):
            q = q.filter(Solicitacao.status == request.args["status"])
        pagina = max(1, request.args.get("pagina", 1, type=int))
        total = q.count()
        items = q.order_by(Solicitacao.criado_em.desc()).offset((pagina-1)*30).limit(30).all()
        return {"itens": [svc.serializar(i) for i in items], "total": total, "pagina": pagina,
                "resumo": resumo, "gestor": svc.gestor(user), "email": svc.email_destino(user),
                "precisa_email": not svc.email_valido(svc.email_destino(user))}

    def post(self):
        if request.content_length and request.content_length > 21 * 1024 * 1024:
            abort(413)
        session = SessionLocal()
        user = usuario(session)
        chave = request.form.get("chave_cliente", "")
        try:
            item = svc.criar(session, user, request.form, request.files.getlist("anexos"), chave)
            return svc.serializar(item), 201
        except ValueError as e:
            session.rollback()
            return {"error": str(e)}, 400
        except IntegrityError:
            session.rollback()
            item = svc.escopo(session, user).filter_by(usuario_id=user.id, chave_cliente=chave).first()
            if item:
                return svc.serializar(item), 200
            raise

@solicitacao_ns.route("/solicitacoes/meu-email")
class MeuEmail(Resource):
    def put(self):
        session = SessionLocal()
        user = usuario(session)
        # Somente o cadastro autenticado; não aceita identidade vinda do cliente.
        user = session.query(Usuarios).filter_by(id=user.id).with_for_update().populate_existing().one()
        if svc.email_valido(svc.email_destino(user)):
            return {"error": "Seu cadastro já possui e-mail. Atualize a tela para continuar."}, 409
        dados = request.get_json(silent=True)
        email = dados.get("email") if isinstance(dados, dict) else None
        email = email.strip() if isinstance(email, str) else email
        if not svc.email_valido(email):
            return {"error": "Informe um e-mail válido com até 255 caracteres."}, 400
        if (user.email_corporativo or "").strip():
            user.email_corporativo = email
        else:
            user.email = email
        session.commit()
        return {"email": svc.email_destino(user), "precisa_email": False}

@solicitacao_ns.route("/solicitacoes/<int:id>")
class SolicitacaoDetalhe(Resource):
    def get(self, id):
        session = SessionLocal()
        item = item_autorizado(session, usuario(session), id)
        d = svc.serializar(item)
        d["anexos"] = [{"id": a.id, "nome": a.nome} for a in session.query(SolicitacaoAnexo.id, SolicitacaoAnexo.nome).filter_by(solicitacao_id=id)]
        d["historico"] = [{"data": e.criado_em.isoformat()+"Z", "descricao": e.descricao} for e in session.query(SolicitacaoEvento).filter_by(solicitacao_id=id).order_by(SolicitacaoEvento.id)]
        return d

@solicitacao_ns.route("/solicitacoes/<int:id>/anexos/<int:anexo_id>")
class Download(Resource):
    def get(self, id, anexo_id):
        session = SessionLocal()
        item_autorizado(session, usuario(session), id)
        a = session.query(SolicitacaoAnexo).filter_by(id=anexo_id, solicitacao_id=id).first()
        if not a:
            abort(404)
        response = send_file(BytesIO(a.conteudo), mimetype=a.mime, as_attachment=True, download_name=a.nome)
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
