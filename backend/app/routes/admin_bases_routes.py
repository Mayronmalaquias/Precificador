from flask import current_app, request
from flask_restx import Namespace, Resource

from app.services import admin_bases_service as svc
from app.services import leads_service
from app.services import dfimoveis_service
from app.services.sync_contratos_service import sync_contratos_from_sheet

admin_bases_ns = Namespace("admin-bases", description="Gestao administrativa das bases (captacao/saida/estoque/venda/destaque)")


def _erro(e, msg="Erro inesperado"):
    current_app.logger.exception(msg)
    return {"ok": False, "error": str(e)}, 500


def _arquivo():
    f = request.files.get("arquivo") or request.files.get("file")
    if not f or not f.filename:
        return None
    return f


def _filtros():
    return {
        "codigo": request.args.get("codigo"),
        "captador": request.args.get("captador"),
        "bairro": request.args.get("bairro"),
        "data_de": request.args.get("data_de"),
        "data_ate": request.args.get("data_ate"),
    }


def _paginacao():
    return int(request.args.get("page", 1)), int(request.args.get("per_page", 50))


# =========================
# Importacao de arquivo
# =========================
@admin_bases_ns.route("/admin/bases/importar/captacao")
class ImportarCaptacao(Resource):
    @admin_bases_ns.doc(description="Importa captacoes de um CSV/XLSX/XLS (Imoview). Campo de arquivo: 'arquivo'.")
    def post(self):
        f = _arquivo()
        if not f:
            return {"ok": False, "error": "Envie o arquivo no campo 'arquivo'"}, 400
        criado_por = request.form.get("criado_por")
        finalidade = request.form.get("finalidade", "Venda")
        try:
            resumo = svc.processar_captacao(f, criado_por=criado_por, finalidade=finalidade or None)
            return {"ok": True, **resumo}, 200
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
        except Exception as e:
            return _erro(e, "Erro ao importar captacao")


@admin_bases_ns.route("/admin/bases/importar/saida")
class ImportarSaida(Resource):
    @admin_bases_ns.doc(description="Importa saidas de um CSV/XLSX/XLS (Imoview). Campo de arquivo: 'arquivo'.")
    def post(self):
        f = _arquivo()
        if not f:
            return {"ok": False, "error": "Envie o arquivo no campo 'arquivo'"}, 400
        criado_por = request.form.get("criado_por")
        finalidade = request.form.get("finalidade", "Venda")
        try:
            resumo = svc.processar_saida(f, criado_por=criado_por, finalidade=finalidade or None)
            return {"ok": True, **resumo}, 200
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
        except Exception as e:
            return _erro(e, "Erro ao importar saida")


@admin_bases_ns.route("/admin/bases/importar/estoque")
class ImportarEstoque(Resource):
    @admin_bases_ns.doc(description="Importa estoque de um XLS (HTML do Imoview)/XLSX/CSV. Campo de arquivo: 'arquivo'.")
    def post(self):
        f = _arquivo()
        if not f:
            return {"ok": False, "error": "Envie o arquivo no campo 'arquivo'"}, 400
        criado_por = request.form.get("criado_por")
        data_estoque = request.form.get("data_estoque")
        try:
            resumo = svc.processar_estoque(f, criado_por=criado_por, data_estoque=data_estoque)
            return {"ok": True, **resumo}, 200
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
        except Exception as e:
            return _erro(e, "Erro ao importar estoque")


@admin_bases_ns.route("/admin/bases/importar/dfimoveis-acessos")
class ImportarDfImoveisAcessos(Resource):
    @admin_bases_ns.doc(description="Importa o XLSX semanal de acessos e impressões do DFImóveis.")
    def post(self):
        f = _arquivo()
        if not f:
            return {"ok": False, "error": "Envie o XLSX no campo 'arquivo'"}, 400
        try:
            resumo = dfimoveis_service.importar_relatorio(
                f,
                data_relatorio=request.form.get("data_relatorio"),
                criado_por=request.form.get("criado_por"),
            )
            return {"ok": True, **resumo}, 200
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
        except Exception as e:
            return _erro(e, "Erro ao importar relatório DFImóveis")


