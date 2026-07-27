from sqlalchemy import (
    Column, String, Text, Date, DateTime, Boolean, Numeric, Integer, ForeignKey
)
from app.models.base import Base


class ClienteVisita(Base):
    """Espelha Dim_Cliente_Visita."""

    __tablename__ = "clientes_visita"

    id_cliente = Column(String(50), primary_key=True)
    nome_cliente = Column(String(255), nullable=True)
    telefone_cliente = Column(String(50), nullable=True)
    email_cliente = Column(String(255), nullable=True)
    created_by = Column(String(100), nullable=True)
    id_corretor = Column(String(50), nullable=True)


class ParceiroVisita(Base):
    """Espelha Dim_Parceiro_Visita."""

    __tablename__ = "parceiros_visita"

    id_parceiro = Column(String(50), primary_key=True)
    nome_parceiro = Column(String(255), nullable=True)
    imobiliaria = Column(String(255), nullable=True)
    id_corretor = Column(String(50), nullable=True)


class Visita(Base):
    """Espelha Fato_Visitas (19 colunas originais)."""

    __tablename__ = "visitas"

    id_visita = Column(String(50), primary_key=True)
    id_imovel = Column(Text, nullable=True)  # solto (sem FK); 1 linha na planilha tem endereco digitado aqui em vez de codigo
    data_visita = Column(Date, nullable=True)
    id_corretor = Column(String(50), nullable=True)
    anexo_ficha_visita = Column(Text, nullable=True)
    audiodescricao_cliente_visita = Column(Text, nullable=True)
    link_audio = Column(Text, nullable=True)
    link_imagem = Column(Text, nullable=True)
    visita_com_parceiro = Column(Boolean, nullable=True)
    tipo_captacao = Column(String(100), nullable=True)
    endereco_externo = Column(Text, nullable=True)
    proposta = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=True)
    created_by = Column(String(100), nullable=True)
    assinatura = Column(Text, nullable=True)
    id_cliente_assinante = Column(
        String(50), ForeignKey("clientes_visita.id_cliente"), nullable=True
    )
    id_parceiro = Column(
        String(50), ForeignKey("parceiros_visita.id_parceiro"), nullable=True
    )
    imovel_nao_captado = Column(Boolean, nullable=True)
    motivo_talvez = Column(Text, nullable=True)


class VisitaCliente(Base):
    """Espelha Fato_Cliente_Visita (associação visita <-> cliente)."""

    __tablename__ = "visita_cliente"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_clientevisita_origem = Column(String(50), nullable=True)
    id_visita = Column(String(50), ForeignKey("visitas.id_visita"), nullable=False)
    id_cliente = Column(
        String(50), ForeignKey("clientes_visita.id_cliente"), nullable=False
    )
    papel_na_visita = Column(String(50), nullable=True)


class VisitaParceiro(Base):
    """Espelha Fato_Parceiro_Visita (associação visita <-> parceiro)."""

    __tablename__ = "visita_parceiro"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_parceirovisita_origem = Column(String(50), nullable=True)
    id_visita = Column(String(50), ForeignKey("visitas.id_visita"), nullable=False)
    id_parceiro = Column(
        String(50), ForeignKey("parceiros_visita.id_parceiro"), nullable=False
    )
    papel_na_visita = Column(String(50), nullable=True)


class Avaliacao(Base):
    """Espelha Fato_Avaliacao."""

    __tablename__ = "avaliacoes_visita"

    id_avaliacao = Column(String(50), primary_key=True)
    id_visita = Column(String(50), ForeignKey("visitas.id_visita"), nullable=True)
    id_cliente = Column(
        String(50), ForeignKey("clientes_visita.id_cliente"), nullable=True
    )
    localizacao = Column(Numeric(4, 1), nullable=True)
    tamanho = Column(Numeric(4, 1), nullable=True)
    planta_imovel = Column(Numeric(4, 1), nullable=True)
    qualidade_acabamento = Column(Numeric(4, 1), nullable=True)
    estado_conservacao = Column(Numeric(4, 1), nullable=True)
    condominio_areacomun = Column(Numeric(4, 1), nullable=True)
    preco = Column(Numeric(4, 1), nullable=True)
    nota_geral = Column(Numeric(4, 1), nullable=True)
    preco_n10 = Column(String(50), nullable=True)
    created_by = Column(String(100), nullable=True)
    id_parceiro = Column(
        String(50), ForeignKey("parceiros_visita.id_parceiro"), nullable=True
    )
