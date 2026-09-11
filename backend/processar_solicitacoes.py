"""python processar_solicitacoes.py [--loop]; executar fora do Gunicorn."""
import argparse
import logging
import time
from dotenv import load_dotenv
load_dotenv()
from app.services.solicitacao_worker import executar

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    while True:
        inicio = time.monotonic()
        try:
            logging.info("Solicitações: %s", executar())
        except Exception as exc:
            logging.error("Worker de solicitações: %s", type(exc).__name__)
            if not args.loop:
                raise SystemExit(1)
        if not args.loop:
            break
        time.sleep(max(1, 900 - (time.monotonic() - inicio)))
