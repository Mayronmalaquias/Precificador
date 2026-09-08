"""Completa `fato_captacao` + `imoveis_legado` (Dim_Imovel) com o que foi cadastrado
DIRETO no Imoview, sem passar pelo Lancar Imovel.

Por que existe
--------------
O fluxo oficial (`lancamento_service`) cria o imovel no Imoview, abre o cartao no Trello
e, no mesmo passo, grava a captacao em `fato_captacao` e a dimensao em `imoveis_legado`.
Quem cadastra o imovel direto no CRM pula esses dois writes: o imovel existe no Imoview,
entra no catalogo local pelo `sync_areas_imoview`, mas **nao tem captacao registrada** —
some do ranking de captacao e da Visao do Diretor.

Este script varre a API do Imoview, acha o codigo que nao tem linha em `fato_captacao`
e monta a captacao com o que o proprio CRM registra: captadores (com o codigo do
usuario), data de cadastro, bairro, tipo, valor, comissao e destinacao.

O que ele NAO faz
-----------------
Nao toca em codigo que ja tem linha em `fato_captacao`, mesmo com captador diferente —
mesma regra do `completar_fato_estoque.py`. Decidir qual fonte vence quando planilha e
API discordam do captador continua sendo decisao de negocio nao tomada (ver 1.10 §9).

Em `imoveis_legado` o padrao e **preencher so o que esta vazio**. A linha que ja existe
veio do import da planilha e pode ter foco classificado a mao no lancamento; sobrescrever
mudaria a classificacao historica do ranking. Use `--sobrescrever-dim` para forcar.

Decisoes que valem registrar
----------------------------
- **Captador pelo codigo, nao pelo nome.** `captadores[].codigo` e o codigo do usuario no
  Imoview, casado direto com `usuarios.id_imoview`. O casamento por nome
  (`ranking_service._resolver_captador`) fica so como plano B — e a fonte dos bugs de
  espaco duplo e prefixo descritos em 1.10 §8.
- **`data_entrada` = `datahoracadastro` do CRM**, nao hoje. Diferente do
  `completar_fato_estoque`, aqui a data e o fato: captacao lancada em julho tem que
  contar em julho no ranking.
- **Padrao `--finalidade venda`.** Locacao e outra operacao e ja esta fora do estoque,
  das saidas e das captacoes na Visao do Diretor (2.14). Mas o ranking de captacao NAO
  filtra finalidade: inserir aluguel aqui infla o ranking dos corretores. Use
  `--finalidade todas` so com essa decisao tomada.
- **Foco pela regra** (`foco_origem='regra'`): nao ha escolha manual para imovel que
  nunca passou pelo formulario.

Uso (cwd = backend/)
--------------------
    python completar_fato_captacao.py                          # simula, nao grava
    python completar_fato_captacao.py --desde 2026-08-01
    python completar_fato_captacao.py --codigos 12470,12471
    python completar_fato_captacao.py --finalidade todas
    python completar_fato_captacao.py --gravar
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import date, datetime

sys.path.insert(0, ".")

from app.database import SessionLocal                              # noqa: E402
from app.models.fato_bases import FatoCaptacao                     # noqa: E402
from app.models.legado_diversos import ImovelLegado                # noqa: E402
from app.models.usuarios import Usuarios                           # noqa: E402
from app.services import admin_bases_service as abs_               # noqa: E402
from app.services.imoview_service import IMOVIEW_BASE, _headers    # noqa: E402
from app.services.ranking_service import RankingService            # noqa: E402

import requests                                                    # noqa: E402

ENDPOINT = f"{IMOVIEW_BASE}/Imovel/RetornarImoveis"
ORIGEM = "imoview_api"
ARQUIVO_ORIGEM = "RetornarImoveis (exibircaptadores)"
POR_PAGINA = 20          # teto da API; acima disso responde 404
MAX_PAGINAS = 120        # 2.400 imoveis a partir do codigo mais alto
# Codigo cresce com o cadastro, mas a data e o criterio: so para a varredura depois de
# N paginas seguidas inteiras fora da janela, nunca na primeira que parecer velha.
PAGINAS_FOLGA = 3
PAUSA = 0.35
TENTATIVAS = 4


def _pedir(corpo: dict):
    """POST com retentativa e espera crescente.

    O Imoview responde `401 "Chave invalida!"` sob rajada e o erro mente sobre a causa —
    a mesma chave funciona no segundo seguinte. Mesmo tratamento do
    `sync_areas_imoview._pedir`.
    """
    import time

    ultimo = None
    for tentativa in range(1, TENTATIVAS + 1):
        resposta = requests.post(ENDPOINT, headers=_headers(), json=corpo, timeout=60)
        if resposta.status_code < 400:
            time.sleep(PAUSA)
            return resposta
        ultimo = resposta
        if resposta.status_code in (401, 429) or resposta.status_code >= 500:
            espera = 5 * (2 ** (tentativa - 1))
            print(f"  Imoview {resposta.status_code} na pagina {corpo.get('numeropagina')}; "
                  f"nova tentativa em {espera}s", file=sys.stderr)
            time.sleep(espera)
            continue
        break
    raise RuntimeError(
        f"Imoview HTTP {ultimo.status_code} apos {TENTATIVAS} tentativas: {ultimo.text[:200]}"
    )


def _corpo_base(pagina: int) -> dict:
    return {
        "numeropagina": pagina,
        "numeroregistros": POR_PAGINA,
        # Sem isto a API devolve so os ~740 imoveis publicados no site proprio, e o
        # cadastrado agora (ainda nao publicado) fica de fora — que e justamente o alvo.
        "naoconsiderarmeusite": True,
        "situacao": 0,                # todas: disponivel, vendido, desativado, moderacao
        "ordenacao": "codigodesc",
        # Sem a flag `captadores` volta `[]` e o imovel parece nao ter captador (1.10 §2).
        "exibircaptadores": True,
    }


# O Imoview classifica por TIPO puro ("Apartamento"); a Dim_Imovel classifica por tipo +
# quartos ("Apartamento 2 quartos"). Casar pelo nome (`abs_.map_tipo`, que e o que o
# upload de planilha faz) so resolve "Casa" — na primeira rodada 36 de 42 imoveis ficaram
# com `tipo` nulo. Este de-para fecha o buraco, e `numeroquartos` desempata o apartamento.
TIPO_IMOVIEW_PARA_LEGADO = {
    "CASA": "T5", "CASA CONDOMINIO": "T5",
    "COBERTURA": "T4",                                  # T4 = "5 quartos/Cobertura"
    "FLAT": "T6", "KITNET": "T6", "LOFT": "T6",
    "GARAGEM": "T7",
    "LOTE": "T8", "LOTE EM CONDOMINIO": "T8",
    "PREDIO": "T9",
    "SALA": "T10", "LOJA": "T10", "COMERCIAL": "T10",
    "GALPAO": "T11", "SITIO": "T11", "CHACARA": "T11", "FAZENDA": "T11",
}
# 1 quarto cai em T6 ("...Apartamento 1 quarto"); 5+ em T4.
#
# ARMADILHA: `numeroquartos` vem '0' quando o campo NAO foi preenchido no CRM, nao quando
# o imovel tem zero quartos — 15 dos 42 primeiros, incluindo um de R$ 1,9 mi na Asa Sul
# com 100 m2. Tratar 0 como "1 quarto" classificava apartamento de luxo como kitnet.
# Desconhecido fica NULL: `imoveis_legado` ja convive com 456 linhas sem tipo, e nulo
# e recuperavel — tipo errado nao aparece como erro em lugar nenhum.
APARTAMENTO_POR_QUARTOS = {1: "T6", 2: "T1", 3: "T2", 4: "T3"}


def tipo_legado(mapas: dict, item: dict):
    """Tipo do Imoview -> id da Dim_Imovel (T1..T11). None se nao souber classificar."""
    nome = abs_.to_str(item.get("tipo"))
    direto = abs_.map_tipo(mapas, nome)   # nome identico na dimensao vence
    if direto:
        return direto
    chave = abs_.norm(nome)
    if chave.startswith("APARTAMENTO"):   # cobre "Apartamento" e "Apartamento Duplex"
        quartos = int(abs_.to_float(item.get("numeroquartos")))
        if quartos <= 0:                  # nao preenchido no CRM — ver a nota acima
            return None
        return APARTAMENTO_POR_QUARTOS.get(quartos, "T4")
    return TIPO_IMOVIEW_PARA_LEGADO.get(chave)


def _data_hora(valor):
    """'04/09/2026 07:37:25' -> datetime. Formato BR, as vezes so a data."""
    texto = str(valor or "").strip()
    for formato in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def varrer_por_codigos(codigos: list[str]) -> list[dict]:
    """Busca codigos especificos.

    `codigosimoveis` e o unico nome aceito — `codigo`, `codigoimovel`, `codigos` e
    `codigointerno` sao ignorados em silencio e devolvem o catalogo inteiro como se
    tivessem filtrado (1.10 §4.1).
    """
    itens: dict[str, dict] = {}
    for inicio in range(0, len(codigos), POR_PAGINA):
        lote = codigos[inicio:inicio + POR_PAGINA]
        corpo = _corpo_base(1)
        corpo["codigosimoveis"] = ",".join(lote)
        for item in (_pedir(corpo).json() or {}).get("lista") or []:
            codigo = str(item.get("codigo") or "").strip()
            if codigo in lote:      # defesa contra o filtro ignorado
                itens[codigo] = item
    return list(itens.values())


def varrer_janela(desde: date, ate: date | None, max_paginas: int) -> list[dict]:
    """Desce o catalogo por codigo decrescente ate passar da janela de cadastro."""
    itens: list[dict] = []
    paginas_fora = 0
    for pagina in range(1, max_paginas + 1):
        lista = (_pedir(_corpo_base(pagina)).json() or {}).get("lista") or []
        if not lista:
            break

        dentro_da_pagina = 0
        for item in lista:
            cadastro = _data_hora(item.get("datahoracadastro"))
            if cadastro is None:
                continue
            if cadastro.date() < desde:
                continue
            if ate and cadastro.date() > ate:
                continue
            dentro_da_pagina += 1
            itens.append(item)

        mais_antigo = min(
            (d for d in (_data_hora(i.get("datahoracadastro")) for i in lista) if d),
            default=None,
        )
        if dentro_da_pagina == 0 and mais_antigo and mais_antigo.date() < desde:
            paginas_fora += 1
            if paginas_fora >= PAGINAS_FOLGA:
                break
        else:
            paginas_fora = 0
    else:
        print(f"AVISO: parou no teto de {max_paginas} paginas — pode haver mais imovel "
              f"na janela. Aumente com --max-paginas.", file=sys.stderr)
    return itens


def _captadores(item: dict) -> list[tuple[str, str]]:
    """Ate 3 captadores como (codigo_imoview, nome), na ordem que o CRM devolve.

    Ordem da API, nao `principal` primeiro: e a mesma escolha do `sync_areas_imoview` e
    do `completar_fato_estoque`, e o ranking conta captador1/2/3 igual. Quem e principal
    fica em `imovel_area.captador_principal`, que ja guarda essa informacao a parte.
    """
    saida = []
    for c in (item.get("captadores") or [])[:3]:
        nome = str((c or {}).get("nome") or "").strip()
        codigo = str((c or {}).get("codigo") or "").strip()
        if nome or codigo:
            saida.append((codigo, nome))
    return saida


def montar(session, item: dict, mapas: dict, por_imoview: dict, servico, indice, stats):
    """Item cru do Imoview -> dict pronto p/ FatoCaptacao (+ efeito na dim)."""
    codigo = abs_.normalize_codigo(item.get("codigo"))
    if not codigo:
        return None

    bairro_nome = abs_.to_str(item.get("bairro"))
    tipo_nome = abs_.to_str(item.get("tipo"))
    valor = abs_.to_float(item.get("valor"))
    comissao = abs_.to_float(item.get("taxacomissao"))
    finalidade = abs_.to_str(item.get("finalidade"))
    cadastro = _data_hora(item.get("datahoracadastro"))

    ids: list[str] = []
    for cod_imoview, nome in _captadores(item):
        # 1) codigo do usuario no Imoview -> id_usuarios. Chave exata, sem casamento
        #    de nome; e o que o CRM ja sabe.
        uid = por_imoview.get(cod_imoview)
        if uid:
            stats["por_codigo"] += 1
        elif nome:
            # 2) plano B: nome do catalogo -> cadastro (prefixo por tokens, ativo vence).
            uid = servico._resolver_captador(nome, indice)
            stats["por_nome" if uid and uid.upper().startswith("C61") else "nome_cru"] += 1
        if uid:
            ids.append(uid)

    if not ids:
        stats["sem_captador"] += 1

    bairro_id, _ = abs_.ensure_bairro(session, mapas, bairro_nome)
    tipo_id = tipo_legado(mapas, item)
    # Destinacao do CRM ("Residencial" / "Comercial" / "Residencial/Comercial") e mais
    # fiel que deduzir pelo tipo — e o mesmo criterio do `lancamento_service`.
    destinacao = abs_.norm(item.get("destinacao"))
    residencial = ("RESIDENCIAL" in destinacao) if destinacao else abs_.is_residencial(tipo_id)
    foco_pp, foco_ac = abs_.classificar_foco(bairro_nome, valor, comissao, residencial)

    return {
        "codigo_imovel": codigo,
        "captador1": ids[0] if len(ids) > 0 else None,
        "captador2": ids[1] if len(ids) > 1 else None,
        "captador3": ids[2] if len(ids) > 2 else None,
        "id_gerente": mapas["idcorretor_to_gerente"].get(ids[0]) if ids else None,
        "data_entrada": cadastro.date() if cadastro else date.today(),
        "bairro_id": bairro_id or None,
        "bairro_nome": bairro_nome or None,
        "tipo_id": tipo_id,
        "tipo_nome": tipo_nome or None,
        "valor": valor or None,
        "comissao_pct": comissao or None,
        "foco_pp": foco_pp,
        "foco_ac": foco_ac,
        # Sem formulario nao ha escolha manual: a regra e a unica origem, e o sugerido
        # e igual ao gravado de proposito — mantem a auditoria de 2.11 §4 coerente.
        "foco_origem": "regra",
        "foco_pp_sugerido": foco_pp,
        "foco_ac_sugerido": foco_ac,
        "finalidade": finalidade or None,
        "origem": ORIGEM,
        "arquivo_origem": ARQUIVO_ORIGEM,
        "criado_por": "backfill",
    }


def gravar_dim(session, linha: dict, sobrescrever: bool) -> str:
    """Upsert em `imoveis_legado` (Dim_Imovel). Devolve 'criou' | 'completou' | 'intacto'."""
    codigo = linha["codigo_imovel"]
    row = session.query(ImovelLegado).filter(ImovelLegado.codigo == codigo).first()
    valor_txt = str(linha["valor"]) if linha["valor"] else None

    if row is None:
        session.add(ImovelLegado(
            codigo=codigo, tipo=linha["tipo_id"], valor=valor_txt,
            bairro=linha["bairro_id"], foco_pp=linha["foco_pp"], foco_ac=linha["foco_ac"],
        ))
        return "criou"

    if sobrescrever:
        row.tipo = linha["tipo_id"] or row.tipo
        row.valor = valor_txt or row.valor
        row.bairro = linha["bairro_id"] or row.bairro
        row.foco_pp = linha["foco_pp"]
        row.foco_ac = linha["foco_ac"]
        return "completou"

    # Padrao: so preenche buraco. Linha antiga pode ter foco classificado a mao.
    mudou = False
    for campo, novo in (("tipo", linha["tipo_id"]), ("valor", valor_txt),
                        ("bairro", linha["bairro_id"]), ("foco_pp", linha["foco_pp"]),
                        ("foco_ac", linha["foco_ac"])):
        if getattr(row, campo) is None and novo is not None:
            setattr(row, campo, novo)
            mudou = True
    return "completou" if mudou else "intacto"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--desde", default="2026-01-01", help="data de cadastro minima (YYYY-MM-DD)")
    p.add_argument("--ate", default=None, help="data de cadastro maxima (YYYY-MM-DD)")
    p.add_argument("--finalidade", default="venda", choices=("venda", "aluguel", "todas"),
                   help="padrao venda; 'todas' entra no ranking de captacao junto")
    p.add_argument("--codigos", default=None,
                   help="lista de codigos separada por virgula; ignora a janela de data")
    p.add_argument("--max-paginas", type=int, default=MAX_PAGINAS)
    p.add_argument("--valor-minimo", type=float, default=0.0,
                   help="descarta imovel abaixo deste valor (teste/rascunho do CRM)")
    p.add_argument("--sobrescrever-dim", action="store_true",
                   help="reescreve tipo/valor/bairro/foco de linha ja existente em imoveis_legado")
    p.add_argument("--gravar", action="store_true", help="grava de verdade")
    args = p.parse_args()

    desde = datetime.strptime(args.desde, "%Y-%m-%d").date()
    ate = datetime.strptime(args.ate, "%Y-%m-%d").date() if args.ate else None

    if args.codigos:
        codigos = [c.strip() for c in args.codigos.split(",") if c.strip()]
        print(f"Buscando {len(codigos)} codigo(s) no Imoview...")
        catalogo = varrer_por_codigos(codigos)
    else:
        print(f"Varrendo o catalogo do Imoview (cadastro >= {desde}"
              f"{f' e <= {ate}' if ate else ''})...")
        catalogo = varrer_janela(desde, ate, args.max_paginas)
    print(f"  {len(catalogo)} imovel(is) na janela")

    if args.finalidade != "todas":
        alvo = "VENDA" if args.finalidade == "venda" else "ALUGUEL"
        antes = len(catalogo)
        catalogo = [i for i in catalogo if abs_.norm(i.get("finalidade")) == alvo]
        print(f"  {antes - len(catalogo)} fora por finalidade != {args.finalidade}")

    servico = RankingService()
    indice = servico._indice_captadores()

    session = SessionLocal()
    try:
        ja_tem = {
            str(c or "").strip()
            for (c,) in session.query(FatoCaptacao.codigo_imovel).distinct().all()
            if str(c or "").strip()
        }
        por_imoview = {
            str(u.id_imoview).strip(): u.id_usuarios
            for u in session.query(Usuarios.id_imoview, Usuarios.id_usuarios).all()
            if str(u.id_imoview or "").strip() and u.id_usuarios
        }
        mapas = abs_.carregar_mapas(session)

        stats = Counter()
        faltantes = [i for i in catalogo
                     if str(i.get("codigo") or "").strip() not in ja_tem]
        print(f"  {len(catalogo) - len(faltantes)} ja tem linha em fato_captacao (intocados)")

        linhas = []
        for item in faltantes:
            linha = montar(session, item, mapas, por_imoview, servico, indice, stats)
            if linha:
                linhas.append(linha)

        # Rascunho e teste do CRM entram como imovel de verdade: o 12377 e o imovel de
        # teste do proprio Lancar Imovel, com valor R$ 1.000. Sem um corte, ele vira
        # captacao no ranking de alguem.
        if args.valor_minimo > 0:
            antes = len(linhas)
            linhas = [l for l in linhas if (l["valor"] or 0) >= args.valor_minimo]
            print(f"  {antes - len(linhas)} descartado(s) por valor < {args.valor_minimo:,.0f}")
        suspeitos = [l for l in linhas if (l["valor"] or 0) < 50_000
                     or not (l["comissao_pct"] or 0)]

        por_mes = Counter(l["data_entrada"].strftime("%Y-%m") for l in linhas)
        por_fin = Counter(l["finalidade"] or "(sem)" for l in linhas)
        foco = sum(1 for l in linhas if l["foco_pp"] or l["foco_ac"])

        print()
        print(f"CAPTACOES A INSERIR ............ {len(linhas)}")
        print(f"  com foco (PP ou AC) .......... {foco}")
        print(f"  sem captador nenhum .......... {stats['sem_captador']}")
        sem_tipo = sum(1 for l in linhas if not l["tipo_id"])
        print(f"  sem tipo na Dim_Imovel ....... {sem_tipo}")
        print("  captador resolvido por:")
        print(f"     codigo Imoview ............ {stats['por_codigo']}")
        print(f"     nome (cadastro) ........... {stats['por_nome']}")
        print(f"     nao resolveu (nome cru) ... {stats['nome_cru']}")
        print("  por finalidade: " + ", ".join(f"{k}={v}" for k, v in por_fin.most_common()))
        print("  por mes de cadastro:")
        for mes, q in sorted(por_mes.items(), reverse=True):
            print(f"     {mes}  {q}")
        if suspeitos:
            print(f"  ATENCAO — {len(suspeitos)} com cara de teste/rascunho "
                  f"(valor < 50.000 ou comissao 0):")
            for l in suspeitos:
                print(f"     {l['codigo_imovel']:<8} {str(l['data_entrada']):<12} "
                      f"valor={(l['valor'] or 0):>12,.0f} com%={(l['comissao_pct'] or 0):>5.2f} "
                      f"{l['bairro_nome'] or '-'}")
            print("     -> conferir antes de gravar; --valor-minimo corta pelo valor.")

        if not args.gravar:
            print()
            print("SIMULACAO — nada gravado. Use --gravar para valer.")
            print(f"{'codigo':<8} {'data':<12} {'cap1':<10} {'equipe':<8} "
                  f"{'valor':>12} {'com%':>6}  foco  bairro")
            for l in linhas[:30]:
                marca = ("PP" if l["foco_pp"] else "") + ("AC" if l["foco_ac"] else "") or "--"
                print(f"{l['codigo_imovel']:<8} {str(l['data_entrada']):<12} "
                      f"{str(l['captador1'] or '-')[:10]:<10} {str(l['id_gerente'] or '-'):<8} "
                      f"{(l['valor'] or 0):>12,.0f} {(l['comissao_pct'] or 0):>6.2f}  "
                      f"{marca:<5} {l['bairro_nome'] or '-'}")
            if len(linhas) > 30:
                print(f"... e mais {len(linhas) - 30}")
            session.rollback()   # descarta bairro auto-criado pelo ensure_bairro
            return 0

        dim = Counter()
        for linha in linhas:
            dim[gravar_dim(session, linha, args.sobrescrever_dim)] += 1
        session.bulk_insert_mappings(FatoCaptacao, linhas)
        session.commit()

        print()
        print(f"GRAVADO: {len(linhas)} linhas em fato_captacao (origem='{ORIGEM}')")
        print(f"         imoveis_legado: {dim['criou']} criadas, {dim['completou']} "
              f"completadas, {dim['intacto']} intactas")
        print(f"Desfazer a fato: DELETE FROM fato_captacao "
              f"WHERE origem='{ORIGEM}' AND criado_por='backfill';")
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
