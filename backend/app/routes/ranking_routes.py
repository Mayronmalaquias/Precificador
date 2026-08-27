# app/routes/ranking_routes.py
from flask import request, send_file
from flask_restx import Namespace, Resource, fields
from app.services.ranking_service import RankingService
from app.services.corretor_pdf_service import gerar_pdf_corretor, gerar_pdf_todos
from app.services.ranking_xlsx_service import gerar_xlsx_vgc_captacao
from app.services import ranking_ocultos_service as ocultos_svc

ranking_ns = Namespace("ranking", description="Rankings (VGV, VGC, Captação, Visitas)")


@ranking_ns.route("/rankings/ocultos")
class RankingOcultos(Resource):
    @ranking_ns.doc(description="Lista corretores ocultados do ranking")
    def get(self):
        return {"ok": True, "ocultos": ocultos_svc.listar_ocultos()}, 200

    @ranking_ns.doc(description="Oculta um corretor do ranking (body: id_corretor, nome)")
    def post(self):
        data = request.get_json() or {}
        res = ocultos_svc.ocultar(data.get("id_corretor"), data.get("nome", ""))
        return res, (200 if res.get("ok") else 400)


@ranking_ns.route("/rankings/ocultos/<path:id_corretor>")
class RankingMostrar(Resource):
    @ranking_ns.doc(description="Remove um corretor da lista de ocultos (volta ao ranking)")
    def delete(self, id_corretor):
        res = ocultos_svc.mostrar(id_corretor)
        return res, (200 if res.get("ok") else 400)

ranking_item = ranking_ns.model("RankingItem", {
    "posicao": fields.Integer,
    "id_corretor": fields.String,
    "corretor": fields.String,
    "total": fields.Float,
})

ranking_response = ranking_ns.model("RankingResponse", {
    "vgv": fields.List(fields.Nested(ranking_item)),
    "vgc": fields.List(fields.Nested(ranking_item)),

    "vgv_geral": fields.List(fields.Nested(ranking_item)),
    "vgc_geral": fields.List(fields.Nested(ranking_item)),

    "captacao": fields.List(fields.Nested(ranking_item)),
    "visitas": fields.List(fields.Nested(ranking_item)),
    "meta": fields.Raw,
})


@ranking_ns.route("/rankings/vgc-foco/xlsx")
class VgcFocoXlsx(Resource):
    @ranking_ns.doc(params={
        "start": "Data inicial (YYYY-MM-DD). Opcional.",
        "end": "Data final (YYYY-MM-DD). Opcional.",
    })
    def get(self):
        import io
        import pandas as pd
        from flask import send_file

        start = request.args.get("start")
        end = request.args.get("end")
        try:
            df = RankingService().relatorio_vgc_foco(start, end)
            bio = io.BytesIO()
            with pd.ExcelWriter(bio, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="VGC Foco")
            bio.seek(0)
            nome = f"vgc_foco_{start or 'inicio'}_{end or 'fim'}.xlsx"
            return send_file(
                bio,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=nome,
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}, 500


@ranking_ns.route("/rankings/fechamento")
class RankingFechamento(Resource):
    @ranking_ns.doc(params={
        "mes": "Mês do fechamento (YYYY-MM). Padrão: mês atual.",
        "meta": "Meta de captações por corretor (padrão 4).",
    })
    def get(self):
        from datetime import date
        mes = (request.args.get("mes") or date.today().strftime("%Y-%m")).strip()
        try:
            meta = int(request.args.get("meta") or 4)
        except ValueError:
            meta = 4
        try:
            servico = RankingService()
            # Texto e dados vem do MESMO calculo: `gerar_texto_fechamento` renderiza
            # `fechamento()`. Dois calculos fariam o numero colado no grupo divergir do
            # numero da tela no primeiro ajuste feito em um so.
            dados = servico.fechamento(mes, meta=meta)
            return {
                "ok": True, "mes": mes,
                "texto": servico.gerar_texto_fechamento(mes, meta=meta),
                "equipes": dados["equipes"],
                "orfas": dados["orfas"],
                "resumo": dados["resumo"],
                "meta": dados["meta"],
            }, 200
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
        except Exception as e:
            return {"ok": False, "error": str(e)}, 500


@ranking_ns.route("/rankings")
class Rankings(Resource):
    @ranking_ns.doc(
        params={
            "start": "Data inicial (YYYY-MM-DD). Opcional.",
            "end": "Data final (YYYY-MM-DD). Opcional.",
            "include_pending": "Se true, inclui vendas sem divisão de comissão. Padrão: false.",
            "apply_factor": "Se true, divide Valor_Total_61 por 0.06 no VGC. Padrão: false.",
        }
    )
    @ranking_ns.marshal_with(ranking_response)
    def get(self):
        start = request.args.get("start")
        end = request.args.get("end")
        include_pending = request.args.get("include_pending", "false").lower() == "true"
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"

        svc = RankingService()
        result = svc.get_all_rankings(start=start, end=end, include_pending=include_pending, apply_factor=apply_factor)
        return result, 200


