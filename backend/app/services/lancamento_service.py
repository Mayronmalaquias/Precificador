"""Lançamento de imóvel pelos assistentes (uma vez só): Imoview + Trello.

Recebe os campos do formulário (subconjunto da planilha antiga + obrigatórios do
Imoview), monta o JSON `parametros` do Imoview, inclui o imóvel e, com o código
retornado, cria o cartão no Trello. Substitui o lançamento duplo (planilha→Trello +
Imoview manual).
"""
from __future__ import annotations

import json as _json
import os
from datetime import date
from typing import Any, Dict, List, Optional

from app.services import imoview_service, trello_service

# Planilha "Estoque - Geral" (aba onde o lançamento grava). ID configurável via env.
SHEET_ESTOQUE_ID = os.getenv("GSHEET_ESTOQUE_ID", "1869RJIoK064xnXjMHDXP0tNan5bkbJPZa-_jVfwY1cY")
SHEET_ESTOQUE_ABA = os.getenv("GSHEET_ESTOQUE_ABA", "Planilha - Geral")
# Aba de-para "nome do corretor" <-> "código Imoview" (mesma planilha).
SHEET_CORRETORES_ABA = os.getenv("GSHEET_CORRETORES_ABA", "Corretores")

# Código 0/1/vazio é placeholder de "sem Imoview ainda" no legado — não é de-para válido.
CODIGOS_PLACEHOLDER = {"", "0", "1"}


def codigo_imoview(v: Any) -> str:
    """Normaliza o código do Imoview: 112, '112', '112.0' -> '112'."""
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else str(v).strip()
    except (TypeError, ValueError):
        return str(v or "").strip()


def carregar_corretores_estoque() -> Dict[str, str]:
    """Lê a aba "Corretores" da planilha de estoque -> {codigo_imoview: nome_na_planilha}.

    A planilha é a fonte do NOME que vai pra coluna Corretor do estoque: `usuarios.nome`
    pode estar escrito diferente (acento, espaço duplo) e furar PROCV/validação da aba.
    """
    from app.services.google_service import get_services

    sheets, _, _ = get_services()
    valores = sheets.values().get(
        spreadsheetId=SHEET_ESTOQUE_ID,
        range=f"'{SHEET_CORRETORES_ABA}'!A:B",
    ).execute().get("values", [])

    mapa: Dict[str, str] = {}
    for linha in valores[1:]:  # pula o cabeçalho
        nome = str(linha[0] if len(linha) > 0 else "").strip()
        codigo = codigo_imoview(linha[1] if len(linha) > 1 else "")
        if nome and codigo not in CODIGOS_PLACEHOLDER:
            mapa.setdefault(codigo, nome)  # código repetido: vale o primeiro
    return mapa


def _nome_corretor_planilha(cod_usuario: Any) -> str:
    """Nome do corretor como está na aba "Corretores". "" se o código não estiver lá.

    Falha de leitura não pode derrubar o lançamento — cai no nome do banco.
    """
    codigo = codigo_imoview(cod_usuario)
    if codigo in CODIGOS_PLACEHOLDER:
        return ""
    try:
        return carregar_corretores_estoque().get(codigo, "")
    except Exception:
        return ""


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
        return {"ok": True, "foco_pp": foco_pp, "foco_ac": foco_ac, "bairro_id": bairro_id}
    except Exception as e:
        session.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def _usuario_por_imoview(session, cod_usuario: Any) -> Optional[Any]:
    """Usuário dono do código Imoview. É como o lançamento descobre o `id_usuarios`
    (C61xxx) do captador — o formulário só conhece o código do CRM."""
    from app.models.usuarios import Usuarios

    codigo = codigo_imoview(cod_usuario)
    if codigo in CODIGOS_PLACEHOLDER:
        return None
    return session.query(Usuarios).filter(Usuarios.id_imoview == codigo).first()


