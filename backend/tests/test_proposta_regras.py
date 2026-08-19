"""Testes puros das regras de proposta e do recorte de periodo do painel.

Nao tocam o banco: exercitam so as funcoes de calculo/validacao. Para os casos que
precisam de sessao (card x funil), use um Postgres descartavel — apontar a fixture
para producao GRAVA nela.

    cd backend && python -m pytest tests/ -v
"""
import ast
import inspect
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import diretor_dashboard_service as dd
from app.services import proposta_service as ps


# ── regressao: _data() duplicada quebrava toda criacao de proposta ────────────────

def test_data_aceita_vazio_none_e_retroativa():
    """A 2a definicao de _data() nao tratava None e estourava ValueError.

    Como o formulario nao manda `data_fechamento`, TODA criacao de proposta caia.
    """
    assert ps._data(None) is None
    assert ps._data("") is None
    assert ps._data("2026-06-01") == date(2026, 6, 1)
    assert ps._data(date(2026, 6, 1)) == date(2026, 6, 1)
    assert ps._data(datetime(2026, 6, 1, 10, 30)) == date(2026, 6, 1)
    assert ps._data("nao e data") is None


@pytest.mark.parametrize("modulo", [ps, dd])
def test_sem_funcao_duplicada_no_modulo(modulo):
    """Trava o shadow: Python usa em silencio a ultima definicao do modulo."""
    arvore = ast.parse(inspect.getsource(modulo))
    nomes = [n.name for n in arvore.body if isinstance(n, ast.FunctionDef)]
    repetidos = {n for n in nomes if nomes.count(n) > 1}
    assert not repetidos, f"funcao definida mais de uma vez: {sorted(repetidos)}"


# ── A-8: fronteira de dia entre o calendario brasileiro e o UTC do banco ──────────

def test_periodo_cobre_o_dia_brasileiro_inteiro():
    inicio, fim = dd._intervalo_utc(date(2026, 8, 10), date(2026, 8, 10))
    # 00h00 de Brasilia = 03h00 UTC do mesmo dia.
    assert inicio == datetime(2026, 8, 10, 3, 0)
    # 23h59:59.999999 de Brasilia = 02h59 UTC do dia seguinte.
    assert fim == datetime(2026, 8, 11, 2, 59, 59, 999999)


def test_proposta_lancada_a_noite_cai_no_dia_certo():
    """21h30 de Brasilia grava created_at as 00h30 UTC do dia seguinte."""
    criada_em_utc = datetime(2026, 8, 11, 0, 30)
    inicio, fim = dd._intervalo_utc(date(2026, 8, 10), date(2026, 8, 10))
    assert inicio <= criada_em_utc <= fim

    # E nao pode vazar para o dia seguinte.
    inicio_11, fim_11 = dd._intervalo_utc(date(2026, 8, 11), date(2026, 8, 11))
    assert not (inicio_11 <= criada_em_utc <= fim_11)


def test_intervalo_do_servico_e_do_painel_coincidem():
    """A listagem e o card tem que recortar o periodo do mesmo jeito."""
    dia = date(2026, 8, 10)
    assert (ps._inicio_utc(dia), ps._fim_utc(dia)) == dd._intervalo_utc(dia, dia)


# ── A-7: dias em aberto para de contar no fechamento ──────────────────────────────

def _proposta(**kw):
    base = dict(situacao="em_analise", data_proposta=date(2026, 8, 1),
                data_fechamento=None, ultima_acao_em=None,
                updated_at=None, created_at=None)
    base.update(kw)
    return SimpleNamespace(**base)


def test_aberta_conta_ate_hoje():
    p = _proposta()
    assert ps._fim_da_contagem(p, date(2026, 8, 19)) == date(2026, 8, 19)


def test_fechada_com_data_para_na_data():
    p = _proposta(situacao="vendido", data_fechamento=date(2026, 8, 5))
    assert ps._fim_da_contagem(p, date(2026, 8, 19)) == date(2026, 8, 5)


def test_fechada_sem_data_para_na_ultima_acao():
    """Antes caia no `hoje` e o contador crescia depois de a proposta ja ter acabado."""
    p = _proposta(situacao="recusada", ultima_acao_em=datetime(2026, 8, 6, 14, 0))
    assert ps._fim_da_contagem(p, date(2026, 8, 19)) == date(2026, 8, 6)


# ── A-9: o card conta TODAS as situacoes, inclusive cancelada e recusada ──────────

def test_situacoes_fechadas_declaradas():
    """Decisao de produto: cancelada e recusada CONTAM no volume do card.

    O card e volume de proposta, nao de fechamento. Este teste existe para que a
    mudanca desse comportamento seja deliberada, e nao um efeito colateral.
    """
    assert ps.SITUACOES_FECHADAS == ("aceita", "vendido", "recusada", "cancelada")
    assert set(ps.SITUACOES) == {
        "em_analise", "contraproposta", "aceita", "vendido", "recusada", "cancelada",
    }
    fonte = inspect.getsource(dd._propostas_efetivas)
    assert "situacao" not in fonte, (
        "o card passou a filtrar por situacao — se foi de proposito, atualize este teste "
        "e o comentario de A-9 no plano de QA"
    )


# ── A-1: card e funil usam a mesma regra de dono ──────────────────────────────────

def test_dono_da_proposta_e_corretor_senao_gerente():
    expr = str(dd._DONO_DA_PROPOSTA)
    assert "coalesce" in expr.lower()
    assert "id_corretor" in expr and "id_gerente" in expr


def test_card_e_funil_usam_a_mesma_expressao():
    """Se um dos dois voltar a ter regra propria, os numeros divergem de novo."""
    assert "_DONO_DA_PROPOSTA" in inspect.getsource(dd._propostas_efetivas)
    assert "_DONO_DA_PROPOSTA" in inspect.getsource(dd._funil)


# ── validacoes de criacao ─────────────────────────────────────────────────────────

def test_num_rejeita_vazio_e_texto():
    assert ps._num(None) is None
    assert ps._num("") is None
    assert ps._num("abc") is None


def test_num_devolve_decimal_exato():
    """Dinheiro nao passa por float em lugar nenhum — nem aqui, nem na mascara do front."""
    assert ps._num("1234.56") == Decimal("1234.56")
    assert ps._num("1.234,56") == Decimal("1234.56")
    assert ps._num("R$ 6.555.555,55") == Decimal("6555555.55")
    assert isinstance(ps._num("1234.56"), Decimal)


def test_validar_recusa_situacao_e_forma_desconhecidas():
    with pytest.raises(ps.PropostaErro) as e:
        ps._validar({"situacao": "vendida"})
    assert "Situação inválida" in e.value.mensagem

    with pytest.raises(ps.PropostaErro) as e:
        ps._validar({"forma_pagamento": "boleto"})
    assert "Forma de pagamento inválida" in e.value.mensagem


def test_validar_aceita_o_caso_normal():
    situacao, forma = ps._validar({"situacao": "em_analise", "forma_pagamento": "permuta"})
    assert (situacao, forma) == ("em_analise", "permuta")
