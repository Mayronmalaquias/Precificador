"""Importa no banco o relatório XLSX DFImóveis já presente no repositório.

Uso (depois de aplicar a migration):
    python importar_dfimoveis_xlsx.py "../legado/Relatorio-de-acesso-imoveis-04_08_2026 17_02_25.xlsx"
"""
import sys
from pathlib import Path

from werkzeug.datastructures import FileStorage

from app import create_app
from app.services.dfimoveis_service import importar_relatorio


def main():
    default = Path(__file__).resolve().parent.parent / "legado" / "Relatorio-de-acesso-imoveis-04_08_2026 17_02_25.xlsx"
    path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default
    if not path.is_file():
        raise SystemExit(f"Arquivo não encontrado: {path}")
    app = create_app()
    with app.app_context(), path.open("rb") as stream:
        result = importar_relatorio(FileStorage(stream=stream, filename=path.name))
    print(result)


if __name__ == "__main__":
    main()