def _persistir_captacao(dados: Dict[str, Any], codigo: Any, foco: Dict[str, Any]) -> Dict[str, Any]:
    """Grava a captação em `fato_captacao` — é a fonte do ranking de captação.

    Captadores vão por `id_usuarios` (resolvidos pelo código Imoview do formulário), não
    por nome: o ranking deixa de depender do de-para nome→cadastro. `captador2` é o
    segundo corretor, que conta como captação cheia igual ao primeiro.

    **Upsert por `codigo_imovel`**: relançar o mesmo imóvel (ou um import repetido da
    planilha) atualiza a linha em vez de duplicar a captação no ranking.
    """
    from datetime import date as _date

    from app.database import SessionLocal
    from app.models.fato_bases import FatoCaptacao

    session = SessionLocal()
    try:
        principal = _usuario_por_imoview(session, dados.get("codigousuario"))
        segundo = _usuario_por_imoview(session, dados.get("codigousuario2"))

        captador1 = getattr(principal, "id_usuarios", None)
        captador2 = getattr(segundo, "id_usuarios", None)
        if captador2 and captador2 == captador1:
            captador2 = None  # mesmo corretor nos dois campos não vira 2 captações

        if not captador1:
            return {"ok": False, "error": "Corretor sem id_usuarios p/ o código Imoview informado."}

        cod = str(codigo or "").strip()
        if not cod:
            return {"ok": False, "error": "Imóvel sem código — captação não gravada."}

        registro = session.query(FatoCaptacao).filter(
            FatoCaptacao.codigo_imovel == cod
        ).first()
        criou = registro is None
        if criou:
            registro = FatoCaptacao(codigo_imovel=cod)
            session.add(registro)

        registro.captador1 = captador1
        registro.captador2 = captador2
        registro.id_gerente = getattr(principal, "team", None)
        registro.data_entrada = _date.today()
        registro.bairro_id = foco.get("bairro_id")
        registro.bairro_nome = dados.get("bairro") or None
        registro.tipo_id = str(dados.get("codigotipo") or "") or None
        registro.tipo_nome = dados.get("tipo_nome") or None
        registro.valor = _num(dados.get("valor"))
        registro.comissao_pct = _num(dados.get("comissao"))
        registro.foco_pp = bool(foco.get("foco_pp"))
        registro.foco_ac = bool(foco.get("foco_ac"))
        registro.finalidade = dados.get("finalidade_nome") or None
        registro.origem = "lancamento"
        registro.criado_por = dados.get("assistente_id") or dados.get("assistente_nome") or None

        session.commit()
        return {
            "ok": True,
            "criou": criou,
            "captador1": captador1,
            "captador2": captador2,
        }
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

    # Nome do corretor: manda o da aba "Corretores" (casado pelo código Imoview), não o do
    # banco — é o que a planilha usa nas fórmulas. Sem match, cai no do banco.
    nome_planilha = _nome_corretor_planilha(dados.get("codigousuario"))
    corretor = nome_planilha or dados.get("corretor_nome") or ""

    # 32 colunas, na ordem da aba "Planilha - Geral".
    linha = [
        corretor,                                     # 0  Corretor
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
    return {
        "ok": True,
        "corretor": corretor,
        # False = código não está na aba "Corretores"; gravou com o nome do banco.
        "corretor_na_planilha": bool(nome_planilha),
    }


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


def _proprietarios(dados: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Lista de proprietários p/ o Imoview.

    O form manda `proprietarios` como JSON (o POST é multipart, então array não passa
    solto). Confirmado no imóvel de teste 12377: o Imoview grava **todos** os itens da
    lista, não só o primeiro. Aceita também o formato antigo de campos `prop_*` soltos.
    """
    bruto = dados.get("proprietarios")
    lista: List[Any] = []
    if bruto:
        if isinstance(bruto, str):
            try:
                lista = _json.loads(bruto)
            except ValueError:
                lista = []
        elif isinstance(bruto, (list, tuple)):
            lista = list(bruto)

    if not lista:  # compat: um proprietário em campos soltos
        lista = [{
            "nome": dados.get("prop_nome"),
            "cpfoucnpj": dados.get("prop_cpf"),
            "telefone": dados.get("prop_telefone"),
            "email": dados.get("prop_email"),
            "percentual": dados.get("prop_percentual"),
        }]

    saida = []
    for item in lista:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("nome") or "").strip()
        if not nome:
            continue
        # Imoview exige percentual quando o proprietário é enviado.
        percentual = _num(item.get("percentual"))
        saida.append(_limpo({
            "nome": nome,
            "cpfoucnpj": item.get("cpfoucnpj") or item.get("cpf"),
            "telefone": item.get("telefone"),
            "email": item.get("email"),
            "percentual": percentual if percentual is not None else 100,
        }))
    return saida


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
        # Vai na RAIZ, não dentro de `endereco` — confirmado no imóvel de teste 12377
        # (mandamos valor diferente nos dois lugares; o da raiz foi o que gravou).
        "edificio": dados.get("edificio"),
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

    # Proprietários (Imoview exige nome/cpf/telefone/percentual em cada um).
    proprietarios = _proprietarios(dados)
    if proprietarios:
        parametros["proprietarios"] = proprietarios

    # `captadores` NÃO é enviado: o Imoview ignorou na escrita (teste 12377 gravou 1 só
    # captador, o do `codigousuario`). O 2º corretor fica em `fato_captacao`, que é o que
    # alimenta o ranking de captação — ver `_persistir_captacao`.

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

    # Registra a captação (fonte do ranking de captação). Não-fatal: o imóvel já entrou
    # no CRM, e um erro aqui não pode desfazer isso — aparece no retorno p/ correção.
    captacao: Dict[str, Any] = {"ok": False}
    try:
        captacao = _persistir_captacao(dados, codigo, foco)
    except Exception as e:
        captacao = {"ok": False, "error": str(e)}

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
        "captacao": captacao,
        "sheet": sheet,
        "trello": trello,
    }
