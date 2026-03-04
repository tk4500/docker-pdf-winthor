from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Autenticação & Usuários ---
class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    role: str = "operador"
    
class ProdutoUpdate(BaseModel):
    nome: Optional[str] = None
    ean: Optional[str] = None
    unidade: Optional[str] = None
    ativo: Optional[bool] = None
    
class PrecoRequest(BaseModel):
    cliente_id: int
    produto_id: int

class RoleCreate(BaseModel):
    name: str
    permissions_slugs: List[str]

class ClienteUpdate(BaseModel):
    id: int
    cnpj_cpf: str
    razao_social: str
    plano_pag_padrao: str
    sellerId: str
    chargingId: str
    regionId: str

# --- Configuração ---
class ConfigItem(BaseModel):
    chave: str
    valor: str
    descricao: Optional[str] = None

class ConfiguracaoUpdate(BaseModel):
    chave: str
    valor: str

# --- Pedidos & Filtros ---
class JobListFilter(BaseModel):
    status: Optional[str] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None

class PedidoFinalInput(BaseModel):
    pedido: dict  # O Frontend manda o objeto do pedido completo já corrigido

class ListaPedidosSync(BaseModel):
    ids: List[int]

# --- Buscas ---
class BuscaItem(BaseModel):
    termo: str

class PedidoOptions(BaseModel):
    """Opções passadas na criação/upload"""
    auto_process: bool = False
    is_bonificacao: bool = False
    force_ai: bool = False

class PedidoCreateManual(BaseModel):
    """Req 1 e 7: Criar pedido via JSON direto"""
    cliente_id: int # ID do Winthor
    itens: List[dict] # Lista de produtos {id_produto: 1, quantidade: 10}
    options: PedidoOptions = PedidoOptions()

class PedidoFinalInput(BaseModel):
    pedido: dict
    options: Optional[PedidoOptions] = None # Permite mudar flags na finalização

