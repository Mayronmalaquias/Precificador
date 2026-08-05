"""Lançamento de imóvel pelos assistentes (uma vez só): Imoview + Trello.

Recebe os campos do formulário (subconjunto da planilha antiga + obrigatórios do
Imoview), monta o JSON `parametros` do Imoview, inclui o imóvel e, com o código
retornado, cria o cartão no Trello. Substitui o lançamento duplo (planilha→Trello +
Imoview manual).
"""
from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List, Optional

from app.services import imoview_service, trello_service

# Planilha "Estoque - Geral" (aba onde o lançamento grava). ID configurável via env.
SHEET_ESTOQUE_ID = os.getenv("GSHEET_ESTOQUE_ID", "1869RJIoK064xnXjMHDXP0tNan5bkbJPZa-_jVfwY1cY")
SHEET_ESTOQUE_ABA = os.getenv("GSHEET_ESTOQUE_ABA", "Planilha - Geral")


def _persistir_foco(dados: Dict[str, Any], codigo: Any) -> Dict[str, Any]:
    """Classifica o foco (regra de bairro/valor/comissão) e grava em `imovel_legado`
    (foco_pp/foco_ac), keyado pelo código do Imoview. É o que a classificação de foco do
    ranking lê — sem isso o imóvel aparece como 'NÃO LOCALIZADO'."""
    from app.database import SessionLocal
    from app.services import admin_bases_service as abs_

    session = SessionLocal()
    try:
        bairro = dados.get("bairro") or ""
        valor = _num(dados.get("valor")) or 0.0
        comissao = _num(dados.get("comissao")) or 0.0
        # residencial pela destinação do Imoview (1=Residencial, 3=Residencial/Comercial)
        is_res = str(dados.get("destinacao") or "").strip() in {"1", "3"}

        foco_pp, foco_ac = abs_.classificar_foco(bairro, valor, comissao, is_res)

        mapas = abs_.carregar_mapas(session)
        bairro_id, _ = abs_.ensure_bairro(session, mapas, bairro)
        abs_.upsert_imovel_legado(session, str(codigo), None, valor, bairro_id, foco_pp, foco_ac)
        session.commit()
        return {"ok": True, "foco_pp": foco_pp, "foco_ac": foco_ac}
    except Exception as e:
        session.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def _foco_label(foco: Dict[str, Any]) -> str:
    """Rótulo p/ a coluna Foco da planilha de estoque."""
    if not foco or not foco.get("ok"):
        return ""
    if foco.get("foco_pp") and foco.get("foco_ac"):
        return "FOCO PP + AC"
    if foco.get("foco_pp"):
        return "FOCO PP"
    if foco.get("foco_ac"):
        return "FOCO AC"
    return "NÃO FOCO"


def _gravar_estoque_sheet(dados: Dict[str, Any], codigo: Any, foco_label: str = "") -> Dict[str, Any]:
    """Anexa uma linha na planilha de estoque (mesma ordem de colunas do cabeçalho)."""
    from app.services.google_service import get_services

    endereco = " ".join(str(x) for x in [dados.get("rua"), dados.get("numero")] if x).strip()
    cessao = "Sim" if _bool(dados.get("cessao_direitos")) else "Não"
    # 32 colunas, na ordem da aba "Planilha - Geral".
    linha = [
        dados.get("corretor_nome") or "",            # 0  Corretor
        str(codigo or ""),                            # 1  Código
        dados.get("matricula") or "",                 # 2  Matrícula
        dados.get("inscricao_iptu") or "",            # 3  Inscrição IPTU
        endereco,                                     # 4  Endereço
        dados.get("bairro") or "",                    # 5  Região
        dados.get("valor") or "",                     # 6  Valor
        date.today().strftime("%d/%m/%Y"),            # 7  Data da Captação
        "", "", "", "", "", "",                       # 8-13 Status..Imóvel Seguro
        dados.get("comissao") or "",                  # 14 Comissão
        foco_label,                                   # 15 Foco (classificação computada)
        "",                                           # 16 Roleta
        dados.get("valoriptu") or "",                 # 17 IPTU
        dados.get("valorcondominio") or "",           # 18 Condomínio
        "", "",                                       # 19-20 Obs. Internas, Características
        dados.get("descricao") or "",                 # 21 Texto
        "", "", "", "",                               # 22-25 Fotos, Parecer, DataRoleta, ValorRoleta
        "Sim",                                        # 26 Lançado Trello (cartão criado direto aqui)
        dados.get("assistente_nome") or "",           # 27 Assistente
        cessao,                                       # 28 Cessão de Direitos
        "", "", "",                                   # 29-31 Observação, Video, Data Doc. CQC
    ]
    sheets, _, _ = get_services()
    sheets.values().append(
        spreadsheetId=SHEET_ESTOQUE_ID,
        range=f"'{SHEET_ESTOQUE_ABA}'!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [linha]},
    ).execute()
    return {"ok": True}


def _num(v: Any) -> Optional[float]:
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(".", "").replace(",", ".")) if isinstance(v, str) and "," in v else float(v)
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> Optional[int]:
    n = _num(v)
    return int(n) if n is not None else None


def _bool(v: Any) -> bool:
    return str(v).strip().lower() in {"true", "1", "sim", "on", "yes"}


