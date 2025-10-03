from app.models.base import Base
from sqlalchemy import Column, Integer, String, Float

class PerformeImoveis(Base):
    __tablename__ = "performe_imoveis"

    id = Column(Integer, primary_key=True)
    codigo_imovel = Column(String(64), unique=False, index=True, nullable=False)

    # Métricas usadas nos gráficos:
    views_df = Column(Float)
    views_olx_zap = Column(Float)
    leads_df = Column(Float)
    leads_olx_zap = Column(Float)
    leads_c2s = Column(Float)
    leads_c2s_imoview = Column(Float)

    def to_rowdict(self):
        """Dicionário compatível com o gerador de PDF."""
        return {
            "Código do Imóvel": self.codigo_imovel,
            "Views DF": self.views_df or 0,
            "Views OLX/ZAP": self.views_olx_zap or 0,
            "Leads DF": self.leads_df or 0,
            "Leads OLX/ZAP": self.leads_olx_zap or 0,
            "Leads C2S": self.leads_c2s or 0,
            "Leads C2S - Imoview": self.leads_c2s_imoview or 0,
        }