@admin_bases_ns.route("/admin/bases/importar/leads-contact2sale")
class ImportarLeadsContact2Sale(Resource):
    @admin_bases_ns.doc(description="Importa leads da Contact2Sale para leads_legado/Fato_Lead. Use CONTACT2SALE_TOKEN no ambiente.")
    def post(self):
        data = request.get_json(silent=True) or {}
        try:
            resumo = leads_service.importar_contact2sale(
                data_de=data.get("data_de") or request.form.get("data_de"),
                data_ate=data.get("data_ate") or request.form.get("data_ate"),
                per_page=data.get("per_page") or request.form.get("per_page") or 50,
            )
            return {"ok": True, **resumo}, 200
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
        except Exception as e:
            return _erro(e, "Erro ao importar leads da Contact2Sale")


# =========================
# Captacao (manual + consulta)
# =========================
@admin_bases_ns.route("/admin/bases/captacao")
class Captacao(Resource):
    def get(self):
        page, per_page = _paginacao()
        try:
            return svc.listar_captacoes(_filtros(), page, per_page), 200
        except Exception as e:
            return _erro(e, "Erro ao listar captacoes")

    def post(self):
        data = request.get_json() or {}
        if not data.get("codigo"):
            return {"ok": False, "error": "codigo obrigatorio"}, 400
        try:
            res = svc.criar_captacao_manual(data, criado_por=data.get("criado_por"))
            return res, (200 if res.get("ok") else 400)
        except Exception as e:
            return _erro(e, "Erro ao criar captacao")


@admin_bases_ns.route("/admin/bases/saida")
class Saida(Resource):
    def get(self):
        page, per_page = _paginacao()
        try:
            return svc.listar_saidas(_filtros(), page, per_page), 200
        except Exception as e:
            return _erro(e, "Erro ao listar saidas")

    def post(self):
        data = request.get_json() or {}
        if not data.get("codigo"):
            return {"ok": False, "error": "codigo obrigatorio"}, 400
        try:
            res = svc.criar_saida_manual(data, criado_por=data.get("criado_por"))
            return res, (200 if res.get("ok") else 400)
        except Exception as e:
            return _erro(e, "Erro ao criar saida")


@admin_bases_ns.route("/admin/bases/estoque")
class Estoque(Resource):
    def get(self):
        page, per_page = _paginacao()
        try:
            return svc.listar_estoque(_filtros(), page, per_page), 200
        except Exception as e:
            return _erro(e, "Erro ao listar estoque")

    def post(self):
        data = request.get_json() or {}
        if not data.get("codigo"):
            return {"ok": False, "error": "codigo obrigatorio"}, 400
        try:
            res = svc.criar_estoque_manual(data, criado_por=data.get("criado_por"))
            return res, (200 if res.get("ok") else 400)
        except Exception as e:
            return _erro(e, "Erro ao criar estoque")


@admin_bases_ns.route("/admin/bases/leads")
class Leads(Resource):
    def get(self):
        page, per_page = _paginacao()
        try:
            return leads_service.listar_leads(page=page, per_page=per_page), 200
        except Exception as e:
            return _erro(e, "Erro ao listar leads")

    def post(self):
        data = request.get_json() or {}
        rows = data.get("rows") or data.get("leads") or []
        if not isinstance(rows, list):
            return {"ok": False, "error": "Envie rows como lista"}, 400
        try:
            resumo = leads_service.inserir_leads(rows)
            return {"ok": True, **resumo}, 200
        except Exception as e:
            return _erro(e, "Erro ao inserir leads")


# =========================
# Dimensoes (Tipo / Bairro)
# =========================
@admin_bases_ns.route("/admin/bases/tipos")
class Tipos(Resource):
    def get(self):
        try:
            return svc.listar_tipos(), 200
        except Exception as e:
            return _erro(e, "Erro ao listar tipos")

    def post(self):
        data = request.get_json() or {}
        try:
            res = svc.criar_tipo(data.get("nome"), data.get("id_tipo"))
            return res, (201 if res.get("ok") else 400)
        except Exception as e:
            return _erro(e, "Erro ao criar tipo")


