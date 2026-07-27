"""Sync contratos <- planilha Google (aba Vendas) + refresh da tabela canonica vendas.

Para rodar no cron da VM, mantendo contratos sempre atualizada:
  */30 * * * * cd /home/ubuntu/Precificador/back-end && \
    /home/ubuntu/Precificador/back-end/venv/bin/python sync_contratos.py > ~/sync_contratos.log 2>&1

(usa '>' e nao '>>' pro log nao crescer e encher o disco)
"""

import json
import sys

from app.services.sync_contratos_service import sync_contratos_from_sheet


def main():
    res = sync_contratos_from_sheet()
    print("[sync contratos]", json.dumps({k: v for k, v in res.items() if k != "erros"}, ensure_ascii=False))
    if res.get("erros"):
        print("erros:", res["erros"][:10])
    if not res.get("ok"):
        sys.exit(1)

    # refresca a tabela canonica vendas (depende de contratos)
    try:
        from popula_vendas import main as popula_vendas_main
        popula_vendas_main()
    except Exception as e:
        print("[refresh vendas] FALHOU:", e)


if __name__ == "__main__":
    main()
