import re
from typing import List, Optional

# Interface Base (Protocolo)
class BaseParser:
    def parse(self, text: str) -> dict:
        raise NotImplementedError

# Exemplo de Template (Mockado por enquanto)
class TemplateVencedorAtacadista(BaseParser):
    def parse(self, text: str) -> dict:
        # AQUI VAI A LOGICA HARDCODED (REGEX PURO) PARA ESSE CLIENTE ESPECIFICO
        # Isso economiza token da IA.
        # Por enquanto retornamos um exemplo fixo para provar que a rota funcionou
        return {
            "source": "TEMPLATE_HARDCODED",
            "pedidos": [
                {
                    "numero_pedido": "HARDCODED-123",
                    "cliente": {"nome": "VENCEDOR ATACADISTA", "cnpj_cpf": "76857747000475"},
                    "produtos": [],
                    "total_pedido_validacao": 0.0
                }
            ]
        }

class ParserFactory:
    """
    Registro central de Templates.
    Chave = CNPJ (apenas números)
    Valor = Classe do Parser
    """
    _registry = {
    }

    @staticmethod
    def get_parser_for_text(text: str) -> Optional[BaseParser]:
        """
        Escaneia o texto procurando CNPJs conhecidos.
        Se achar um CNPJ que tem template, retorna o template.
        """
        # Regex para extrair todos os CNPJs do texto
        # Remove pontuação para comparar
        found_cnpjs = re.findall(r'\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}', text)
        
        clean_cnpjs = [re.sub(r'\D', '', c) for c in found_cnpjs]
        
        # Verifica se algum CNPJ encontrado tem registro
        for cnpj in clean_cnpjs:
            if cnpj in ParserFactory._registry:
                return ParserFactory._registry[cnpj]
        
        return None