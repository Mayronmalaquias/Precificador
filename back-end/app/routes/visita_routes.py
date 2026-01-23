# app/routes/visita_routes.py
from flask import request, current_app
from flask_restx import Namespace, Resource

from app.services.visita_service import registrar_visita, upload_pdf_to_drive

visita_ns = Namespace("visitas", description="Lançamento de visitas")


@visita_ns.route("")
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
                return {"ok": False, "error": "Nenhum arquivo enviado (campo 'file')."}, 400

            filename = (f.filename or "").lower()
            if not filename.endswith(".pdf"):
                return {"ok": False, "error": "Envie um PDF (.pdf)."}, 400

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
