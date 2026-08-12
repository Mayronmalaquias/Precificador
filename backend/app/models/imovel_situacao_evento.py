"""Historico de mudanca de situacao do imovel no Imoview.

Existe porque `imovel_area.situacao` guarda so o estado ATUAL — e "saida de estoque" e
uma *transicao* (estava disponivel, deixou de estar), nao um estado. Sem historico nao
da p/ responder "quantos imoveis sairam em julho".

Quem alimenta: `sync_areas_imoview.py`, comparando a varredura do dia com o que estava
gravado. Uma linha por mudanca detectada.
"""
from sqlalchemy import Column, Date, DateTime, Index, Integer, String, func

from app.models.base import Base


class ImovelSituacaoEvento(Base):
    __tablename__ = "imovel_situacao_evento"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), nullable=False, index=True)
    situacao_anterior = Column(String(40), nullable=True)
    situacao_nova = Column(String(40), nullable=True)
    # Data da varredura que percebeu a mudanca — nao a data real do fato no CRM, que a
    # API nao informa. Com cron diario, o erro maximo e de 1 dia.
    detectado_em = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


Index("ix_imovel_situacao_evento_periodo", ImovelSituacaoEvento.detectado_em,
      ImovelSituacaoEvento.situacao_anterior, ImovelSituacaoEvento.situacao_nova)