@ranking_ns.route("/rankings/<string:kind>")
class RankingsByKind(Resource):
    @ranking_ns.doc(
        params={
            "start": "Data inicial (YYYY-MM-DD). Opcional.",
            "end": "Data final (YYYY-MM-DD). Opcional.",
            "include_pending": "Mesma regra do endpoint geral. Padrão: false.",
            "apply_factor": "Se true, divide Valor_Total_61 por 0.06 no VGC. Padrão: false.",
        }
    )
    @ranking_ns.marshal_list_with(ranking_item)
    def get(self, kind: str):
        kind = (kind or "").lower().strip()
        if kind not in {"vgv_geral", "vgc_geral", "captacao", "visitas"}:
            ranking_ns.abort(400, "kind inválido. Use: vgv_geral, vgc_geral, captacao, visitas")

        start = request.args.get("start")
        end = request.args.get("end")
        include_pending = request.args.get("include_pending", "false").lower() == "true"
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"

        svc = RankingService()
        ranking = svc.get_ranking(kind=kind, start=start, end=end, include_pending=include_pending, apply_factor=apply_factor)
        return ranking, 200


@ranking_ns.route("/rankings/<string:kind>/equipe")
class RankingsByKindEquipe(Resource):
    @ranking_ns.doc(
        params={
            "start": "Data inicial (YYYY-MM-DD). Opcional.",
            "end": "Data final (YYYY-MM-DD). Opcional.",
            "include_pending": "Se true, inclui vendas pendentes. Padrão: false.",
            "apply_factor": "Se true, divide Valor_Total_61 por 0.06 no VGC. Padrão: false.",
        }
    )
    @ranking_ns.marshal_list_with(ranking_item)
    def get(self, kind: str):
        kind = (kind or "").lower().strip()
        if kind not in {"vgv_geral", "vgc_geral", "captacao", "visitas"}:
            ranking_ns.abort(400, "kind inválido. Use: vgv_geral, vgc_geral, captacao, visitas")

        start = request.args.get("start")
        end = request.args.get("end")
        include_pending = request.args.get("include_pending", "false").lower() == "true"
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"

        svc = RankingService()
        ranking = svc.get_ranking_equipe(kind=kind, start=start, end=end, include_pending=include_pending, apply_factor=apply_factor)
        return ranking, 200


@ranking_ns.route("/rankings/todos/pdf")
class TodosPdf(Resource):
    @ranking_ns.doc(
        params={
            "kind": "vgc_geral ou vgv_geral.",
            "start": "Data inicial (YYYY-MM-DD).",
            "end": "Data final (YYYY-MM-DD).",
            "apply_factor": "Divide Valor_Total_61 por 0.06 (só VGC). Padrão: false.",
        }
    )
    def get(self):
        kind = (request.args.get("kind", "vgc_geral") or "vgc_geral").lower().strip()
        if kind not in {"vgc_geral", "vgv_geral"}:
            return {"error": "kind inválido."}, 400

        start = request.args.get("start")
        end = request.args.get("end")
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"

        svc = RankingService()
        detalhes = svc.get_todos_detalhe(kind=kind, start=start, end=end, apply_factor=apply_factor)

        if not detalhes:
            return {"error": "Nenhum dado encontrado para os filtros informados."}, 404

        rankings = {
            "vgv_corretor": svc.get_ranking("vgv_geral", start, end),
            "vgc_corretor": svc.get_ranking("vgc_geral", start, end, apply_factor=apply_factor),
            "vgv_equipe": svc.get_ranking_equipe("vgv_geral", start, end),
            "vgc_equipe": svc.get_ranking_equipe("vgc_geral", start, end, apply_factor=apply_factor),
        }
        buf = gerar_pdf_todos(detalhes, rankings=rankings)
        nome_arquivo = f"relatorio_comissoes_{start}_{end}.pdf"
        return send_file(buf, as_attachment=True, download_name=nome_arquivo, mimetype="application/pdf")


