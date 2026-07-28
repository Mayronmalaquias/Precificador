from flask import request, send_file, current_app
from flask_restx import Namespace, Resource
from sqlalchemy import func

from app.database import SessionLocal
from app.models.usuarios import Usuarios

from app.services.rela_gerentes_service import (
    dashboard_gerente,
    listar_corretores_do_gerente,
    listar_visitas_do_gerente,
    listar_clientes_do_gerente,
    ranking_corretores_do_gerente,
    serie_gerente,
    gerar_pdf_corretor_publico,
    gerar_pdf_corretor_download,
    gerar_pdf_gerente_publico,
    gerar_pdf_gerente_download,
    listar_imoveis_do_gerente,
    detalhe_visita_gerente,
    dashboard_equipes,
    gerar_pdf_equipes_download,
    gestao_clientes_visitas,
    evolucao_visitas_gerente,
    opcoes_evolucao_visitas,
)
from app.services.cliente_acao_service import (
    atualizar_acao_cliente,
    criar_acao_cliente,
)

gerente_dashboard_ns = Namespace(
    "gerente_dashboard",
    description="Dashboard consolidado de gerentes e corretores",
)


def _diretor_ativo(usuario_id):
    usuario_id = (usuario_id or "").strip()
    if not usuario_id:
        return False
    session = SessionLocal()
    try:
        return session.query(Usuarios.id_usuarios).filter(
            Usuarios.id_usuarios == usuario_id,
            Usuarios.ativo.is_(True),
            func.lower(Usuarios.permissao) == "diretor",
        ).first() is not None
    finally:
        session.close()


def _escopo_evolucao_visitas(id_gerente):
    solicitou_todas = (request.args.get("solicitante_permissao") or "").strip().lower() == "diretor"
    if solicitou_todas and not _diretor_ativo(id_gerente):
        return False, ({"ok": False, "error": "Apenas diretores podem consultar todas as equipes"}, 403)
    return solicitou_todas, None

@gerente_dashboard_ns.route("/imoveis")
class ImoveisGerente(Resource):
    def get(self):
        try:
            id_gerente = (request.args.get("id_gerente") or "").strip()
            q = (request.args.get("q") or "").strip()
            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None
            limit = int(request.args.get("limit") or 200)

            if not id_gerente:
                return {"ok": False, "error": "id_gerente é obrigatório"}, 400

            lista = listar_imoveis_do_gerente(
                id_gerente=id_gerente,
                q=q,
                start=start,
                end=end,
                limit=limit,
            )
            return {"ok": True, "lista": lista}, 200

        except Exception as e:
            current_app.logger.exception("Erro ao listar imóveis do gerente")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/corretores")
class CorretoresDoGerente(Resource):
    def get(self):
        try:
            id_gerente = (request.args.get("id_gerente") or "").strip()
            if not id_gerente:
                return {"ok": False, "error": "id_gerente é obrigatório"}, 400

            lista = listar_corretores_do_gerente(id_gerente)
            return {"ok": True, "lista": lista}, 200

        except Exception as e:
            current_app.logger.exception("Erro ao listar corretores do gerente")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/dashboard")
class DashboardGerente(Resource):
    def get(self):
        try:
            id_gerente = (request.args.get("id_gerente") or "").strip()
            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None

            if not id_gerente:
                return {"ok": False, "error": "id_gerente é obrigatório"}, 400

            data = dashboard_gerente(id_gerente=id_gerente, start=start, end=end)
            return data, 200

        except Exception as e:
            current_app.logger.exception("Erro ao montar dashboard do gerente")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/visitas")
class VisitasGerente(Resource):
    def get(self):
        try:
            id_gerente = (request.args.get("id_gerente") or "").strip()
            q = (request.args.get("q") or "").strip()
            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None
            limit = int(request.args.get("limit") or 100)

            if not id_gerente:
                return {"ok": False, "error": "id_gerente é obrigatório"}, 400

            lista = listar_visitas_do_gerente(
                id_gerente=id_gerente,
                q=q,
                start=start,
                end=end,
                limit=limit,
            )

            return {"ok": True, "lista": lista}, 200

        except Exception as e:
            current_app.logger.exception("Erro ao listar visitas do gerente")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/clientes")
class ClientesGerente(Resource):
    def get(self):
        try:
            id_gerente = (request.args.get("id_gerente") or "").strip()
            q = (request.args.get("q") or "").strip()
            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None
            limit = int(request.args.get("limit") or 200)

            if not id_gerente:
                return {"ok": False, "error": "id_gerente é obrigatório"}, 400

            lista = listar_clientes_do_gerente(
                id_gerente=id_gerente,
                q=q,
                start=start,
                end=end,
                limit=limit,
            )

            return {"ok": True, "lista": lista}, 200

        except Exception as e:
            current_app.logger.exception("Erro ao listar clientes do gerente")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/ranking")
