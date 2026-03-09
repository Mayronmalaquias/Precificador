from flask import request, current_app, send_file
from flask_restx import Namespace, Resource

from app.services.visita_service import (
    registrar_visita,
    upload_pdf_to_drive,
    buscar_visitas_do_corretor,
    gerar_pdf_visita_download,
    gerar_pdf_visita_publico,
)
from app.services.imoview_service import buscar_imoveis_por_endereco
# from app.services.relatorio_visita_service import (
#     gerar_pdf_visita_download,
#     gerar_pdf_visita_publico,
# )

visita_ns = Namespace("visitas", description="Lançamento de visitas")


@visita_ns.route("/visitas")
class LancaVisita(Resource):
    def post(self):
        payload = request.get_json() or {}
        try:
            id_visita = registrar_visita(payload)
            return {"ok": True, "id_visita": id_visita}, 201
        except Exception as e:
            current_app.logger.exception("Erro ao registrar visita")
            return {"ok": False, "error": str(e)}, 500


@visita_ns.route("/upload_pdf")
class UploadPdf(Resource):
    def post(self):
        try:
            f = request.files.get("file")
            if not f:
                return {"ok": False, "error": "Nenhum arquivo enviado."}, 400

            filename = (f.filename or "").lower()
            allowed_extensions = (".pdf", ".jpg", ".jpeg", ".png")
            if not filename.endswith(allowed_extensions):
                return {
                    "ok": False,
                    "error": "Formato inválido. Envie PDF ou Imagem (JPG/PNG).",
                }, 400

            id_corretor = request.form.get("idCorretor", "") or ""
            imovel_id = request.form.get("imovelId", "") or ""
            data_visita = request.form.get("dataVisita", "") or ""

            out = upload_pdf_to_drive(
                file_storage=f,
                id_corretor=id_corretor,
                imovel_id=imovel_id,
                data_visita=data_visita,
            )

            return {"ok": True, **out}, 200

        except Exception as e:
            current_app.logger.exception("Erro no upload_pdf")
            return {"ok": False, "error": str(e)}, 500


@visita_ns.route("/imoveis_busca")
class ImoveisBusca(Resource):
    def get(self):
        try:
            endereco = (request.args.get("endereco") or "").strip()
            if len(endereco) < 3:
                return {"ok": True, "lista": []}, 200

            codigocidade = request.args.get("codigocidade")
            codigosbairros = request.args.get("codigosbairros")

            lista = buscar_imoveis_por_endereco(
                endereco=endereco,
                codigocidade=codigocidade,
                codigosbairros=codigosbairros,
                page=1,
                page_size=20,
            )

            return {"ok": True, "lista": lista}, 200

        except Exception as e:
            current_app.logger.exception("Erro ao buscar imóveis por endereço (Imoview)")
            return {"ok": False, "error": str(e)}, 500


@visita_ns.route("/visitas_busca")
class VisitaBusca(Resource):
    def get(self):
        try:
            id_corretor = (request.args.get("id_corretor") or "").strip()
            q = (request.args.get("q") or "").strip()
            limit = int(request.args.get("limit") or 50)

            if not id_corretor:
                return {"ok": False, "error": "id_corretor é obrigatório"}, 400

            lista = buscar_visitas_do_corretor(
                id_corretor=id_corretor,
                q=q,
                limit=limit,
            )
            return {"ok": True, "lista": lista}, 200

        except Exception as e:
            current_app.logger.exception("Erro ao buscar visita")
            return {"ok": False, "error": str(e)}, 500


@visita_ns.route("/visitas/pdf")
class GerarPdfVisita(Resource):
    def get(self):
        """
        Gera o PDF, salva no Drive e devolve a URL pública.
        Ex:
        /visitas/pdf?visita_id=ABC12345
        """
        try:
            visita_id = (request.args.get("visita_id") or "").strip()
            if not visita_id:
                return {
                    "ok": False,
                    "error": "Parâmetro visita_id é obrigatório.",
                }, 400

            result = gerar_pdf_visita_publico(visita_id)

            return {
                "ok": True,
                "visita_id": visita_id,
                "file_id": result["file_id"],
                "file_name": result["file_name"],
                "drive_url": result["drive_url"],
                "drive_path": result["drive_path"],
            }, 200

        except Exception as e:
            current_app.logger.exception("Erro ao gerar PDF público da visita")
            return {
                "ok": False,
                "error": str(e),
            }, 500


@visita_ns.route("/visitas/pdf/download")
class BaixarPdfVisita(Resource):
    def get(self):
        """
        Gera o PDF em memória e faz download direto.
        Ex:
        /visitas/pdf/download?visita_id=ABC12345
        """
        try:
            visita_id = (request.args.get("visita_id") or "").strip()
            if not visita_id:
                return {
                    "ok": False,
                    "error": "Parâmetro visita_id é obrigatório.",
                }, 400

            buffer_pdf, filename = gerar_pdf_visita_download(visita_id)
            buffer_pdf.seek(0)

            return send_file(
                buffer_pdf,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            current_app.logger.exception("Erro ao baixar PDF da visita")
            return {
                "ok": False,
                "error": str(e),
            }, 500