@ranking_ns.route("/rankings/vgc-captacao/xlsx")
class VgcCaptacaoXlsx(Resource):
    @ranking_ns.doc(params={
        "start": "Data inicial (YYYY-MM-DD).",
        "end": "Data final (YYYY-MM-DD).",
        "apply_factor": "Divide o VGC por 0.06. Padrão: false.",
    })
    def get(self):
        start = request.args.get("start")
        end = request.args.get("end")
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"
        relatorio = RankingService().get_relatorio_vgc_captacao(start, end, apply_factor)
        if not relatorio["detalhes"]:
            return {"error": "Nenhum contrato com captação encontrado para os filtros informados."}, 404

        buf = gerar_xlsx_vgc_captacao(relatorio)
        nome = f"vgc_captacao_{start or 'inicio'}_{end or 'fim'}.xlsx"
        return send_file(
            buf,
            as_attachment=True,
            download_name=nome,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


@ranking_ns.route("/rankings/corretor/detalhe")
class CorretorDetalhe(Resource):
    @ranking_ns.doc(
        params={
            "nome": "Nome do corretor (exato, case-insensitive).",
            "kind": "vgc_geral ou vgv_geral.",
            "start": "Data inicial (YYYY-MM-DD).",
            "end": "Data final (YYYY-MM-DD).",
            "apply_factor": "Se true, divide Valor_Total_61 por 0.06 (só VGC). Padrão: false.",
        }
    )
    def get(self):
        nome = request.args.get("nome", "")
        kind = (request.args.get("kind", "vgc_geral") or "vgc_geral").lower().strip()
        if kind not in {"vgc_geral", "vgv_geral"}:
            return {"error": "kind inválido. Use: vgc_geral, vgv_geral"}, 400

        start = request.args.get("start")
        end = request.args.get("end")
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"

        svc = RankingService()
        resultado = svc.get_corretor_detalhe(
            nome_corretor=nome,
            kind=kind,
            start=start,
            end=end,
            apply_factor=apply_factor,
        )
        return resultado, 200


@ranking_ns.route("/rankings/corretor/pdf")
class CorretorPdf(Resource):
    @ranking_ns.doc(
        params={
            "nome": "Nome do corretor.",
            "kind": "vgc_geral ou vgv_geral.",
            "start": "Data inicial (YYYY-MM-DD).",
            "end": "Data final (YYYY-MM-DD).",
            "apply_factor": "Divide Valor_Total_61 por 0.06 (só VGC). Padrão: false.",
        }
    )
    def get(self):
        nome = request.args.get("nome", "")
        kind = (request.args.get("kind", "vgc_geral") or "vgc_geral").lower().strip()
        if kind not in {"vgc_geral", "vgv_geral"}:
            return {"error": "kind inválido."}, 400

        start = request.args.get("start")
        end = request.args.get("end")
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"

        svc = RankingService()
        detalhe = svc.get_corretor_detalhe(
            nome_corretor=nome,
            kind=kind,
            start=start,
            end=end,
            apply_factor=apply_factor,
        )

        buf = gerar_pdf_corretor(detalhe)
        nome_arquivo = f"comissoes_{nome.replace(' ', '_').lower()}_{start}_{end}.pdf"
        return send_file(buf, as_attachment=True, download_name=nome_arquivo, mimetype="application/pdf")


# app/routes/meta_gerente_routes.py
# app/routes/meta_gerente_routes.py# app/routes/meta_gerente_routes.py
import os
from flask import Blueprint, request, send_file
from app.services.meta_service import MetaGerenteConfig, MetaGerenteService
from datetime import datetime

meta_gerente_bp = Blueprint("meta_gerente_bp", __name__)

@meta_gerente_bp.route("/relatorio/metas-gerentes", methods=["POST"])
def gerar_relatorio_metas_gerentes():
    body = request.get_json() or {}
    hoje = datetime.today()

    config = MetaGerenteConfig(
        ano_relatorio=body.get("ano_relatorio", hoje.year),
        mes_relatorio=body.get("mes_relatorio", hoje.month),
        sheet_id_contratos=body.get(
            "sheet_id_contratos",
            os.environ.get("GSHEET_VENDAS_ID", "1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y")
        ),
        sheet_id_base_inteligencia=body.get(
            "sheet_id_base_inteligencia",
            os.environ.get("GSHEET_BASE_INTELIGENCIA_ID", "1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw")
        ),
        sheet_id_visitas=body.get(
            "sheet_id_visitas",
            os.environ.get("GSHEET_VISITAS_ID", "1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU")
        ),
        caminho_credencial=body.get("caminho_credencial", "./app/utils/asserts/credenciais.json")
    )

    service = MetaGerenteService(config)
    metas_mensais = body.get("metas_mensais", {})

    pdf_buffer = service.gerar_relatorio_pdf(metas_mensais)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=config.nome_arquivo_pdf,
        mimetype="application/pdf"
    )


@meta_gerente_bp.route("/relatorio/metas-gerentes/preview", methods=["POST"])
def preview_relatorio_metas_gerentes():
    from flask import jsonify
    body = request.get_json() or {}
    hoje = datetime.today()

    config = MetaGerenteConfig(
        ano_relatorio=body.get("ano_relatorio", hoje.year),
        mes_relatorio=body.get("mes_relatorio", hoje.month),
        sheet_id_contratos=body.get(
            "sheet_id_contratos",
            os.environ.get("GSHEET_VENDAS_ID", "1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y")
        ),
        sheet_id_base_inteligencia=body.get(
            "sheet_id_base_inteligencia",
            os.environ.get("GSHEET_BASE_INTELIGENCIA_ID", "1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw")
        ),
        sheet_id_visitas=body.get(
            "sheet_id_visitas",
            os.environ.get("GSHEET_VISITAS_ID", "1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU")
        ),
        caminho_credencial=body.get("caminho_credencial", "./app/utils/asserts/credenciais.json")
    )

    service = MetaGerenteService(config)
    metas_mensais = body.get("metas_mensais", {})

    try:
        df = service.calcular_dados_relatorio(metas_mensais)
        return jsonify(df.to_dict(orient="records"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500
