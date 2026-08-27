"""Completa `fato_estoque` com os imoveis do catalogo que ainda nao estao la.

Por que existe
--------------
`fato_estoque` sempre foi alimentado por **upload de planilha** exportada a mao do
Imoview (`origem='upload'`), e so com os imoveis **Vago/Disponivel** — ~1.000 por leva,
tres levas em 2026 (26/06, 24/07, 03/08). Vendido, Desativado, Em moderacao e Em reforma
nunca entraram.

O bloqueio para automatizar era o captador: acreditava-se que a API nao o informava.
Ela informa — falta enviar **`exibircaptadores=true`** em `/Imovel/RetornarImoveis`. Com a
flag, `sync_areas_imoview.py` passou a gravar captador e percentual em `imovel_area`, com
cobertura de 97% (2.550 de 2.624 em 27/08/2026).

Este script pega o que existe no catalogo e nao existe em `fato_estoque` e insere.

O que ele NAO faz
-----------------
Nao reescreve nem apaga linha existente. Cada leva antiga continua onde esta — sao
snapshots datados, e reescreve-los apagaria o historico de quem cuidava do imovel antes.

Nao mexe em imovel que ja tem linha, mesmo que o captador tenha mudado. Para isso seria
outro script, e a decisao de qual fonte vence (planilha ou API) precisa ser tomada antes.

Por que inserir com a data de hoje e seguro
-------------------------------------------
Os tres consumidores (`ranking_service._responsavel_no_estoque`,
`leads_service._estoque_por_codigo`, `imovel_rel_service`) deduplicam por codigo pegando
`data_estoque` mais recente. Nenhum agrega uma leva inteira, entao uma leva parcial nao
distorce contagem de estoque.

Uso
---
    python completar_fato_estoque.py              # simula, nao grava
    python completar_fato_estoque.py --gravar
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

sys.path.insert(0, ".")

from app import create_app                                    # noqa: E402
from app.database import SessionLocal                          # noqa: E402
from app.models.fato_bases import FatoEstoque                  # noqa: E402
from app.models.imovel_area import ImovelArea                  # noqa: E402
from app.models.usuarios import Usuarios                       # noqa: E402
from app.services.ranking_service import RankingService        # noqa: E402

ORIGEM = "imoview_api"


def _equipe_do(uid: str, equipes: dict) -> str:
    """Equipe do captador principal. `fato_estoque.id_gerente` guarda o id da EQUIPE."""
    return equipes.get(str(uid or "").strip().upper(), "")


def coletar(session, servico, indice, equipes):
    """Linhas a inserir: catalogo menos o que ja esta em `fato_estoque`."""
    ja_tem = {
        str(c or "").strip()
        for (c,) in session.query(FatoEstoque.codigo_imovel).distinct().all()
        if str(c or "").strip()
    }

    novas, sem_captador = [], 0
    for area in session.query(ImovelArea).all():
        codigo = str(area.codigo or "").strip()
        if not codigo or codigo in ja_tem:
            continue

        # Nomes do catalogo -> ids do cadastro, com o mesmo resolvedor do fechamento
        # (prefixo por tokens, ativo vencendo homonimo). Sem ele, "IONNARA VIEIRA DE
        # ARAUJO" nao casaria com "Ionnara Vieira".
        ids = []
        for nome in (area.captador1, area.captador2, area.captador3):
            if not str(nome or "").strip():
                continue
            resolvido = servico._resolver_captador(nome, indice)
            # Guarda o id quando resolve; senao o nome cru, para nao perder a informacao.
            ids.append(resolvido)

        if not ids:
            sem_captador += 1

        novas.append({
            "codigo_imovel": codigo,
            "captador1": ids[0] if len(ids) > 0 else None,
            "captador2": ids[1] if len(ids) > 1 else None,
            "captador3": ids[2] if len(ids) > 2 else None,
            "id_gerente": _equipe_do(ids[0], equipes) if ids else None,
            "data_estoque": date.today(),
            "origem": ORIGEM,
            "arquivo_origem": "sync_areas_imoview (exibircaptadores)",
            "_situacao": area.situacao,
        })
    return novas, sem_captador


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gravar", action="store_true",
                   help="Grava de verdade. Sem isto, so mostra o que faria.")
    args = p.parse_args()

    app = create_app()
    with app.app_context():
        servico = RankingService()
        indice = servico._indice_captadores()

        session = SessionLocal()
        try:
            equipes = {
                str(u.id_usuarios).strip().upper(): str(u.team or "")
                for u in session.query(Usuarios).all()
            }
            novas, sem_captador = coletar(session, servico, indice, equipes)

            from collections import Counter
            por_situacao = Counter(x.pop("_situacao") or "(sem situacao)" for x in novas)

            print(f"imoveis a inserir: {len(novas)}")
            print(f"  sem captador no catalogo: {sem_captador}")
            print("  por situacao:")
            for sit, q in por_situacao.most_common():
                print(f"     {sit:<24} {q}")

            if not args.gravar:
                print()
                print("SIMULACAO — nada foi gravado. Use --gravar para valer.")
                for x in novas[:5]:
                    print(f"     {x['codigo_imovel']:<8} cap1={x['captador1']} "
                          f"gerente={x['id_gerente']}")
                return 0

            session.bulk_insert_mappings(FatoEstoque, novas)
            session.commit()
            print()
            print(f"GRAVADO: {len(novas)} linhas com data_estoque={date.today()}")
            return 0
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


if __name__ == "__main__":
    sys.exit(main())
