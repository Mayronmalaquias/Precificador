import re
from datetime import date, datetime

import pandas as pd

from app.database import SessionLocal
from app.extensions import cache
from app.models.dfimoveis_acesso import DfImoveisAcesso
from app.services.admin_bases_service import ler_arquivo


REQUIRED_COLUMNS = {"Endereco", "CodigoDeBusca", "Acesso", "Impressao"}
NUMERIC_COLUMNS = [
    "Acesso", "Impressao", "Emails", "Telefone", "WhatsAppEmailsGerados", "Indique",
    "IndiqueWhatsapp", "Termo", "CompartilheFacebook", "CompartilheGoogle",
    "CompartilheTwitter", "AtendimentoOnlineParaLancamento", "Visita", "Proposta",
]


def extrair_bairro(endereco):
    parts = [part.strip() for part in str(endereco or "").split("-") if part.strip()]
    if len(parts) >= 3 and parts[1].upper() == "BRASILIA":
        return parts[2].title()
    if len(parts) >= 2:
        return parts[1].title()
    return "Não identificado"


def _report_date(value, filename):
    if value:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("Data do relatório inválida") from exc
    match = re.search(r"(\d{2})_(\d{2})_(\d{4})", filename or "")
    if match:
        return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    return date.today()


def importar_relatorio(file_storage, data_relatorio=None, criado_por=None):
    filename = getattr(file_storage, "filename", "") or "relatorio-dfimoveis.xlsx"
    if not filename.lower().endswith(".xlsx"):
        raise ValueError("O relatório DFImóveis deve estar no formato XLSX")
    df = ler_arquivo(file_storage)
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing)}")
    for column in NUMERIC_COLUMNS:
        if column not in df.columns:
            df[column] = 0
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)
    report_date = _report_date(data_relatorio, filename)

    session = SessionLocal()
    try:
        # O upload da mesma data é uma atualização atômica daquele snapshot.
        removidos = session.query(DfImoveisAcesso).filter(DfImoveisAcesso.data_relatorio == report_date).delete(synchronize_session=False)
        rows = []
        for _, item in df.iterrows():
            code = str(item.get("CodigoDeBusca") or "").strip()
            if not code or code.lower() == "nan":
                continue
            rows.append(DfImoveisAcesso(
                data_relatorio=report_date, arquivo_origem=filename, criado_por=criado_por,
                endereco=str(item.get("Endereco") or "").strip(), bairro=extrair_bairro(item.get("Endereco")),
                codigo_busca=code, negocio=str(item.get("Negocio") or "").strip() or None,
                situacao_cadastro=str(item.get("SituacaoDoCadastro") or "").strip() or None,
                acesso=int(item["Acesso"]), impressao=int(item["Impressao"]), emails=int(item["Emails"]),
                telefone=int(item["Telefone"]), whatsapp_emails_gerados=int(item["WhatsAppEmailsGerados"]),
                indique=int(item["Indique"]), indique_whatsapp=int(item["IndiqueWhatsapp"]), termo=int(item["Termo"]),
                compartilhe_facebook=int(item["CompartilheFacebook"]), compartilhe_google=int(item["CompartilheGoogle"]),
                compartilhe_twitter=int(item["CompartilheTwitter"]),
                atendimento_online_lancamento=int(item["AtendimentoOnlineParaLancamento"]),
                visita=int(item["Visita"]), proposta=int(item["Proposta"]),
            ))
        session.bulk_save_objects(rows)
        session.commit()
        cache.clear()
        return {"inseridos": len(rows), "atualizados": removidos, "ignorados_duplicados": 0,
                "data_relatorio": report_date.isoformat(), "arquivo": filename, "erros": []}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
