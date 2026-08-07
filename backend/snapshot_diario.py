"""Snapshot diario da Jornada de Captacao (rodar via cron na VM do back).

Grava o estado atual de todas as captacoes no dia de hoje. Idempotente: rodar 2x no
mesmo dia regrava o dia (nao duplica). Sem esse cron a evolucao "congela" no ultimo
dia com snapshot — foi o que aconteceu entre 22/07 e 07/08/2026.

Uso (cwd precisa ser o backend/ — o config le o .env via load_dotenv):
    cd /caminho/Precificador/backend && venv/bin/python snapshot_diario.py

Buraco no historico (dias sem snapshot) nao e resolvido por aqui: usa o backfill,
que reconstroi tudo a partir de captacao + captacao_historico (faz TRUNCATE antes):
    venv/bin/python -c "from app.services import captacao_snapshot_service as s; print(s.backfill())"
"""
import sys
from datetime import datetime

from app.services import captacao_snapshot_service as snap_svc

if __name__ == "__main__":
    agora = datetime.now().isoformat(timespec="seconds")
    try:
        resultado = snap_svc.gerar_snapshot()
        print(f"[{agora}] snapshot ok: dia={resultado['dia']} linhas={resultado['linhas']}")
    except Exception as e:
        print(f"[{agora}] snapshot FALHOU: {e}", file=sys.stderr)
        sys.exit(1)