def _limpo(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove chaves None/'' (Imoview assume default nos opcionais ausentes)."""
    return {k: v for k, v in d.items() if v not in (None, "")}


def montar_parametros_imoview(dados: Dict[str, Any]) -> Dict[str, Any]:
    """Mapeia o payload do form → estrutura `parametros` do /Imovel/IncluirImovel."""
    # Os códigos (usuario/unidade/finalidade/destinacao/tipo/localchave) precisam ser INT —
    # o Imoview (.NET) dá null-reference se vierem como string.
    parametros: Dict[str, Any] = _limpo({
        "codigousuario": _int(dados.get("codigousuario")),
        "codigounidade": _int(dados.get("codigounidade")),
        "finalidade": _int(dados.get("finalidade")),
        "destinacao": _int(dados.get("destinacao")),
        "codigotipo": _int(dados.get("codigotipo")),
        "localchave": _int(dados.get("localchave")),
        "codigoauxiliar": dados.get("codigoauxiliar"),
        "exclusivo": _bool(dados.get("exclusivo")),
        "descricao": dados.get("descricao"),
        "anotacoes": dados.get("anotacoes"),
    })

    parametros["valores"] = _limpo({
        "valor": _num(dados.get("valor")),
        "valorcondominio": _num(dados.get("valorcondominio")),
        "valoriptu": _num(dados.get("valoriptu")),
        "comissao": _num(dados.get("comissao")),
    })
    parametros["areas"] = _limpo({
        "areainterna": _num(dados.get("areainterna")),
        "areaexterna": _num(dados.get("areaexterna")),
        "arealote": _num(dados.get("arealote")),
    })
    parametros["endereco"] = _limpo({
        "rua": dados.get("rua"),
        "numero": dados.get("numero"),
        "complemento": dados.get("complemento"),
        "bloco": dados.get("bloco"),
        "bairro": dados.get("bairro"),
        "cidade": dados.get("cidade") or "Brasília",
        "estado": dados.get("estado") or "DF",
        "pontoreferencia": dados.get("pontoreferencia"),
    })
    carac_int = _limpo({
        "numeroquartos": _int(dados.get("numeroquartos")),
        "numerosalas": _int(dados.get("numerosalas")),
        "numerobanhos": _int(dados.get("numerobanhos")),
        "numerosuites": _int(dados.get("numerosuites")),
        "numerovarandas": _int(dados.get("numerovarandas")),
        "mobiliado": _bool(dados.get("mobiliado")) or None,
    })
    if carac_int:
        parametros["caracteristicasinterna"] = carac_int
    carac_ext = _limpo({
        "numerovagas": _int(dados.get("numerovagas")),
        "tipovagas": dados.get("tipovagas"),
    })
    if carac_ext:
        parametros["caracteristicasexterna"] = carac_ext

    # Proprietário (Imoview exige nome/cpf/telefone/percentual quando enviado).
    prop = _limpo({
        "nome": dados.get("prop_nome"),
        "cpfoucnpj": dados.get("prop_cpf"),
        "telefone": dados.get("prop_telefone"),
        "email": dados.get("prop_email"),
        "percentual": _num(dados.get("prop_percentual")) or (100 if dados.get("prop_nome") else None),
    })
    if prop.get("nome"):
        parametros["proprietarios"] = [prop]

    return parametros


def lancar_imovel(
    dados: Dict[str, Any],
    fotos: Optional[List[Any]] = None,
    criar_trello: bool = True,
) -> Dict[str, Any]:
    """Inclui no Imoview e cria o cartão no Trello. Retorna código + status do Trello."""
    parametros = montar_parametros_imoview(dados)
    resultado_imoview = imoview_service.incluir_imovel(parametros, fotos=fotos)
    codigo = resultado_imoview.get("codigo")

    # Classifica e persiste o foco em imovel_legado (é o que a classificação de foco lê;
    # sem isso o imóvel entra como 'NÃO LOCALIZADO'). Não-fatal.
    foco = _persistir_foco(dados, codigo)

    # Grava na planilha de estoque (não derruba o lançamento se falhar — imóvel já entrou).
    sheet: Dict[str, Any] = {"ok": False}
    try:
        sheet = _gravar_estoque_sheet(dados, codigo, foco_label=_foco_label(foco))
    except Exception as e:
        sheet = {"ok": False, "error": str(e)}

    trello: Dict[str, Any] = {"ok": False}
    if criar_trello:
        try:
            card = trello_service.criar_cartao(
                endereco=dados.get("rua") or dados.get("endereco") or "Novo imóvel",
                codigo=codigo,
                matricula=dados.get("matricula"),
                iptu=dados.get("inscricao_iptu") or dados.get("valoriptu"),
                corretor=dados.get("corretor_nome"),
                assistente=dados.get("assistente_nome"),
                cessao_direitos=_bool(dados.get("cessao_direitos")),
            )
            trello = {"ok": True, **card}
        except Exception as e:  # Trello não deve derrubar o lançamento (imóvel já entrou)
            trello = {"ok": False, "error": str(e)}

    return {
        "ok": True,
        "codigo": codigo,
        "mensagem": resultado_imoview.get("mensagem"),
        "foco": {"classificacao": _foco_label(foco), **foco},
        "sheet": sheet,
        "trello": trello,
    }
