"""Validacao e preservacao da previsao, sem acesso ao banco."""
from unittest.mock import MagicMock
from types import SimpleNamespace
import pytest
from app.services import proposta_service as ps
from app.models.proposta_efetiva import PropostaEfetiva


@pytest.mark.parametrize("nivel", ["alta", "media_alta", "media", "media_baixa", "baixa", "", None])
def test_probabilidades_validas(nivel):
    ps._validar({"probabilidade_fechamento": nivel}, parcial=True)


@pytest.mark.parametrize("dados", [{"probabilidade_fechamento": "muito_alta"}, {"fechamento_7_dias": "false"}, {"fechamento_7_dias": 1}, {"fechamento_7_dias": None}])
def test_rejeita_previsao_invalida(dados):
    with pytest.raises(ps.PropostaErro):
        ps._validar(dados, parcial=True)


def preparar(monkeypatch, edita=True, team="A"):
    proposta = PropostaEfetiva(id=1, ativo=True, team="A", situacao="em_analise",
                              fechamento_7_dias=True, probabilidade_fechamento="alta")
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = proposta
    monkeypatch.setattr(ps, "SessionLocal", lambda: session)
    monkeypatch.setattr(ps, "escopo_do_solicitante", lambda _: {
        "edita": edita, "ve_tudo": False, "team": team,
        "user": SimpleNamespace(id_usuarios="G1", nome="Gerente", username="gerente")})
    return proposta, session


def test_atualizacao_persiste_limpa_e_preserva_campos_omitidos(monkeypatch):
    proposta, session = preparar(monkeypatch)
    ps.atualizar("G1", 1, {"observacao": "Revisada"})
    assert proposta.fechamento_7_dias is True
    assert proposta.probabilidade_fechamento == "alta"
    ps.atualizar("G1", 1, {"fechamento_7_dias": False, "probabilidade_fechamento": ""})
    assert proposta.fechamento_7_dias is False
    assert proposta.probabilidade_fechamento is None
    assert proposta.ultima_acao_em is None
    ps.atualizar("G1", 1, {"fechamento_7_dias": True, "probabilidade_fechamento": "media_alta"})
    result = ps._serializar(proposta)
    assert result["fechamento_7_dias"] is True
    assert result["probabilidade_fechamento_label"] == "Média alta"
    assert session.commit.call_count == 3


@pytest.mark.parametrize("edita,team", [(False, "A"), (True, "B")])
def test_previsao_respeita_perfil_e_equipe(monkeypatch, edita, team):
    proposta, session = preparar(monkeypatch, edita, team)
    with pytest.raises(ps.PropostaErro) as exc:
        ps.atualizar("G1", 1, {"fechamento_7_dias": False})
    assert exc.value.status == 403
    assert proposta.fechamento_7_dias is True
    session.commit.assert_not_called()