class RankingGerente(Resource):
    def get(self):
        try:
            id_gerente = (request.args.get("id_gerente") or "").strip()
            tipo = (request.args.get("tipo") or "visitas").strip()
            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None

            if not id_gerente:
                return {"ok": False, "error": "id_gerente é obrigatório"}, 400

            lista = ranking_corretores_do_gerente(
                id_gerente=id_gerente,
                tipo=tipo,
                start=start,
                end=end,
            )

            return {"ok": True, "lista": lista}, 200

        except Exception as e:
            current_app.logger.exception("Erro ao gerar ranking do gerente")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/serie")
class SerieGerente(Resource):
    def get(self):
        try:
            id_gerente = (request.args.get("id_gerente") or "").strip()
            tipo = (request.args.get("tipo") or "visitas").strip()
            agrupamento = (request.args.get("agrupamento") or "dia").strip()
            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None

            if not id_gerente:
                return {"ok": False, "error": "id_gerente é obrigatório"}, 400

            data = serie_gerente(
                id_gerente=id_gerente,
                tipo=tipo,
                agrupamento=agrupamento,
                start=start,
                end=end,
            )
            return data, 200

        except Exception as e:
            current_app.logger.exception("Erro ao gerar série do gerente")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/visitas/evolucao/opcoes")
class OpcoesEvolucaoVisitasGerente(Resource):
    def get(self):
        try:
            id_gerente = (request.args.get("id_gerente") or "").strip()
            todas_equipes, erro_escopo = _escopo_evolucao_visitas(id_gerente)
            if erro_escopo:
                return erro_escopo
            if not id_gerente and not todas_equipes:
                return {"ok": False, "error": "id_gerente e obrigatorio"}, 400
            return opcoes_evolucao_visitas(id_gerente, todas_equipes=todas_equipes), 200
        except Exception as e:
            current_app.logger.exception("Erro nas opcoes da evolucao de visitas")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/visitas/evolucao")
class EvolucaoVisitasGerente(Resource):
    def get(self):
        try:
            id_gerente = (request.args.get("id_gerente") or "").strip()
            todas_equipes, erro_escopo = _escopo_evolucao_visitas(id_gerente)
            if erro_escopo:
                return erro_escopo
            if not id_gerente and not todas_equipes:
                return {"ok": False, "error": "id_gerente e obrigatorio"}, 400
            filtros = {
                "equipe": (request.args.get("equipe") or "").strip(),
                "corretor": (request.args.get("corretor") or "").strip(),
                "proposta": (request.args.get("proposta") or "").strip(),
                "quartos": (request.args.get("quartos") or "").strip(),
                "cliente": (request.args.get("cliente") or "").strip(),
                "imovel": (request.args.get("imovel") or "").strip(),
                "tipo_captacao": (request.args.get("tipo_captacao") or "").strip(),
                "com_parceiro": (request.args.get("com_parceiro") or "").strip(),
                "revisita": (request.args.get("revisita") or "").strip(),
            }
            return evolucao_visitas_gerente(
                id_gerente=id_gerente,
                dimensao=request.args.get("dimensao") or "corretor",
                start=(request.args.get("start") or "").strip() or None,
                end=(request.args.get("end") or "").strip() or None,
                filtros=filtros,
                todas_equipes=todas_equipes,
                granularidade=(request.args.get("granularidade") or "dia").strip(),
            ), 200
        except Exception as e:
            current_app.logger.exception("Erro na evolucao de visitas")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/visita/detalhe")
class DetalheVisitaGerente(Resource):
    def get(self):
        try:
            visita_id = (request.args.get("visita_id") or "").strip()
            if not visita_id:
                return {"ok": False, "error": "visita_id é obrigatório"}, 400

            data = detalhe_visita_gerente(visita_id)
            return data, 200

        except Exception as e:
            current_app.logger.exception("Erro ao buscar detalhe da visita")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/corretor/pdf")
class PdfCorretorPublico(Resource):
    def get(self):
        try:
            id_corretor = (request.args.get("id_corretor") or "").strip()
            if not id_corretor:
                return {"ok": False, "error": "id_corretor é obrigatório"}, 400

            result = gerar_pdf_corretor_publico(id_corretor)

            return {
                "ok": True,
                "id_corretor": id_corretor,
                "file_id": result["file_id"],
                "file_name": result["file_name"],
                "drive_url": result["drive_url"],
                "drive_path": result["drive_path"],
            }, 200

        except Exception as e:
            current_app.logger.exception("Erro ao gerar PDF público do corretor")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/corretor/pdf/download")
