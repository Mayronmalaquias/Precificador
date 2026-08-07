from flask import current_app, request
from flask_restx import Namespace, Resource

from app.database import SessionLocal
from app.models.usuarios import Usuarios
from app.services.diretor_dashboard_service import executive_view


diretor_dashboard_ns = Namespace("diretor_dashboard", description="Visão executiva da diretoria e dos gerentes")

# Quem enxerga todas as equipes. Gerente entra, mas preso à própria equipe.
PERMISSOES_GLOBAIS = {"diretor", "administrativo"}


def _solicitante(user_id):
    session = SessionLocal()
    try:
        return session.query(Usuarios).filter(
            Usuarios.id_usuarios == str(user_id or "").strip(),
            Usuarios.ativo.is_(True),
        ).first()
    finally:
        session.close()


def _escopo(user):
    """Escopo do solicitante: None = sem acesso.

    {'global': True} vê tudo; {'global': False, 'team': X} só enxerga a equipe X.
    O `team` do gerente vem SEMPRE do banco — o parâmetro da URL é ignorado, senão
    bastaria trocar ?team= para ler a equipe do vizinho.
    """
    if not user:
        return None
    permissao = str(user.permissao or "").strip().lower()
    team = str(user.team or "").strip()
    if permissao in PERMISSOES_GLOBAIS or team.lower() == "administrativo":
        return {"global": True, "team": None}
    if permissao == "gerente" and team:
        return {"global": False, "team": team}
    return None


@diretor_dashboard_ns.route("/executivo")
class ExecutivoDiretor(Resource):
    def get(self):
        escopo = _escopo(_solicitante(request.args.get("solicitante_id")))
        if not escopo:
            return {"ok": False, "error": "Sem permissão para a visão executiva"}, 403
        if escopo["global"]:
            team = (request.args.get("team") or "").strip() or None
        else:
            team = escopo["team"]
        try:
            return executive_view(
                start_value=request.args.get("start"),
                end_value=request.args.get("end"),
                team=team,
                broker=(request.args.get("corretor") or "").strip() or None,
                somente_equipe=not escopo["global"],
            ), 200
        except Exception as exc:
            current_app.logger.exception("Erro ao montar visão executiva do diretor")
            return {"ok": False, "error": str(exc)}, 500
