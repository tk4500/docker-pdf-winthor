from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import uuid
from sqlalchemy import Table

role_permissions = Table(
    'role_permissions', Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id')),
    Column('permission_id', Integer, ForeignKey('permissions.id'))
)

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True) # Ex: "pedido:upload"
    description = Column(String) # Ex: "Permite enviar novos arquivos"

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Ex: "Gerente de Vendas"
    
    # Relacionamento M-N
    permissions = relationship("Permission", secondary=role_permissions, lazy="joined")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    email = Column(String)
    winthor_password = Column(String)
    ativo = Column(Boolean, default=True)
    # Agora o usuário aponta para uma Role
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    role = relationship("Role", lazy="joined") # lazy="joined" carrega a role junto na query


class Configuracao(Base):
    __tablename__ = 'configuracoes'
    id = Column(Integer, primary_key=True)
    chave = Column(String, unique=True, index=True)
    valor = Column(String)
    descricao = Column(String)

class Cliente(Base):
    __tablename__ = 'clientes'
    id = Column(Integer, primary_key=True) # ID Único do Winthor
    # REMOVIDO unique=True do cnpj_cpf
    cnpj_cpf = Column(String, index=True) 
    razao_social = Column(String)
    plano_pag_padrao = Column(Integer)
    sellerId = Column(Integer) # Vendedor padrão no Winthor
    chargingId = Column(String) # ID de cobrança no Winthor
    regionId = Column(Integer) # Região do cliente (para regras de negócio específicas)
    ativo = Column(Boolean, default=True)
    
    aliases = relationship("ProdutoAlias", back_populates="cliente")

class Produto(Base):
    __tablename__ = 'produtos'
    id = Column(Integer, primary_key=True) # ID Único do Winthor
    nome = Column(String)
    ean = Column(String, index=True)
    unidade = Column(String)
    ativo = Column(Boolean, default=True)
    
    aliases = relationship("ProdutoAlias", back_populates="produto")

class ProdutoAlias(Base):
    __tablename__ = 'produto_aliases'
    id = Column(Integer, primary_key=True, index=True)
    id_cliente = Column(Integer, ForeignKey('clientes.id'))
    id_produto = Column(Integer, ForeignKey('produtos.id'))
    
    codigo_cliente = Column(String, index=True)
    tipo = Column(String)

    cliente = relationship("Cliente", back_populates="aliases")
    produto = relationship("Produto", back_populates="aliases")

class HistoricoPedido(Base):
    __tablename__ = 'historico_pedidos'
    id = Column(Integer, primary_key=True, index=True)
    data_upload = Column(DateTime, default=datetime.utcnow)
    nome_arquivo = Column(String)
    json_entrada = Column(JSON)
    json_final = Column(JSON)
    status = Column(String)

class ProcessamentoPedido(Base):
    __tablename__ = 'processamentos'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # --- Rastreabilidade e Permissão (Req 3) ---
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) 
    user = relationship("User")
    
    # --- Hierarquia (Req 10 - Split de Pedidos) ---
    # Se um PDF gera 3 pedidos, o PDF é o Pai e os 3 pedidos são filhos
    job_pai_id = Column(String, ForeignKey("processamentos.id"), nullable=True)
    
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_finalizacao = Column(DateTime, nullable=True)
    
    nome_arquivo = Column(String) 
    # Status: PENDENTE, EXTRAINDO, VALIDANDO, AGUARDANDO_APROVACAO, ENVIADO, CANCELADO, ERRO
    status_global = Column(String, default="PENDENTE") 
    
    # --- Flags de Comportamento (Req 5, 8, 9) ---
    origem_entrada = Column(String, default="PDF") # PDF, JSON_UPLOAD, MANUAL
    is_bonificacao = Column(Boolean, default=False) # Req 8 (Muda SaleType)
    auto_process = Column(Boolean, default=False)   # Req 5 (Tenta ir até o fim)
    force_ai = Column(Boolean, default=False)       # Req 9 (Ignora Template)
    
    # Dados
    resultado_json = Column(JSON, nullable=True)
    mensagem_erro = Column(String, nullable=True)
    
    # ID retornado pelo Winthor (para cancelamento - Req 6)
    winthor_order_id = Column(String, nullable=True)

class ProdutoConversao(Base):
    """
    Tabela para converter produtos unitários em caixas automaticamente.
    Ex: Chamyto Unitário (ID 100) -> Chamyto Pack 6 (ID 200). Fator = 6.
    """
    __tablename__ = 'produto_conversoes'
    id = Column(Integer, primary_key=True, index=True)
    
    id_produto_origem = Column(Integer, ForeignKey('produtos.id'), unique=True) # O que vem no PDF
    id_produto_destino = Column(Integer, ForeignKey('produtos.id'))             # O que vai pro Winthor
    
    fator = Column(Float) # Ex: 6.0 (Multiplica preço, Divide quantidade)
    
    # Relacionamentos para facilitar
    produto_origem = relationship("Produto", foreign_keys=[id_produto_origem])
    produto_destino = relationship("Produto", foreign_keys=[id_produto_destino])