class PdfCorretorDownload(Resource):
    def get(self):
        try:
            id_corretor = (request.args.get("id_corretor") or "").strip()
            if not id_corretor:
                return {"ok": False, "error": "id_corretor é obrigatório"}, 400

            buffer_pdf, filename = gerar_pdf_corretor_download(id_corretor)
            buffer_pdf.seek(0)

            return send_file(
                buffer_pdf,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            current_app.logger.exception("Erro ao baixar PDF do corretor")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/gerente/pdf")
class PdfGerentePublico(Resource):
    def get(self):
        try:
            id_gerente = (request.args.get("id_gerente") or "").strip()
            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None

            if not id_gerente:
                return {"ok": False, "error": "id_gerente é obrigatório"}, 400

            result = gerar_pdf_gerente_publico(id_gerente, start, end)

            return {
                "ok": True,
                "id_gerente": id_gerente,
                "file_id": result["file_id"],
                "file_name": result["file_name"],
                "drive_url": result["drive_url"],
                "drive_path": result["drive_path"],
            }, 200

        except Exception as e:
            current_app.logger.exception("Erro ao gerar PDF público do gerente")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/gerente/pdf/download")
class PdfGerenteDownload(Resource):
    def get(self):
        try:
            id_gerente = (request.args.get("id_gerente") or "").strip()
            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None

            if not id_gerente:
                return {"ok": False, "error": "id_gerente é obrigatório"}, 400

            buffer_pdf, filename = gerar_pdf_gerente_download(id_gerente, start, end)
            buffer_pdf.seek(0)

            return send_file(
                buffer_pdf,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            current_app.logger.exception("Erro ao baixar PDF do gerente")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/equipes/dashboard")
class DashboardEquipes(Resource):
    def get(self):
        try:
            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None
            data = dashboard_equipes(start=start, end=end)
            return data, 200
        except Exception as e:
            current_app.logger.exception("Erro ao gerar dashboard de equipes")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/equipes/pdf/download")
class PdfEquipesDownload(Resource):
    def get(self):
        try:
            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None
            buffer_pdf, filename = gerar_pdf_equipes_download(start=start, end=end)
            buffer_pdf.seek(0)
            return send_file(
                buffer_pdf,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )
        except Exception as e:
            current_app.logger.exception("Erro ao baixar PDF de equipes")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/gestao-clientes")
class GestaoClientesVisitas(Resource):
    def get(self):
        try:
            usuario_id = (request.args.get("usuario_id") or "").strip()
            permissao = (request.args.get("permissao") or "").strip()
            team = (request.args.get("team") or "").strip()
            escopo = (request.args.get("escopo") or "").strip()
            id_corretor = (request.args.get("id_corretor") or "").strip()
            id_gerente = (request.args.get("id_gerente") or "").strip()
            q = (request.args.get("q") or "").strip()
            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None
            limit_raw = (request.args.get("limit") or "").strip()
            limit = int(limit_raw) if limit_raw else None

            if not usuario_id or not permissao:
                return {"ok": False, "error": "usuario_id e permissao sao obrigatorios"}, 400

            data = gestao_clientes_visitas(
                usuario_id=usuario_id,
                permissao=permissao,
                team=team,
                escopo=escopo,
                id_corretor=id_corretor,
                id_gerente=id_gerente,
                q=q,
                start=start,
                end=end,
                limit=limit,
            )
            return data, 200

        except Exception as e:
            current_app.logger.exception("Erro ao montar gestao de clientes")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/gestao-clientes/acoes")
class GestaoClientesAcoes(Resource):
    def post(self):
        try:
            data = request.get_json(silent=True) or {}
            acao = criar_acao_cliente(data)
            return {"ok": True, "acao": acao}, 201
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
        except Exception as e:
            current_app.logger.exception("Erro ao criar acao do cliente")
            return {"ok": False, "error": str(e)}, 500


@gerente_dashboard_ns.route("/gestao-clientes/acoes/<int:acao_id>")
class GestaoClientesAcaoDetalhe(Resource):
    def patch(self, acao_id):
        try:
            data = request.get_json(silent=True) or {}
            acao = atualizar_acao_cliente(acao_id, data)
            if not acao:
                return {"ok": False, "error": "acao nao encontrada"}, 404
            return {"ok": True, "acao": acao}, 200
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
        except Exception as e:
            current_app.logger.exception("Erro ao atualizar acao do cliente")
            return {"ok": False, "error": str(e)}, 500
