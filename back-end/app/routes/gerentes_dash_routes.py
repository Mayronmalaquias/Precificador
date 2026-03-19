from flask import request, send_file, current_app
from flask_restx import Namespace, Resource

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
    listar_imoveis_do_gerente
)

gerente_dashboard_ns = Namespace(
    "gerente_dashboard",
    description="Dashboard consolidado de gerentes e corretores",
)

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