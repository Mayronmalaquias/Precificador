"""Espelha os leads do Contact2Sale em `leads_c2s` (rodar via cron, de hora em hora).

Por que existe: a tela de leads lia a API ao vivo a cada consulta filtrada. Como a API do
C2S nao filtra por equipe, portal nem motivo, qualquer recorte varria o periodo inteiro a
10 requisicoes por minuto — minutos de espera por clique. Aqui a varredura roda fora do
caminho do usuario e a tela le do banco.

**Lead ja importado muda.** Situacao, etapa do funil, arquivamento e motivo do
arquivamento sao decididos depois que o lead entrou. O sync e UPSERT por `id_c2s`, entao
a passada horaria ATUALIZA o que ja esta la — o importador antigo (`importar_leads_c2s`,
que alimenta `leads_legado`) so insere e pula duplicado, congelando o lead no estado do
dia em que chegou. Os dois convivem: `leads_legado` e a base do relatorio historico e
passa por filtro de negocio; `leads_c2s` e copia crua.

Uso (cwd = backend/):

    # passada horaria: pega quem MUDOU desde a ultima sincronizacao
    venv/bin/python sync_leads_c2s.py

    # carga inicial (~52 mil leads, ~1044 paginas, ~1h45 no teto de 10 req/min)
    venv/bin/python sync_leads_c2s.py --inicial

    # janela explicita, por data de criacao
    venv/bin/python sync_leads_c2s.py --de 2026-06-01 --ate 2026-06-30 --por criacao

Cron sugerido (VM roda em UTC):

    5 * * * * cd /caminho/Precificador/backend && venv/bin/python sync_leads_c2s.py \\
        >> /var/log/precificador/leads_c2s.log 2>&1
"""
import argparse
import json
import sys
from datetime import datetime

from app.services import lead_sync_service as sync


def main() -> int:
    p = argparse.ArgumentParser(description="Sincroniza leads do Contact2Sale.")
    p.add_argument("--de", help="Data inicial (YYYY-MM-DD). Sem ela, retoma da marca d'agua.")
    p.add_argument("--ate", help="Data final (YYYY-MM-DD). Padrao: amanha.")
    p.add_argument("--por", choices=["criacao", "atualizacao"], default="atualizacao",
                   help="Campo da janela. 'atualizacao' (padrao) pega quem mudou.")
    p.add_argument("--inicial", action="store_true",
                   help="Carga inicial: varre por data de CRIACAO desde 2020.")
    p.add_argument("--max-paginas", type=int, default=sync.MAX_PAGINAS)
    args = p.parse_args()

    inicio, por = args.de, args.por
    if args.inicial:
        # Carga inicial vai por criacao: `updated_at` de lead antigo pode ser recente, e
        # varrer por atualizacao deixaria buracos de leads nunca tocados desde a entrada.
        inicio, por = inicio or "2020-01-01", "criacao"

    campo = "created" if por == "criacao" else "updated"
    comeco = datetime.now()
    try:
        resumo = sync.sincronizar(inicio=inicio, fim=args.ate, campo_data=campo,
                                  max_paginas=args.max_paginas)
    except sync.SyncErro as e:
        print(json.dumps({"ok": False, "erro": e.mensagem}, ensure_ascii=False))
        return 1

    resumo["segundos"] = round((datetime.now() - comeco).total_seconds(), 1)
    resumo["estado"] = sync.estado()
    print(json.dumps(resumo, ensure_ascii=False, default=str))
    # Parcial nao e falha: as paginas lidas ja tiveram commit e a proxima passada retoma
    # pela marca d'agua. Sai 2 para o cron distinguir no log sem disparar alarme de erro.
    return 2 if resumo.get("parcial") else 0


if __name__ == "__main__":
    sys.exit(main())
