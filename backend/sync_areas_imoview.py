"""Snapshot das areas do catalogo Imoview -> tabela `imovel_area` (rodar via cron).

Por que existe: a API do Imoview so lista imovel ATIVO. Quando o imovel vende ele
some da API, e e nesse momento que precisamos da metragem p/ o valor do m2 do
contrato. Rodando periodicamente, a area fica gravada antes da venda.

Cobre o que estiver no catalogo no momento da execucao — venda antiga cujo imovel
ja saiu do ar continua sem area (nao ha de onde tirar).

Uso (cwd = backend/):
    cd /caminho/Precificador/backend && venv/bin/python sync_areas_imoview.py
"""
import time
import sys
import unicodedata
from datetime import date, datetime, timedelta

import requests

from app.database import SessionLocal
from app.models.imovel_area import ImovelArea
from app.models.imovel_situacao_evento import ImovelSituacaoEvento
from app.services.imoview_service import IMOVIEW_BASE, _headers

ENDPOINT = f"{IMOVIEW_BASE}/Imovel/RetornarImoveis"
POR_PAGINA = 20  # teto da API: acima disso responde 404 "N de registros nao pode ser maior que 20!"
MAX_PAGINAS = 200

# Situacoes varridas. 1=Vago/Disponivel (854) e o estoque; 3=Vendido (1.175) importa
# porque some da API depois e e dele que sai a metragem do valor/m2 dos contratos;
# 4=Em reforma (4) e 5=Em moderacao (81) sao baratas e precisam ser distinguidas — sem
# elas, um imovel em moderacao pareceria "desativado" e entraria como saida de estoque,
# que e justamente o que a regra manda excluir.
SITUACOES = {1: "Vago/Disponivel", 3: "Vendido", 4: "Em reforma", 5: "Em moderacao"}

# 6=Desativado (9.326) e varrido de forma INCREMENTAL, nao inteiro.
#
# Ele ficava de fora porque baixar tudo custa ~466 paginas por dia. O efeito colateral
# era grave: o painel do diretor contava 6 saidas em agosto quando o Imoview tinha 59
# (50 desativados + 9 vendidos) — quem sai do estoque por desativacao e a maioria, e
# nunca aparecia com a data real.
#
# A saida barata: `ordenacao=dataatualizacaodesc` traz o mexido recentemente primeiro,
# entao basta descer ate passar da janela. Medido em 20/08/2026: 3 paginas cobriram o
# mes inteiro. (`datahoraultimasituacaodesc` NAO funciona — a API aceita o parametro e
# devolve fora de ordem.)
SITUACAO_DESATIVADO = 6
NOME_SITUACAO = {**SITUACOES, 6: "Desativado"}
DIAS_DESATIVADO = 45      # margem sobre o intervalo do cron; nao e o custo, e a folga
MAX_PAGINAS_DESATIVADO = 40
# Teto da varredura completa dos desativados: 9.354 / 20 por pagina = 468, com folga.
MAX_PAGINAS_TUDO = 700


def _num(valor):
    """Area do Imoview vem como texto BR ("95,00").

    Cuidado: `areaprivativa`/`areaservico` sao BOOLEANOS no mesmo payload — sem
    barrar bool, um `True` viraria "1 m2" e estragaria o valor do m2.
    """
    if isinstance(valor, bool) or valor in (None, ""):
        return None
    if isinstance(valor, (int, float)):
        numero = float(valor)
    else:
        texto = str(valor).strip().replace("R$", "").replace(" ", "")
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        try:
            numero = float(texto)
        except ValueError:
            return None
    return numero if numero > 0 else None


def _inteiro(valor):
    numero = _num(valor)
    return int(numero) if numero is not None else None