@admin_bases_ns.route("/admin/bases/tipos/<int:id_>")
class TipoDetalhe(Resource):
    def put(self, id_):
        data = request.get_json() or {}
        try:
            res = svc.atualizar_tipo(id_, data.get("nome"))
            return res, (200 if res.get("ok") else 404)
        except Exception as e:
            return _erro(e, "Erro ao atualizar tipo")

    def delete(self, id_):
        try:
            res = svc.excluir_tipo(id_)
            return res, (200 if res.get("ok") else 404)
        except Exception as e:
            return _erro(e, "Erro ao excluir tipo")


@admin_bases_ns.route("/admin/bases/bairros")
class Bairros(Resource):
    def get(self):
        try:
            return svc.listar_bairros(), 200
        except Exception as e:
            return _erro(e, "Erro ao listar bairros")

    def post(self):
        data = request.get_json() or {}
        try:
            res = svc.criar_bairro(data.get("nome"))
            return res, (201 if res.get("ok") else 400)
        except Exception as e:
            return _erro(e, "Erro ao criar bairro")


@admin_bases_ns.route("/admin/bases/bairros/<int:id_>")
class BairroDetalhe(Resource):
    def put(self, id_):
        data = request.get_json() or {}
        try:
            res = svc.atualizar_bairro(id_, data.get("nome"))
            return res, (200 if res.get("ok") else 404)
        except Exception as e:
            return _erro(e, "Erro ao atualizar bairro")

    def delete(self, id_):
        try:
            res = svc.excluir_bairro(id_)
            return res, (200 if res.get("ok") else 404)
        except Exception as e:
            return _erro(e, "Erro ao excluir bairro")


# =========================
# Venda (cadastro enxuto em contratos) + Destaque
# =========================
@admin_bases_ns.route("/admin/bases/sync-contratos")
class SyncContratos(Resource):
    @admin_bases_ns.doc(description="Sincroniza a tabela contratos com a planilha Google (aba Vendas). Upsert por id_contrato.")
    def post(self):
        try:
            res = sync_contratos_from_sheet(criado_por=(request.get_json(silent=True) or {}).get("criado_por"))
            return res, (200 if res.get("ok") else 400)
        except Exception as e:
            return _erro(e, "Erro ao sincronizar contratos")


@admin_bases_ns.route("/admin/bases/venda")
class Venda(Resource):
    def get(self):
        page, per_page = _paginacao()
        try:
            return svc.listar_vendas(_filtros(), page, per_page), 200
        except Exception as e:
            return _erro(e, "Erro ao listar vendas")

    def post(self):
        data = request.get_json() or {}
        if not data.get("id_contrato"):
            return {"ok": False, "error": "id_contrato obrigatorio"}, 400
        try:
            res = svc.criar_venda(data, criado_por=data.get("criado_por"))
            return res, (201 if res.get("ok") else 400)
        except Exception as e:
            return _erro(e, "Erro ao criar venda")


@admin_bases_ns.route("/admin/bases/importar/destaque")
class ImportarDestaque(Resource):
    @admin_bases_ns.doc(description="Importa Destaque dos 3 XLSX (campos 'imoveis', 'seguros', 'assinados'). Faz full replace.")
    def post(self):
        imoveis = request.files.get("imoveis")
        seguros = request.files.get("seguros")
        assinados = request.files.get("assinados")
        if not (imoveis and imoveis.filename) or not (seguros and seguros.filename) or not (assinados and assinados.filename):
            return {"ok": False, "error": "Envie os 3 arquivos: 'imoveis', 'seguros' e 'assinados'"}, 400
        criado_por = request.form.get("criado_por")
        try:
            resumo = svc.processar_destaque(imoveis, seguros, assinados, criado_por=criado_por)
            return {"ok": True, **resumo}, 200
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
        except Exception as e:
            return _erro(e, "Erro ao importar destaque")


@admin_bases_ns.route("/admin/bases/destaque")
class Destaque(Resource):
    def get(self):
        page, per_page = _paginacao()
        try:
            return svc.listar_destaques(_filtros(), page, per_page), 200
        except Exception as e:
            return _erro(e, "Erro ao listar destaques")

    def post(self):
        data = request.get_json() or {}
        if not data.get("codigo"):
            return {"ok": False, "error": "codigo obrigatorio"}, 400
        try:
            res = svc.criar_destaque_manual(data, criado_por=data.get("criado_por"))
            return res, (201 if res.get("ok") else 400)
        except Exception as e:
            return _erro(e, "Erro ao criar destaque")
