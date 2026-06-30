"""Importa vendas_legado (< 2024) para `contratos`, tornando contratos a base UNICA
completa (2015 -> hoje). Idempotente: pula id_contrato ja existente.

- vendas_legado guarda pessoa como codigo (C61xxx corretor / G61xxx equipe);
  resolve C->usuarios.nome e G->equipes.nome p/ casar a convencao de contratos (nome).
- valores/percentuais do legado sao Text -> parse numerico.
- marca fonte='legado_pre2024' (a sincronizacao com a planilha NAO toca nessas linhas).
"""

from app.database import SessionLocal
from app.models.contrato import Contrato
from app.models.equipe import Equipe
from app.models.usuarios import Usuarios
from app.models.venda_legado import VendaLegado
from app.services.admin_bases_service import parse_date_any, to_float, to_str

# legado_attr -> contrato_attr (copia direta, parse por tipo da coluna de contratos)
MAP_DIRETO = {
    "data_venda": "data_contrato",
    "bairro": "bairro",
    "tipo": "tipo",
    "valor_do_negocio": "valor_negocio",
    "valor_comissao": "valor_comissao",
    "valor_total_61": "valor_total_61",
    "percentual_comissao": "percentual_comissao_61",
    "nf_61_imovies": "nf_61_imoveis",
    "liquido_61": "liquido_61",
    "origemleadvenda": "origem_lead",
    "percentual_vendedor_1": "percentual_corretor_venda_1",
    "valor_vendedor_1": "valor_corretor_venda_1",
    "percentual_vendedor_2": "percentual_corretor_venda_2",
    "valor_vendedor_2": "valor_corretor_venda_2",
    "percentual_captador_1": "percentual_corretor_captacao_1",
    "valor_captador_1": "valor_corretor_captador_1",
    "percentual_captador_2": "percentual_corretor_captacao_2",
    "valor_captador_2": "valor_corretor_captador_2",
    "percentual_gerente_venda_1": "percentual_gerente_venda",
    "valor_gerente_venda_1": "valor_gerente_venda",
    "percentualgerente_de_captacao_1": "percentual_gerente_captacao",
    "valor_gerente_de_captacao_1": "valor_gerente_captacao",
}
# legado_attr (codigo de pessoa) -> contrato_attr (nome)
MAP_PESSOA = {
    "vendedor_1": "corretor_venda_1_nome",
    "vendedor_2": "corretor_venda_2_nome",
    "captador_1": "corretor_captador_1_nome",
    "captador_2": "corretor_captador_2_nome",
    "gerente_de_venda1": "gerente_venda_nome",
    "gerente_de_captacao_1": "gerente_captacao_nome",
}

_COL_TYPE = {c.name: type(c.type).__name__ for c in Contrato.__table__.columns}


def _parse_para(attr, raw):
    t = _COL_TYPE.get(attr)
    if t == "Date":
        return parse_date_any(raw)
    if t in ("Numeric", "DECIMAL"):
        s = to_str(raw)
        return to_float(s) if s else None
    return to_str(raw) or None


def main():
    session = SessionLocal()
    try:
        usuarios = {to_str(u.id_usuarios): to_str(u.nome) for u in session.query(Usuarios.id_usuarios, Usuarios.nome).all() if to_str(u.id_usuarios)}
        equipes = {to_str(e.id_equipe): to_str(e.nome) for e in session.query(Equipe.id_equipe, Equipe.nome).all()}
        existentes = {c.id_contrato for c in session.query(Contrato.id_contrato).all()}

        def resolve(code):
            c = to_str(code)
            if not c:
                return None
            return usuarios.get(c) or equipes.get(c) or c  # nome, senao codigo cru

        legados = session.query(VendaLegado).filter(VendaLegado.data_venda < __import__("datetime").date(2024, 1, 1)).all()
        inseridos, pulados = 0, 0
        novos = []
        for v in legados:
            idc = to_str(v.idcontrato)
            if not idc or idc in existentes:
                pulados += 1
                continue
            dados = {"id_contrato": idc, "fonte": "legado_pre2024"}
            for la, ca in MAP_DIRETO.items():
                dados[ca] = _parse_para(ca, getattr(v, la, None))
            for la, ca in MAP_PESSOA.items():
                dados[ca] = resolve(getattr(v, la, None))
            novos.append(Contrato(**dados))
            existentes.add(idc)
            inseridos += 1

        session.add_all(novos)
        session.commit()
        print(f"importados pre-2024: {inseridos} | pulados (sem id / ja existia): {pulados}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
