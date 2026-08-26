"""Painel de Tarefas: agrega as pendências dos quatro módulos.

Só leitura. O hub NÃO tem endpoint de conclusão próprio — resolver uma tarefa é chamar o
mesmo endpoint que o módulo de origem usa (`POST /propostas/:id/acoes`,
`POST /visitas/vistas`, `PUT /leads/gestao/:id`). É o que faz concluir num lugar refletir
no outro sem código de sincronização.
"""
from flask import current_app, g, request
from flask_restx import Namespace, Resource

from app.services import tarefas_service as servico
from app.services.tarefas_service import TarefaErro

tarefas_ns = Namespace("tarefas", description="Pendências agregadas dos módulos de gestão")


def _solicitante():
    """Identidade do JWT quando há; o parâmetro só vale sem token (app/integração)."""
    payload = getattr(g, "jwt_payload", None) or {}
    if payload.get("sub"):
        return payload["sub"]
    return request.args.get("solicitante_id")


@tarefas_ns.route("/tarefas")
class Tarefas(Resource):
    @tarefas_ns.doc(params={
        "solicitante_id": "Id do usuário (ignorado quando há JWT).",
        "tipos": "Lista separada por vírgula: proposta,visita,lead,cliente.",
        "nivel": "critica | atencao | normal",
        "responsavel": "Filtra por nome de quem responde (busca parcial).",
        "gerente_id": "Recorta pela equipe do gerente (somente perfis globais).",
    })
    def get(self):
        try:
            tipos = [t.strip() for t in (request.args.get("tipos") or "").split(",") if t.strip()]
            return servico.listar(
                _solicitante(),
                tipos=tipos or None,
                nivel=request.args.get("nivel") or None,
                responsavel=request.args.get("responsavel") or None,
                gerente_id=request.args.get("gerente_id") or None,
            ), 200
        except TarefaErro as e:
            return {"ok": False, "error": e.mensagem}, e.status
        except Exception:
            current_app.logger.exception("Erro ao listar tarefas")
            return {"ok": False, "error": "Erro interno ao listar tarefas."}, 500
