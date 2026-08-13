from __future__ import annotations

from flask import request, send_file
from flask_restx import Namespace, Resource

from app.services.imovel_rel_service import (
    listar_imoveis_do_corretor,
    listar_imoveis_estoque_do_corretor,
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


@imovel_catalogo_ns.route("/imoveis_estoque_corretor")
class ImoveisEstoqueCorretorResource(Resource):
    """Imoveis NO NOME do corretor (estoque atual, captador1/2/3). Usado pelo app."""

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

            lista = listar_imoveis_estoque_do_corretor(
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



@imovel_catalogo_ns.route("/imoveis/captados")
class ImoveisCaptadosResource(Resource):
    @imovel_catalogo_ns.doc(
        description=(
            "Códigos de imóveis captados pelo corretor (`fato_captacao.captador1/2/3`). "
            "A tela usa para marcar quais rendem relatório — o mesmo critério que a rota "
            "de download aplica."
        ),
        params={"id_corretor": "Id do corretor."},
    )
    def get(self):
        from app.services.imovel_pdf_service import listar_codigos_captados

        id_corretor = (request.args.get("id_corretor") or "").strip()
        if not id_corretor:
            return {"ok": False, "error": "Parâmetro id_corretor é obrigatório."}, 400
        codigos = listar_codigos_captados(id_corretor)
        return {"ok": True, "lista": codigos, "total": len(codigos)}, 200



def _checar_captacao_propria(imovel_id):
    """Corretor identificado só baixa relatório de imóvel que ele captou.

    Só vale quando `id_corretor` vem na chamada: gerente e diretoria continuam baixando
    sem restrição, como sempre — o parâmetro é a tela do corretor se identificando.
    """
    from flask import request

    from app.services.imovel_pdf_service import ImovelPdfErro, checar_direito

    id_corretor = (request.args.get("id_corretor") or "").strip()
    if not id_corretor:
        return None
    try:
        checar_direito(imovel_id, id_corretor)
        return None
    except ImovelPdfErro as e:
        return {"ok": False, "error": e.mensagem}, e.status


@imovel_catalogo_ns.route("/imoveis/pdf")
class GerarPdfImovelResource(Resource):
    def get(self):
        try:
            imovel_id = (request.args.get("imovel_id") or "").strip()
            if not imovel_id:
                return {"ok": False, "error": "Parâmetro imovel_id é obrigatório."}, 400

            negado = _checar_captacao_propria(imovel_id)
            if negado:
                return negado

            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None
            result = gerar_pdf_imovel_publico(imovel_id, start, end)

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

            negado = _checar_captacao_propria(imovel_id)
            if negado:
                return negado

            start = (request.args.get("start") or "").strip() or None
            end = (request.args.get("end") or "").strip() or None
            try:
                buffer_pdf, filename = gerar_pdf_imovel_download(imovel_id, start, end)
            except Exception as e:
                if "Nenhuma visita encontrada" in str(e):
                    return {"ok": False, "error": "Esse imóvel ainda não tem visita registrada — o relatório é montado a partir delas."}, 404
                raise
            buffer_pdf.seek(0)

            return send_file(
                buffer_pdf,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            return {"ok": False, "error": str(e)}, 500