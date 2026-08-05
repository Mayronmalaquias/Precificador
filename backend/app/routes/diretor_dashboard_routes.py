from flask import current_app, request
from flask_restx import Namespace, Resource
from sqlalchemy import func, or_

from app.database import SessionLocal
from app.models.usuarios import Usuarios
from app.services.diretor_dashboard_service import executive_view


diretor_dashboard_ns = Namespace("diretor_dashboard", description="Visão executiva exclusiva da diretoria")


def _is_active_director(user_id):
    session = SessionLocal()
    try:
        return session.query(Usuarios.id).filter(
            Usuarios.id_usuarios == str(user_id or "").strip(),
            Usuarios.ativo.is_(True),
            or_(
                func.lower(Usuarios.permissao).in_(["diretor", "administrativo"]),
                func.lower(Usuarios.team) == "administrativo",
            ),
        ).first() is not None
    finally:
        session.close()


@diretor_dashboard_ns.route("/executivo")
class ExecutivoDiretor(Resource):
    def get(self):
        solicitante_id = request.args.get("solicitante_id")
        if not _is_active_director(solicitante_id):
            return {"ok": False, "error": "Apenas diretoria ou administrativo podem acessar a visão executiva"}, 403
        try:
            return executive_view(
                start_value=request.args.get("start"),
                end_value=request.args.get("end"),
                team=(request.args.get("team") or "").strip() or None,
            ), 200
        except Exception as exc:
            current_app.logger.exception("Erro ao montar visão executiva do diretor")
            return {"ok": False, "error": str(exc)}, 500
