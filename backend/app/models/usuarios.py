from sqlalchemy import Column, Integer, String, Text, Boolean, Date
from app.models.base import Base


class Usuarios(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100))
    password = Column(String(255))
    team = Column(String(100))
    nome      = Column(String(100), nullable=True)
    email     = Column(String(255), nullable=True)
    telefone  = Column(String(20), nullable=True)
    instagram = Column(String(100), nullable=True)
    descricao = Column(Text, nullable=True)
    permissao = Column(String(20))
    id_usuarios = Column(String(50))
    ativo = Column(Boolean, nullable=False, default=True)
    id_imoview = Column(String(50), nullable=True)
    status = Column(String(30), nullable=True)
    unidade = Column(String(100), nullable=True)
    gerente_responsavel = Column(String(100), nullable=True)
    data_entrada_61 = Column(Date, nullable=True)
    creci = Column(String(50), nullable=True)
    validade_creci = Column(Date, nullable=True)
    telefone_pessoal = Column(String(30), nullable=True)
    telefone_corporativo = Column(String(30), nullable=True)
    email_pessoal = Column(String(255), nullable=True)
    email_corporativo = Column(String(255), nullable=True)
    data_nascimento = Column(Date, nullable=True)
    estado_civil = Column(String(50), nullable=True)
    possui_filhos = Column(Boolean, nullable=True)
    endereco = Column(Text, nullable=True)
    contato_emergencia = Column(Text, nullable=True)
    cpf = Column(String(20), nullable=True)
    rg = Column(String(30), nullable=True)
    cnpj = Column(String(30), nullable=True)
    razao_social = Column(String(255), nullable=True)
    banco = Column(String(100), nullable=True)
    agencia = Column(String(30), nullable=True)
    conta = Column(String(50), nullable=True)
    tipo_conta = Column(String(30), nullable=True)
    chave_pix = Column(String(255), nullable=True)
    contrato_assinado = Column(Boolean, nullable=True)
    codigo_conduta_assinado = Column(Boolean, nullable=True)
    lgpd_assinada = Column(Boolean, nullable=True)
    onboarding_realizado = Column(Boolean, nullable=True)
    desligado = Column(Boolean, nullable=True, default=False)
    data_desligamento = Column(Date, nullable=True)
    # Pasta do Drive com os documentos do corretor (contrato, CRECI, RG...).
    # E link, nao upload: os arquivos continuam no Drive do RH.
    link_documentos = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)