def _data_hora(valor):
    """'13/08/2026 10:32:51' -> datetime. Formato BR, as vezes so a data."""
    texto = str(valor or "").strip()
    for formato in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def coletar(desativados_completo=False):
    """Percorre o catalogo por situacao e devolve {codigo: dados de area}.

    `naoconsiderarmeusite=True` e obrigatorio: sem ele a API devolve so os 741 imoveis
    publicados no site, e o recem-lancado (que ainda nao foi publicado) fica de fora.

    Cobertura do Imoview em 27/08/2026 (`quantidade` da propria API):

        1 Vago/Disponivel      864   varrido inteiro
        3 Vendido            1.181   varrido inteiro
        4 Em reforma             4   varrido inteiro
        5 Em moderacao          84   varrido inteiro
        6 Desativado         9.354   fatia de 45 dias por padrao
        2 Alugado                0   nao existe nesta conta
        7 Em desocupacao         0   nao existe nesta conta
        ------------------------------
        0 todas             11.487

    Os desativados sao 81% do catalogo. Varre-los todo dia custa 468 paginas (~26 min) e
    nao muda quase nada — imovel desativado ha meses continua desativado. Por isso o
    padrao e a fatia recente.

    `desativados_completo=True` varre os 9.354. Serve para a carga inicial, uma vez: sem
    ela o catalogo fica com ~2.600 dos 11.487, e um imovel vendido em 2023 nunca aparece.
    """
    catalogo = {}
    for situacao in SITUACOES:
        catalogo.update(_coletar_situacao(situacao))
    if desativados_completo:
        catalogo.update(_coletar_situacao(
            SITUACAO_DESATIVADO, max_paginas=MAX_PAGINAS_TUDO))
    else:
        catalogo.update(_coletar_desativados_recentes())
    return catalogo


def _coletar_desativados_recentes():
    """Desativados mexidos nos ultimos `DIAS_DESATIVADO` dias.

    Nao varre os 9.326: desce por data de atualizacao e para quando a pagina ja e mais
    velha que o corte. O que ficou desativado ha meses nao muda mais, e ja esta gravado.
    """
    corte = datetime.now() - timedelta(days=DIAS_DESATIVADO)
    return _coletar_situacao(
        SITUACAO_DESATIVADO,
        ordenacao="dataatualizacaodesc",
        parar_antes_de=corte,
        max_paginas=MAX_PAGINAS_DESATIVADO,
    )


# Pausa entre paginas. O Imoview nao publica limite, mas devolve 401 "Chave invalida!"
# depois de uma rajada — aconteceu na pagina ~180 de uma varredura completa, e o erro
# mente sobre a causa: a chave continua valida logo em seguida.
PAUSA_ENTRE_PAGINAS = 0.35
TENTATIVAS = 4


def _pedir(corpo):
    """POST na API com retentativa e espera crescente.

    O 401 do Imoview e transitorio e nao distingue chave errada de excesso de chamadas.
    Tratar como fatal fazia 10 minutos de varredura irem embora — `coletar()` so grava no
    fim, entao uma falha na pagina 180 perde as 179 anteriores.

    Chave realmente invalida falha nas quatro tentativas e ai sim estoura.
    """
    ultimo = None
    for tentativa in range(1, TENTATIVAS + 1):
        resposta = requests.post(ENDPOINT, headers=_headers(), json=corpo, timeout=60)
        if resposta.status_code < 400:
            time.sleep(PAUSA_ENTRE_PAGINAS)
            return resposta
        ultimo = resposta
        if resposta.status_code in (401, 429) or resposta.status_code >= 500:
            espera = 5 * (2 ** (tentativa - 1))  # 5s, 10s, 20s
            print(f"  Imoview {resposta.status_code} na pagina "
                  f"{corpo.get('numeropagina')}; nova tentativa em {espera}s",
                  file=sys.stderr)
            time.sleep(espera)
            continue
        break
    raise RuntimeError(
        f"Imoview HTTP {ultimo.status_code} apos {TENTATIVAS} tentativas: "
        f"{ultimo.text[:200]}"
    )


def _captadores(item):
    """Ate 3 captadores do imovel, com o percentual de cada um.

    O `percentual` e o rateio OFICIAL do CRM entre co-captadores, e nao e sempre meio a
    meio: ha imovel com o captador marcado como principal em 0% e o outro em 100%.
    Guardar o numero evita supor `1/n`, que erraria justamente nesses casos.

    `principal` tambem e guardado a parte porque nao coincide com quem tem o maior
    percentual — sao duas informacoes diferentes do CRM.
    """
    lista = item.get("captadores") or []
    dados = {
        "captador1": None, "captador2": None, "captador3": None,
        "percentual1": None, "percentual2": None, "percentual3": None,
        "captador_principal": None,
    }
    for i, c in enumerate(lista[:3], start=1):
        nome = str((c or {}).get("nome") or "").strip()
        if not nome:
            continue
        dados[f"captador{i}"] = nome
        try:
            dados[f"percentual{i}"] = float((c or {}).get("percentual") or 0)
        except (TypeError, ValueError):
            dados[f"percentual{i}"] = None
        if (c or {}).get("principal"):
            dados["captador_principal"] = nome
    return dados


