"""Importa os leads da Contact2Sale do dia anterior (rodar via cron na VM do back).

Alimenta `leads_legado`, que e a fonte do KPI "Leads C2S" da Visao do Diretor e dos
relatorios de lead. Idempotente: o service deduplica por `_dedupe_key`/`_existe_lead`,
entao rodar 2x no mesmo dia nao duplica.

Precisa de CONTACT2SALE_TOKEN no .env do backend. Uso (cwd = backend/):
    cd /caminho/Precificador/backend && venv/bin/python importar_leads_c2s.py

Aceita um intervalo p/ backfill manual (YYYY-MM-DD):
    venv/bin/python importar_leads_c2s.py 2026-06-22 2026-08-07
"""
import sys
from datetime import date, datetime, timedelta

from app.services import leads_service

if __name__ == "__main__":
    ontem = (date.today() - timedelta(days=1)).isoformat()
    de = sys.argv[1] if len(sys.argv) > 1 else ontem
    ate = sys.argv[2] if len(sys.argv) > 2 else de
    agora = datetime.now().isoformat(timespec="seconds")
    try:
        r = leads_service.importar_contact2sale(de, ate, 50)
        print(f"[{agora}] leads c2s {r['data_de']}..{r['data_ate']}: api={r['total_api']} "
              f"inseridos={r['inseridos']} duplicados={r['ignorados_duplicados']} ignorados={r['ignorados']}")
    except Exception as e:
        print(f"[{agora}] import c2s FALHOU ({de}..{ate}): {e}", file=sys.stderr)
        sys.exit(1)
