"""Importa o histórico da planilha de estoque para `fato_captacao`.

Contexto: o ranking de captação passou a ler `fato_captacao` em vez da planilha
("Planilha - Geral"). Sem este import, tudo que só existe na planilha some do ranking.

Regras:
- **Só insere código que ainda não está na tabela.** Linhas de `origem='upload'` ou
  `'lancamento'` são mais confiáveis (já têm id_usuarios) e nunca são sobrescritas.
- **Captador** é resolvido em cascata: nome exato no cadastro → aba "Corretores"
  (nome → código Imoview → usuarios) → prefixo único. Não resolveu, grava o NOME cru:
  o ranking sabe exibir linha por nome, e perder a captação seria pior.
- **foco_pp/foco_ac ficam NULL de propósito.** A coluna "Foco" da planilha é outra
  taxonomia ('FOCO - 61' / 'FOCO - Corretor'), não a classificação PP/AC do
  `imoveis_legado`. O ranking pega o foco pelo código na Dim_Imovel.
- `origem='planilha'` marca o lote — dá pra desfazer com um DELETE por esse valor.

Rodar (raiz do backend):
    PYTHONPATH=. python importar_captacoes_planilha.py            # dry-run (padrão)
    PYTHONPATH=. python importar_captacoes_planilha.py --commit   # grava
"""
import sys
import unicodedata
from datetime import datetime

from app.database import SessionLocal
from app.models.fato_bases import FatoCaptacao
from app.models.usuarios import Usuarios
from app.services.lancamento_service import (
    SHEET_ESTOQUE_ABA,
    SHEET_ESTOQUE_ID,
    carregar_corretores_estoque,
)

ORIGEM = "planilha"


def _norm(s) -> str:
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()


def _data(valor):
    """'07/11/24' e '07/11/2024' -> date. None se não der."""
    txt = str(valor or "").strip()
    if not txt:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            pass
    return None


def _numero(valor):
    """'R$ 880.000,00' / '880000' / '5,5' -> float. None se não der."""
    txt = str(valor or "").strip()
    if not txt:
        return None
    txt = txt.replace("R$", "").replace("%", "").replace(" ", "").replace("\xa0", "")
    if "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return None


def _ler_planilha():
    from app.services.google_service import get_services

    sheets, _, _ = get_services()
    vals = sheets.values().get(
        spreadsheetId=SHEET_ESTOQUE_ID,
        range=f"'{SHEET_ESTOQUE_ABA}'!A:AF",
    ).execute().get("values", [])
    if len(vals) < 2:
        return [], {}

    header = [str(h).strip() for h in vals[0]]
    idx = {h: i for i, h in enumerate(header)}
    return vals[1:], idx


def _resolvedor(session):
    """Devolve fn(nome) -> (captador, como_resolveu)."""
    usuarios = session.query(Usuarios).filter(Usuarios.id_usuarios.isnot(None)).all()
    por_nome = {_norm(u.nome): u.id_usuarios for u in usuarios if u.nome}
    por_imoview = {str(u.id_imoview): u.id_usuarios for u in usuarios if u.id_imoview}
    nome_para_codigo = {_norm(nome): cod for cod, nome in carregar_corretores_estoque().items()}

    def resolver(nome):
        chave = _norm(nome)
        if not chave:
            return None, "sem_nome"
        if chave in por_nome:
            return por_nome[chave], "nome"
        codigo = nome_para_codigo.get(chave)
        if codigo and codigo in por_imoview:
            return por_imoview[codigo], "aba_corretores"
        candidatos = [n for n in por_nome if n.startswith(chave + " ")]
        if len(candidatos) == 1:
            return por_nome[candidatos[0]], "prefixo"
        # Sem match: preserva o nome cru (o ranking exibe por nome).
        return str(nome).strip(), "nome_cru"

    return resolver


def main() -> None:
    commit = "--commit" in sys.argv
    linhas, idx = _ler_planilha()
    if not linhas:
        print("Planilha vazia ou inacessível.")
        return

    def campo(linha, nome):
        i = idx.get(nome)
        if i is None or i >= len(linha):
            return ""
        return str(linha[i]).strip()

    col_foco = "Foco " if "Foco " in idx else "Foco"

    session = SessionLocal()
    try:
        resolver = _resolvedor(session)
        ja_existem = {
            str(c or "").strip()
            for (c,) in session.query(FatoCaptacao.codigo_imovel).all()
        }

        novos, pulados_existentes, sem_codigo, sem_data = [], 0, 0, 0
        como = {"nome": 0, "aba_corretores": 0, "prefixo": 0, "nome_cru": 0, "sem_nome": 0}
        vistos = set()

        for linha in linhas:
            codigo = campo(linha, "Código")
            if not codigo:
                sem_codigo += 1
                continue
            if codigo in ja_existem or codigo in vistos:
                pulados_existentes += 1
                continue

            captador, via = resolver(campo(linha, "Corretor"))
            como[via] = como.get(via, 0) + 1
            if not captador:
                continue

            data = _data(campo(linha, "Data da Captação"))
            if data is None:
                sem_data += 1

            vistos.add(codigo)
            novos.append(FatoCaptacao(
                codigo_imovel=codigo,
                captador1=captador,
                data_entrada=data,
                bairro_nome=campo(linha, "Região") or None,
                valor=_numero(campo(linha, "Valor ") or campo(linha, "Valor")),
                comissao_pct=_numero(campo(linha, "Comissão")),
                # foco_pp/foco_ac NULL: a coluna Foco da planilha e outra taxonomia.
                foco_pp=None,
                foco_ac=None,
                origem=ORIGEM,
                arquivo_origem=f"{SHEET_ESTOQUE_ABA} ({SHEET_ESTOQUE_ID[:12]}…)",
                criado_por="import",
            ))

        print(f"Linhas na planilha .............. {len(linhas)}")
        print(f"Sem código (ignoradas) .......... {sem_codigo}")
        print(f"Código já em fato_captacao ...... {pulados_existentes}")
        print(f"A INSERIR ....................... {len(novos)}")
        print(f"  sem data de captação .......... {sem_data}")
        print("Resolução do captador:")
        for k in ("nome", "aba_corretores", "prefixo", "nome_cru", "sem_nome"):
            print(f"  {k:16} {como.get(k, 0)}")

        if not commit:
            print("\nDRY-RUN — nada gravado. Rode com --commit para inserir.")
            return

        session.bulk_save_objects(novos)
        session.commit()
        print(f"\nOK: {len(novos)} captações inseridas (origem='{ORIGEM}').")
        print(f"Desfazer: DELETE FROM fato_captacao WHERE origem = '{ORIGEM}';")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
