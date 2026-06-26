"""Popula a tabela canonica `vendas` a partir de vw_vendas (Etapa B passo 2).

Re-executavel: TRUNCATE + reload. NAO toca em contratos/vendas_legado (fontes brutas).
- valor: parseado com to_float (BR-aware); vazio -> NULL.
- *_nome: nome humano de usuarios quando o id resolveu; senao a ref original (nome/codigo).
"""

from sqlalchemy import text

from app.database import engine
from app.services.admin_bases_service import to_float, to_str


def money(x):
    s = to_str(x)
    return to_float(s) if s else None


def main():
    with engine.connect() as c:
        nome_map = {
            r[0]: r[1]
            for r in c.execute(text("select id_usuarios, nome from usuarios where id_usuarios is not null"))
        }
        rows = list(c.execute(text("""
            select fonte, id_contrato, data_venda, data_captacao, bairro, tipo, codigo_imovel,
                   valor_negocio, valor_comissao,
                   vendedor_ref, vendedor_id, captador_ref, captador_id,
                   gerente_venda_ref, gerente_venda_id, gerente_captacao_ref, gerente_captacao_id,
                   diretor_ref, diretor_id
            from vw_vendas
        """)))

    def nome(idv, ref):
        return nome_map.get(idv) or (to_str(ref) or None)

    payload = []
    for r in rows:
        (fonte, id_contrato, data_venda, data_captacao, bairro, tipo, codigo_imovel,
         vneg, vcom, vded_ref, vded_id, cap_ref, cap_id, gv_ref, gv_id, gc_ref, gc_id, dir_ref, dir_id) = r
        payload.append({
            "fonte": fonte, "id_contrato": to_str(id_contrato) or None,
            "data_venda": data_venda, "data_captacao": data_captacao,
            "bairro": to_str(bairro) or None, "tipo": to_str(tipo) or None,
            "codigo_imovel": to_str(codigo_imovel) or None,
            "valor_negocio": money(vneg), "valor_comissao": money(vcom),
            "vendedor_nome": nome(vded_id, vded_ref), "vendedor_id": vded_id,
            "captador_nome": nome(cap_id, cap_ref), "captador_id": cap_id,
            "gerente_venda_nome": nome(gv_id, gv_ref), "gerente_venda_id": gv_id,
            "gerente_captacao_nome": nome(gc_id, gc_ref), "gerente_captacao_id": gc_id,
            "diretor_nome": nome(dir_id, dir_ref), "diretor_id": dir_id,
        })

    ins = text("""
        INSERT INTO vendas (fonte, id_contrato, data_venda, data_captacao, bairro, tipo, codigo_imovel,
            valor_negocio, valor_comissao,
            vendedor_nome, vendedor_id, captador_nome, captador_id,
            gerente_venda_nome, gerente_venda_id, gerente_captacao_nome, gerente_captacao_id,
            diretor_nome, diretor_id)
        VALUES (:fonte,:id_contrato,:data_venda,:data_captacao,:bairro,:tipo,:codigo_imovel,
            :valor_negocio,:valor_comissao,
            :vendedor_nome,:vendedor_id,:captador_nome,:captador_id,
            :gerente_venda_nome,:gerente_venda_id,:gerente_captacao_nome,:gerente_captacao_id,
            :diretor_nome,:diretor_id)
    """)
    with engine.begin() as c:
        c.execute(text("TRUNCATE TABLE vendas RESTART IDENTITY"))
        c.execute(ins, payload)
    print(f"vendas populada: {len(payload)} linhas")


if __name__ == "__main__":
    main()
