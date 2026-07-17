# app/routes/parcerias_routes.py
from flask import request
from flask_restx import Namespace, Resource, fields

from app.services import parcerias_service as svc

parcerias_ns = Namespace("parcerias", description="Parcerias da 61 com imobiliárias/corretores")

parceria_model = parcerias_ns.model("Parceria", {
    "id": fields.Integer,
    "nome": fields.String,
    "percentual": fields.String,
    "faz_parceria": fields.Boolean,
    "tem_contrato": fields.Boolean,
    "observacao": fields.String,
})


@parcerias_ns.route("/parcerias")
class ParceriasList(Resource):
    @parcerias_ns.doc(description="Lista todas as parcerias (ordenadas por nome)")
    def get(self):
        return {"ok": True, "items": svc.listar()}, 200

    @parcerias_ns.doc(description="Cria uma parceria (body: nome, percentual, faz_parceria, tem_contrato, observacao)")
    def post(self):
        data = request.get_json() or {}
        res = svc.criar(data)
        return res, (201 if res.get("ok") else 400)


@parcerias_ns.route("/parcerias/<int:parceria_id>")
class ParceriaItem(Resource):
    @parcerias_ns.doc(description="Atualiza uma parceria")
    def put(self, parceria_id):
        data = request.get_json() or {}
        res = svc.atualizar(parceria_id, data)
        return res, (200 if res.get("ok") else 400)

    @parcerias_ns.doc(description="Remove uma parceria")
    def delete(self, parceria_id):
        res = svc.remover(parceria_id)
        return res, (200 if res.get("ok") else 400)
