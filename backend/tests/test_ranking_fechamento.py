from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.services.ranking_service import RankingService


@pytest.mark.parametrize("vazio", [False, True])
def test_fechamento_segue_ranking_sem_rateio(monkeypatch, vazio):
    service = RankingService.__new__(RankingService)
    service.excluded_ids = {"H"}
    service.excluded_names = set()
    nomes = {"A": "ANA", "B": "BRUNO", "H": "OCULTO"}
    monkeypatch.setattr(service, "_maps_corretores", lambda: (nomes, {}))
    # A e B participam da mesma captacao: credito inteiro para ambos.
    monkeypatch.setattr(service, "load_captacao", lambda start, end: pd.DataFrame(
        {"Captador": [] if vazio else ["A", "B", "H", "SEM CADASTRO"]}))
    monkeypatch.setattr(service, "_captacoes_rateadas", lambda *args: pytest.fail("Nao deve ratear"))
    equipe = SimpleNamespace(id_equipe=1, nome="Equipe A")
    usuarios = [SimpleNamespace(id_usuarios=k, nome=n, team=1, ativo=k != "B",
                               permissao="corretor")
                for k, n in {**nomes, "Z": "SEM CAPTACAO"}.items()]
    session = MagicMock()
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [equipe]
    session.query.return_value.all.return_value = usuarios
    monkeypatch.setattr("app.database.SessionLocal", lambda: session)

    dados = service.fechamento("2026-09")
    texto = service.gerar_texto_fechamento("2026-09", dados=dados)
    assert "OCULTO" not in texto
    assert "SEM CAPTACAO" not in texto
    assert dados["resumo"]["total_ranking"] == (0 if vazio else 3)
    if vazio:
        assert dados["equipes"] == []
        assert dados["orfas"] == []
    else:
        assert {x["nome"]: x["total"] for x in dados["equipes"][0]["linhas"]} == {"ANA": 1, "BRUNO": 1}
        assert dados["equipes"][0]["total"] == 2
        assert dados["orfas"] == [{"nome": "SEM CADASTRO", "total": 1}]
        assert "ANA: 1/4" in texto
        assert "BRUNO (saiu): 1" in texto
