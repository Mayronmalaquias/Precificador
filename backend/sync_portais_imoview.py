"""Sincroniza a publicacao dos imoveis nos portais (Imoview -> `imovel_area`).

`POST /Imovel/RetornarPortaisImoveis` aceita ate 200 codigos por chamada e devolve, para
cada imovel, a lista de portais com situacao, tipo de destaque e dias de publicacao.
Consultando por codigos nao ha paginacao e vem portal em qualquer situacao — inclusive os
retirados, que e o que permite separar "publicado" de "ja esteve publicado".

Custo: 999 disponiveis de venda = 5 chamadas. O catalogo inteiro (12.450) = 63.

Por padrao roda so sobre o estoque de VENDA DISPONIVEL, que e o que a tela mostra e o
unico recorte em que "esta publicado?" e uma pergunta util — imovel vendido ou desativado
nao deveria estar em portal nenhum.

    python sync_portais_imoview.py            # so venda/disponivel
    python sync_portais_imoview.py --tudo     # catalogo inteiro
"""
from __future__ import annotations

import sys
import time
from datetime import datetime

import requests

sys.path.insert(0, ".")

from app import create_app                                      # noqa: E402
from app.database import SessionLocal                            # noqa: E402
from app.models.imovel_area import ImovelArea                    # noqa: E402
from app.services.imoview_service import IMOVIEW_BASE, _headers  # noqa: E402

ENDPOINT = f"{IMOVIEW_BASE}/Imovel/RetornarPortaisImoveis"
POR_LOTE = 200          # teto da API
PAUSA = 0.35            # mesma folga do sync de areas: o Imoview 401 sob rajada
TENTATIVAS = 4

# Situacao 1 = ativo; 2 = desativado/retirado do portal.
ATIVO = 1


def _pedir(codigos):
    """POST com retentativa. O 401 do Imoview e transitorio e mente sobre a causa."""
    corpo = {"codigosimoveis": ",".join(codigos)}
    ultimo = None
    for tentativa in range(1, TENTATIVAS + 1):
        r = requests.post(ENDPOINT, headers=_headers(), json=corpo, timeout=60)
        if r.status_code < 400:
            time.sleep(PAUSA)
            return r.json() or {}
        ultimo = r
        if r.status_code in (401, 429) or r.status_code >= 500:
            espera = 5 * (2 ** (tentativa - 1))
            print(f"  Imoview {r.status_code}; nova tentativa em {espera}s", file=sys.stderr)
            time.sleep(espera)
            continue
        break
    raise RuntimeError(f"Imoview HTTP {ultimo.status_code}: {ultimo.text[:200]}")


def _resumir(item):
    """Agrega os portais de um imovel no que a tela precisa."""
    portais = item.get("portais") or []
    ativos = [p for p in portais if int(p.get("codigosituacao") or 0) == ATIVO]

    # Maior nivel ENTRE OS ATIVOS. Portal retirado nao conta como destaque — o imovel
    # nao esta la.
    nivel, rotulo = None, None
    for p in ativos:
        try:
            n = int(p.get("codigotipodestaque") or 0)
        except (TypeError, ValueError):
            continue
        if n and (nivel is None or n > nivel):
            nivel, rotulo = n, str(p.get("tipodestaque") or "").strip() or None

    return {
        "portais_ativos": len(ativos),
        "portais_total": len(portais),
        "destaque_nivel": nivel,
        "destaque_portal": rotulo,
        "exibir_meu_site": bool(item.get("exibirmeusite")),
        "destaque_site": str(item.get("tipodestaquesite") or "").strip() or None,
        "portais_em": datetime.now(),
    }


def main() -> int:
    tudo = "--tudo" in sys.argv
    agora = datetime.now().isoformat(timespec="seconds")

    app = create_app()
    with app.app_context():
        session = SessionLocal()
        try:
            query = session.query(ImovelArea.codigo)
            if not tudo:
                query = query.filter(
                    ImovelArea.situacao.ilike("%dispon%"),
                    ImovelArea.finalidade == "Venda",
                )
            codigos = [str(c) for (c,) in query.all() if str(c or "").strip()]

            lidos = com_portal = 0
            for i in range(0, len(codigos), POR_LOTE):
                lote = codigos[i:i + POR_LOTE]
                dados = _pedir(lote)
                for item in (dados.get("lista") or []):
                    codigo = str(item.get("codigoimovel") or "").strip()
                    if not codigo:
                        continue
                    registro = session.query(ImovelArea).filter(
                        ImovelArea.codigo == codigo
                    ).first()
                    if not registro:
                        continue
                    resumo = _resumir(item)
                    for campo, valor in resumo.items():
                        setattr(registro, campo, valor)
                    lidos += 1
                    com_portal += 1 if resumo["portais_ativos"] else 0
                # Commit por lote: uma falha na chamada 40 nao joga fora as 39 anteriores.
                session.commit()
                print(f"  lote {i // POR_LOTE + 1}: {len(lote)} codigos", file=sys.stderr)

            print(f"[{agora}] portais imoview: consultados={len(codigos)} "
                  f"atualizados={lidos} publicados={com_portal}"
                  + (" [catalogo inteiro]" if tudo else " [venda/disponivel]"))
            return 0
        except Exception as e:
            session.rollback()
            print(f"[{agora}] sync de portais FALHOU: {e}", file=sys.stderr)
            return 1
        finally:
            session.close()


if __name__ == "__main__":
    sys.exit(main())
