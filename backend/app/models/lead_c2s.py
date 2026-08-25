from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String, Text, Index
from sqlalchemy.sql import func

from app.models.base import Base


class LeadC2S(Base):
    """Espelho local dos leads do Contact2Sale.

    Existe separado de `leads_legado` de propósito. `leads_legado` é a base do relatório
    histórico e passa por um **filtro de negócio** na importação (só entra lead criado
    pela recepção, ou de fonte Faixa/Indicação; equipe LOCAÇÃO e LIXEIRA saem). Esta
    tabela é cópia crua: todo lead do C2S, sem regra nenhuma.

    Misturar as duas quebraria uma das pontas — ou o relatório passaria a contar leads
    que a regra sempre excluiu, ou a tela de leads deixaria de mostrar o que o C2S mostra.

    A chave é `id_c2s`, o hash que a API usa. É o que permite **atualizar** um lead já
    importado: situação, etapa do funil e motivo de arquivamento mudam depois que o lead
    entrou, e a base tem que acompanhar. A ligação com `leads_legado` (`id_legado`) é por
    cliente + telefone, a mesma chave da importação — é frágil, mas é o único elo que
    existe, e serve só para achar o acompanhamento, que continua morando lá.
    """

    __tablename__ = "leads_c2s"

    id_c2s = Column(String(64), primary_key=True)

    # `data` é `criado_em` truncado. Redundante de propósito: quase todo filtro da tela é
    # por dia, e comparar Date indexado é muito mais barato que truncar DateTime em cada
    # linha da varredura.
    data = Column(Date, nullable=True, index=True)

    cliente = Column(Text, nullable=True)
    telefone = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    fonte = Column(Text, nullable=True)
    canal = Column(Text, nullable=True)
    equipe = Column(Text, nullable=True)
    corretor = Column(Text, nullable=True)
    codigo_imovel = Column(Text, nullable=True)
    imovel = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    observacao = Column(Text, nullable=True)

    # ── campos que mudam depois da entrada do lead ────────────────────────────
    situacao = Column(Text, nullable=True)
    situacao_alias = Column(String(40), nullable=True, index=True)
    funil = Column(Text, nullable=True)
    arquivado = Column(Boolean, nullable=True, index=True)
    motivo_arquivamento = Column(Text, nullable=True)
    negocio_fechado = Column(Boolean, nullable=True)
    valor_fechado = Column(Numeric(14, 2), nullable=True)
    favorito = Column(Boolean, nullable=True)

    criado_em = Column(DateTime, nullable=True)
    atualizado_em = Column(DateTime, nullable=True, index=True)
    ultima_atividade = Column(DateTime, nullable=True)
    respondido_em = Column(DateTime, nullable=True)

    # ── controle da sincronização ─────────────────────────────────────────────
    id_legado = Column(Integer, nullable=True, index=True)
    sincronizado_em = Column(DateTime, server_default=func.now(), nullable=True)

    __table_args__ = (
        # A tela quase sempre pede uma janela de datas dentro de uma equipe.
        Index("ix_leads_c2s_data_equipe", "data", "equipe"),
        Index("ix_leads_c2s_data_corretor", "data", "corretor"),
    )