def _coletar_situacao(situacao, ordenacao=None, parar_antes_de=None, max_paginas=None):
    catalogo = {}
    pagina = 1
    teto = max_paginas or MAX_PAGINAS
    while pagina <= teto:
        corpo = {
            "numeropagina": pagina, "numeroregistros": POR_PAGINA,
            "naoconsiderarmeusite": True, "situacao": situacao,
            # Sem esta flag o campo `captadores` volta `[]` — e era por isso que se
            # acreditava que a API nao informava o captador. Com ela, a cobertura medida
            # em 27/08/2026 foi de 100% (160 de 160 na amostra).
            "exibircaptadores": True,
        }
        if ordenacao:
            corpo["ordenacao"] = ordenacao
        resposta = _pedir(corpo)
        lista = (resposta.json() or {}).get("lista") or []
        if not lista:
            break
        for item in lista:
            codigo = str(item.get("codigo") or "").strip()
            if not codigo:
                continue
            principal = _num(item.get("areaprincipal"))
            interna = _num(item.get("areainterna"))
            # `areaprivativa` costuma vir como flag; só entra se for número de verdade.
            privativa = _num(item.get("areaprivativa"))
            catalogo[codigo] = {
                "area": principal or interna or privativa,
                "area_principal": principal,
                "area_interna": interna,
                "area_privativa": privativa,
                "area_lote": _num(item.get("arealote")),
                "quartos": _inteiro(item.get("numeroquartos")),
                "vagas": _inteiro(item.get("numerovagas")),
                "valor": _num(item.get("valor")),
                "endereco": item.get("endereco"),
                "bairro": item.get("bairro"),
                "tipo": item.get("tipo") or item.get("descricaotipo"),
                # `SITUACOES` nao tem a 6 (ela e varrida a parte); o fallback cobre.
                "situacao": item.get("situacao") or NOME_SITUACAO.get(situacao, ""),
                "cadastrado_em": _data_hora(item.get("datahoracadastro")),
                "finalidade": (item.get("finalidade") or "").strip() or None,
                "situacao_em": _data_hora(item.get("datahoraultimasituacao")),
                **_captadores(item),
            }
            # Matricula quase nunca vem preenchida do CRM (2 em 60 na amostra), mas
            # quando vem serve de ponto de partida. Fica fora do dict acima de proposito:
            # o upsert sobrescreve tudo que esta la, e matricula digitada por nos nao
            # pode ser apagada por um campo vazio do Imoview.
            matricula_crm = str(item.get("matriculacartorio") or "").strip()
            if matricula_crm:
                catalogo[codigo]["_matricula_crm"] = matricula_crm
        if len(lista) < POR_PAGINA:
            break
        # Varredura incremental: a lista vem da mais recente para a mais antiga, entao
        # quando a ULTIMA da pagina ja e anterior ao corte, o resto so tem coisa velha.
        if parar_antes_de:
            ultima = _data_hora(
                lista[-1].get("dataatualizacao") or lista[-1].get("datahoraultimasituacao")
            )
            if ultima and ultima < parar_antes_de:
                break
        pagina += 1
    return catalogo


DESATIVADO = "Desativado"


def _sem_acento(texto):
    """A API manda 'Vago/Disponivel' com acento; o fallback local, sem. Compara igual."""
    return unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower().strip()


def _e_disponivel(situacao):
    return _sem_acento(situacao).startswith("vago")


