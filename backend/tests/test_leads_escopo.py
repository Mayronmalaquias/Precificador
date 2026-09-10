"""Regressoes de isolamento de equipes; somente SQLite em memoria e mocks."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.lead_c2s import LeadC2S
from app.models.estoque_legado import LeadLegado
from app.services import lead_c2s_service as c2s
from app.services import lead_gestao_service as gestao


@pytest.mark.parametrize("team,nome", [("", None), ("G61016", None), ("G61016", " ")])
def test_gerente_sem_equipe_valida_nao_ganha_escopo_global(team, nome):
    session = Mock()
    user = SimpleNamespace(permissao="gerente", team=team)
    session.query.return_value.filter.return_value.first.side_effect = [
        user, SimpleNamespace(nome=nome),
    ]
    with pytest.raises(c2s.LeadC2SErro) as exc:
        c2s._escopo(session, "gerente", "AGEF")
    assert exc.value.status == 403


def test_gerente_nao_pode_pedir_outra_equipe():
    session = Mock()
    session.query.return_value.filter.return_value.first.side_effect = [
        SimpleNamespace(permissao="gerente", team="G61016"),
        SimpleNamespace(nome="LIDER"),
    ]
    assert c2s._escopo(session, "G61016", "AGEF") == {
        "ve_tudo": False, "equipe": "LIDER", "corretor": "",
    }


def test_listagem_e_historico_excluem_agef_mesmo_com_corretor_da_lider():
    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        conn.connection.driver_connection.create_function(
            "translate", 3, lambda value, src, dst:
            value.translate(str.maketrans(src, dst)) if value else value,
        )
    with Session(engine) as session:
        session.execute(text("CREATE TABLE leads_c2s (id_c2s TEXT, equipe TEXT)"))
        session.execute(text("INSERT INTO leads_c2s VALUES ('1', 'AGEF'), ('2', 'LÍDER')"))
        session.execute(text("CREATE TABLE leads_legado (id INTEGER, equipe TEXT, atendimento TEXT)"))
        session.execute(text("INSERT INTO leads_legado VALUES (1, 'AGEF', 'corretor_lider'), (2, 'G61016', 'corretor_lider')"))
        escopo = {"ve_tudo": False, "equipe": "LIDER", "corretor": ""}
        query = c2s._aplicar_filtros(session.query(LeadC2S.id_c2s), {}, escopo)
        assert query.all() == [("2",)]
        equipes = Mock()
        equipes.query.return_value.all.return_value = [SimpleNamespace(id_equipe="G61016", nome="LIDER")]
        with patch.object(c2s, "_escopo", return_value=escopo), patch.object(
            gestao, "_filtro_de_escopo", return_value=["corretor_lider", "G61016"]
        ):
            query = gestao._aplicar_escopo_legado(
                session.query(LeadLegado.id), equipes, {"id": "G61016"}
            )
            assert query.all() == [(2,)]
