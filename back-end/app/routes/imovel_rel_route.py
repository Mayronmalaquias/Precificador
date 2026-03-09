from __future__ import annotations

from flask import request, send_file
from flask_restx import Namespace, Resource

from app.services.imovel_rel_service import (
    listar_imoveis_do_corretor,
    gerar_pdf_imovel_publico,
    gerar_pdf_imovel_download,
)

imovel_catalogo_ns = Namespace(
    "imovel_catalogo",
    description="Busca de imóveis por corretor",
)


@imovel_catalogo_ns.route("/imoveis_busca_corretor")
class ImoveisBuscaCorretorResource(Resource):
    def get(self):
        try:
            id_corretor = (request.args.get("id_corretor") or "").strip()
            q = (request.args.get("q") or "").strip()

            try:
                limit = int(request.args.get("limit") or 50)
            except Exception:
                limit = 50

            if not id_corretor:
                return {
                    "ok": False,
                    "error": "Parâmetro id_corretor é obrigatório.",
                }, 400

            lista = listar_imoveis_do_corretor(
                id_corretor=id_corretor,
                q=q,
                limit=limit,
            )

            return {
                "ok": True,
                "lista": lista,
            }, 200

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }, 500


@imovel_catalogo_ns.route("/imoveis/pdf")
class GerarPdfImovelResource(Resource):
    def get(self):
        try:
            imovel_id = (request.args.get("imovel_id") or "").strip()
            if not imovel_id:
                return {"ok": False, "error": "Parâmetro imovel_id é obrigatório."}, 400

            result = gerar_pdf_imovel_publico(imovel_id)

            return {
                "ok": True,
                "imovel_id": imovel_id,
                "file_id": result["file_id"],
                "file_name": result["file_name"],
                "drive_url": result["drive_url"],
                "drive_path": result["drive_path"],
            }, 200

        except Exception as e:
            return {"ok": False, "error": str(e)}, 500


@imovel_catalogo_ns.route("/imoveis/pdf/download")
class BaixarPdfImovelResource(Resource):
    def get(self):
        try:
            imovel_id = (request.args.get("imovel_id") or "").strip()
            if not imovel_id:
                return {"ok": False, "error": "Parâmetro imovel_id é obrigatório."}, 400

            buffer_pdf, filename = gerar_pdf_imovel_download(imovel_id)
            buffer_pdf.seek(0)

            return send_file(
                buffer_pdf,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            return {"ok": False, "error": str(e)}, 500