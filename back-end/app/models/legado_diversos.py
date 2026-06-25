from sqlalchemy import Column, Integer, Text, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base


class ClienteLegado(Base):
    """Espelha 'Dim_Cliente' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "clientes_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cpf = Column(Text, nullable=True)  # 'CPF'
    nome = Column(Text, nullable=True)  # 'Nome'
    id_contrato = Column(Text, nullable=True)  # 'IdContrato'
    link_drive = Column(Text, nullable=True)  # 'Link_Drive'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class NichoLegado(Base):
    """Espelha 'Dim_Nicho' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "nichos_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    corretor = Column(Text, nullable=True)  # 'Corretor'
    nome = Column(Text, nullable=True)  # 'Nome'
    equipe = Column(Text, nullable=True)  # 'Equipe'
    gerente = Column(Text, nullable=True)  # 'Gerente'
    regiao = Column(Text, nullable=True)  # 'Região'
    bairro = Column(Text, nullable=True)  # 'Bairro'
    valor_min = Column(Text, nullable=True)  # 'Valor_min'
    valor_max = Column(Text, nullable=True)  # 'Valor_max'
    tipologia_1 = Column(Text, nullable=True)  # 'Tipologia_1'
    tipologia_2 = Column(Text, nullable=True)  # 'Tipologia_2'
    tipologia_3 = Column(Text, nullable=True)  # 'Tipologia_3'
    tipologia_4 = Column(Text, nullable=True)  # 'Tipologia_4'
    vaga = Column(Text, nullable=True)  # 'Vaga'
    n_cap_nicho = Column(Text, nullable=True)  # 'N_Cap_Nicho'
    estoque_nicho = Column(Text, nullable=True)  # 'Estoque_Nicho'
    n_estoque_total = Column(Text, nullable=True)  # 'N_Estoque_total'
    vgv_venda = Column(Text, nullable=True)  # 'VGV_Venda'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class TipoImovelLegado(Base):
    """Espelha 'Dim_Tipo' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "tipos_imovel_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_tipo = Column(Text, nullable=True, unique=True)  # 'IdTipo'
    nome = Column(Text, nullable=True)  # 'Nome'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class BairroLegado(Base):
    """Espelha 'Dim_Bairro' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "bairros_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_bairro = Column(Text, nullable=True, unique=True)  # 'IdBairro'
    nome = Column(Text, nullable=True)  # 'Nome'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class ImovelLegado(Base):
    """Espelha 'Dim_Imovel' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "imoveis_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(Text, nullable=True)  # 'Código' (tem duplicata - reanuncios; nao e PK)
    tipo = Column(Text, ForeignKey("tipos_imovel_legado.id_tipo"), nullable=True)  # 'Tipo'
    valor = Column(Text, nullable=True)  # 'Valor'
    bairro = Column(Text, ForeignKey("bairros_legado.id_bairro"), nullable=True)  # 'Bairro'
    foco_pp = Column(Boolean, nullable=True)  # 'Foco PP'
    foco_ac = Column(Boolean, nullable=True)  # 'Foco AC'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class DiretorLegado(Base):
    """Espelha 'Dim_Diretor' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "diretores_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_diretor = Column(Text, nullable=True)  # 'IdDiretor'
    nome = Column(Text, nullable=True)  # 'Nome'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class AnuncioImovelLegado(Base):
    """Espelha 'Dim_AnuncioImóvel' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "anuncios_imovel_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_anuncio = Column(Text, nullable=True)  # 'IdAnuncio'
    cod = Column(Text, nullable=True)  # 'Cod'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class PortalLegado(Base):
    """Espelha 'Dim_Portal' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "portais_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    categoria = Column(Text, nullable=True)  # 'Categoria'
    limite = Column(Text, nullable=True)  # 'Limite'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class FonteLegado(Base):
    """Espelha 'Dim_Fonte' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "fontes_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(Text, nullable=True)  # 'Codigo'
    nome = Column(Text, nullable=True)  # 'Nome'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class AtendimentoLegado(Base):
    """Espelha 'Dim_Atendimento' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "atendimentos_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(Text, nullable=True)  # 'Codigo'
    nome = Column(Text, nullable=True)  # 'Nome'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class CampanhaLegado(Base):
    """Espelha 'Fato_Campanhas' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "campanhas_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_campanha = Column(Text, nullable=True)  # 'Nome da campanha'
    nome_conjunto_anuncios = Column(Text, nullable=True)  # 'Nome do conjunto de anúncios'
    nome_anuncio = Column(Text, nullable=True)  # 'Nome do anúncio'
    dia = Column(Date, nullable=True)  # 'Dia'
    alcance = Column(Text, nullable=True)  # 'Alcance'
    impressoes = Column(Text, nullable=True)  # 'Impressões'
    frequencia = Column(Text, nullable=True)  # 'Frequência'
    montante_gasto_brl = Column(Text, nullable=True)  # 'Montante gasto (BRL)'
    definicao_atribuicao = Column(Text, nullable=True)  # 'Definição de atribuição'
    comeca_a = Column(Date, nullable=True)  # 'Começa a'
    termina_a = Column(Date, nullable=True)  # 'Termina a'
    tipo_resultado = Column(Text, nullable=True)  # 'Tipo de resultado'
    resultados = Column(Text, nullable=True)  # 'Resultados'
    custo_por_resultado = Column(Text, nullable=True)  # 'Custo por resultado'
    inicio_relatorios = Column(Date, nullable=True)  # 'Início dos relatórios'
    fim_relatorios = Column(Date, nullable=True)  # 'Fim dos relatórios'
    id_anuncio = Column(Text, nullable=True)  # 'IdAnuncio'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class MetaMensalLegado(Base):
    """Espelha 'Fato_Meta_Mensal' (Base Inteligência 61 (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "metas_mensais_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mes = Column(Date, nullable=True)  # 'Mes'
    id_gerente = Column(Text, nullable=True)  # 'IdGerente'
    equipe = Column(Text, nullable=True)  # 'Equipe'
    meta_cap = Column(Text, nullable=True)  # 'Meta_Cap'
    meta_vgv = Column(Text, nullable=True)  # 'Meta_VGV'
    super_meta_cap = Column(Text, nullable=True)  # 'Super_Meta_Cap'
    super_meta_vgv = Column(Text, nullable=True)  # 'Super_Meta_Vgv'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class RecebidoLegado(Base):
    """Espelha 'Recebido' (Controle de Contratos 61 Imóveis (7).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "recebidos_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(Date, nullable=True)  # 'Data'
    contrato = Column(Text, nullable=True)  # 'Contrato'
    valor_recebido = Column(Text, nullable=True)  # 'Valor Recebido'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class RelatorioImovelLegado(Base):
    """Espelha 'Relatorio_Imovel' (Modelo_Visitas (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "relatorios_imovel_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_relatorio = Column(Text, nullable=True)  # 'Id_Relatorio'
    id_imovel = Column(Text, nullable=True)  # 'Id_Imovel'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class SessaoUsuarioLegado(Base):
    """Espelha 'Sessao_Usuario' (Modelo_Visitas (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "sessoes_usuario_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_sessao = Column(Text, nullable=True)  # 'IdSessao'
    id_corretor = Column(Text, nullable=True)  # 'IdCorretor'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class AdminLegado(Base):
    """Espelha 'App_Admins' (Modelo_Visitas (6).xlsx). Tudo Text/Date/Boolean conforme a celula - sem perder dado."""

    __tablename__ = "admins_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(Text, nullable=True)  # 'Email'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)


class MenuLegado(Base):
    """Espelha Menu_Corretor/Menu_Gerente/Menu_Sem_Cadastro (Modelo_Visitas.xlsx)."""

    __tablename__ = "menus_legado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_menu = Column(Text, nullable=True)  # corretor / gerente / sem_cadastro
    id_item = Column(Text, nullable=True)  # 'Id'
    titulo = Column(Text, nullable=True)  # 'Titulo'
    subtitulo = Column(Text, nullable=True)  # 'Subtitulo'
    icone = Column(Text, nullable=True)  # 'Icone'
    deep_link = Column(Text, nullable=True)  # 'DeepLink'
    ordem = Column(Text, nullable=True)  # 'Ordem'
    created_at = Column(DateTime, server_default=func.now(), nullable=True)