def gravar(catalogo):
    """Upsert por codigo — nunca apaga: imovel que saiu do catalogo tem que ficar.

    Alem do upsert, registra em `imovel_situacao_evento` toda TRANSICAO de situacao. E
    dai que sai a "saida de estoque" do painel do diretor: a API nao tem endpoint de
    movimentacao, entao a mudanca so existe se a gente comparar duas varreduras.

    Dois tipos de mudanca:
      1. o imovel aparece na varredura com situacao diferente da gravada;
      2. o imovel estava disponivel e SUMIU da varredura -> virou `Desativado` (situacao
         6, 9.312 imoveis: caro demais p/ baixar todo dia so p/ confirmar o obvio).

    Primeira execucao e BASELINE: a tabela de eventos vazia significa que as diferencas
    acumuladas nao sao do dia (imovel marcado disponivel que ja saiu ha meses). Reconcilia
    calado e grava uma linha-marco (`codigo='__baseline__'`) datada de AMANHA.

    A marca e necessaria: sem ela, "tabela vazia" continuaria verdadeiro apos o baseline
    (que nao escreve nada) e TODA execucao seria baseline — nenhum evento sairia nunca.
    Datada de amanha porque as transicoes de hoje nao foram capturadas; o painel usa
    `min(detectado_em)` como inicio da cobertura do log e cai na planilha antes disso.
    """
    session = SessionLocal()
    hoje = date.today()
    try:
        baseline = session.query(ImovelSituacaoEvento.id).first() is None
        existentes = {row.codigo: row for row in session.query(ImovelArea).all()}
        novos = atualizados = 0
        eventos = []

        def _anotar(codigo, antes, depois):
            if _sem_acento(antes) == _sem_acento(depois):
                return
            eventos.append({"codigo": codigo, "antes": antes, "depois": depois})
            if not baseline:
                session.add(ImovelSituacaoEvento(
                    codigo=codigo, situacao_anterior=antes, situacao_nova=depois, detectado_em=hoje,
                ))

        for codigo, dados in catalogo.items():
            matricula_crm = dados.pop("_matricula_crm", None)
            registro = existentes.get(codigo)
            if registro is None:
                session.add(ImovelArea(
                    codigo=codigo, origem="imoview", matricula=matricula_crm, **dados
                ))
                novos += 1
                continue
            anterior = registro.situacao
            for campo, valor in dados.items():
                setattr(registro, campo, valor)
            # So preenche buraco: matricula digitada na Consulta manda no dado do CRM.
            if matricula_crm and not (registro.matricula or "").strip():
                registro.matricula = matricula_crm
            atualizados += 1
            _anotar(codigo, anterior, dados.get("situacao"))

        # Sumiu da varredura estando disponivel = saiu do ar (desativado).
        for codigo, registro in existentes.items():
            if codigo in catalogo or not _e_disponivel(registro.situacao):
                continue
            _anotar(codigo, registro.situacao, DESATIVADO)
            registro.situacao = DESATIVADO
            # Desativado e deduzido por AUSENCIA (situacao 6 nao e varrida), entao nao ha
            # `datahoraultimasituacao` p/ copiar — a data da deteccao e o melhor que existe.
            registro.situacao_em = datetime.now()

        if baseline:
            session.add(ImovelSituacaoEvento(
                codigo="__baseline__", situacao_anterior="baseline", situacao_nova="baseline",
                detectado_em=hoje + timedelta(days=1),
            ))

        session.commit()
        return novos, atualizados, eventos, baseline
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    agora = datetime.now().isoformat(timespec="seconds")
    # `--tudo` varre TODOS os desativados. E carga inicial, nao rotina: ~26 min contra
    # ~1 min do incremental. O cron continua sem a flag.
    completo = "--tudo" in sys.argv
    try:
        catalogo = coletar(desativados_completo=completo)
        novos, atualizados, eventos, baseline = gravar(catalogo)
        saidas = [e for e in eventos if _e_disponivel(e["antes"]) and not _e_disponivel(e["depois"])]
        print(f"[{agora}] areas imoview: catalogo={len(catalogo)} novos={novos} "
              f"atualizados={atualizados} mudancas={len(eventos)} saidas={len(saidas)}"
              + (" [BASELINE: eventos NAO gravados]" if baseline else ""))
    except Exception as e:
        print(f"[{agora}] sync de areas FALHOU: {e}", file=sys.stderr)
        sys.exit(1)
