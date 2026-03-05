import logging
import re
from typing import List, Optional

logger = logging.getLogger("ParserFactory")
# Interface Base (Protocolo)
class BaseParser:
    def parse(self, text: str) -> dict:
        raise NotImplementedError
    
class TemplateMoniariParser(BaseParser):
    def parse(self, text: str) -> dict:
        data = {}
        pedidos = []
        
        # Extract general order data
        numero_pedido_match = re.search(r"Número do Pedido:\\s*(\\d+)", text)
        numero_pedido = numero_pedido_match.group(1) if numero_pedido_match else None

        total_pedido_match = re.search(r"Total\\s*(\\d{1,3}(?:\\.\\d{3})*,\\d{2})\\s*$", text, re.MULTILINE)
        total_pedido_str = total_pedido_match.group(1).replace('.', '').replace(',', '.') if total_pedido_match else "0.00"
        total_pedido_validacao = float(total_pedido_str)

        # Extract supplier data
        fornecedor_name_match = re.search(r"Fornecedor:\\s*\\d+\\s*-\\s*(.+)", text)
        fornecedor_name = fornecedor_name_match.group(1).strip() if fornecedor_name_match else None

        fornecedor_cnpj_match = re.search(r"CNPJ:\\s*(\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2})", text)
        fornecedor_cnpj = fornecedor_cnpj_match.group(1).replace('.', '').replace('/', '').replace('-', '') if fornecedor_cnpj_match else None

        # Extract client data
        cliente_name_match = re.search(r"Empresa:\\s*(.+)", text)
        cliente_name = cliente_name_match.group(1).strip() if cliente_name_match else None

        cliente_cnpj_match = re.search(r"N PJ:\\s*(\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{1})", text)
        cliente_cnpj = cliente_cnpj_match.group(1).replace('.', '').replace('/', '').replace('-', '') if cliente_cnpj_match else None

        # Extract products
        produtos = []
        # Regex to capture product lines, including multi-line descriptions and the EAN on the next line
        # It looks for a line starting with 'Ite m' to identify the header, then captures lines below it.
        # The product lines are tricky due to the variable spacing and the EAN on a separate line.
        # We'll capture the main product line and then the EAN line separately.
        
        # The product data starts after "ITENS DO PEDIDO" and before "TOTALIZAÇÃO DO PEDIDO"
        items_section_match = re.search(r"ITENS DO PEDIDO\\s*Ite m Produto Descritivo.*?(\\d{1,5}\\s+.*?)(?=\\s*TOTALIZAÇÃO DO PEDIDO)", text, re.DOTALL)
        
        if items_section_match:
            items_section = items_section_match.group(0)
            
            # Regex to capture each product block.
            # It starts with a product code (5 digits), then description, UN, Emb, Qtde, Price, Total Price.
            # The EAN is on the next line, sometimes with "Ref:" or "UN 1".
            product_pattern = re.compile(
                r"^\\s*(\\d{1,5})\\s+(.*?)\\s+(UN|CX)\\s+(\\d+)\\s+(\\d+)\\s+([\\d,.]+)\\s+([\\d,.]+)\\s+[\\d,.]+\\s+[\\d,.]+\\s+([\\d,.]+)\\s+[\\d,.]+\\s+[\\d,.]+\\s*\
" # Main product line
                r"(?:Ref:\\s*.*?)?\\s*EAN:\\s*(\\d+)\\s*.*?$", # EAN line
                re.MULTILINE
            )

            # Find all matches in the items section
            for match in product_pattern.finditer(items_section):
                codigo_referencia = match.group(1).strip()
                descricao_raw = match.group(2).strip()
                unidade_embalagem = match.group(3).strip()
                # The 'Emb' column is actually the quantity for some items, and 'Qtde' is the inner quantity.
                # For simplicity, we'll use the 'Qtde' column as the total quantity as per the JSON.
                quantidade_total = int(match.group(5)) 
                valor_unitario = float(match.group(6).replace('.', '').replace(',', '.'))
                valor_total = float(match.group(7).replace('.', '').replace(',', '.'))
                ean = match.group(8).strip()

                # Clean up description - remove "UN 1" if present, and extra spaces
                descricao = re.sub(r'\\s*UN\\s+\\d+\\s*', ' ', descricao_raw).strip()
                # Remove any trailing "UN 1" or similar from the description if it's not part of the actual product name
                descricao = re.sub(r'\\s+UN\\s+\\d+$', '', descricao).strip()
                # Remove any extra EANs that might have been picked up in the description
                descricao = re.sub(r'EAN:\\s*\\d+', '', descricao).strip()
                # Remove any Ref: codes that might have been picked up in the description
                descricao = re.sub(r'Ref:\\s*\\d+', '', descricao).strip()
                # Remove any stray numbers that look like quantities or prices
                descricao = re.sub(r'\\s+\\d{1,3}(?:,\\d{2})?$', '', descricao).strip()
                
                # Special handling for "IOGURTE NESTLE 1,250KG CX 12 2 11,88 142,56"
                # The 'CX 12' is part of the description, and '2' is the quantity.
                # The JSON has quantity_total as 24 for this item.
                # This implies that 'Qtde' (2) * 'Emb' (12) = 24.
                # Let's re-evaluate the quantity extraction for this specific case.
                # For most items, 'Qtde' is the total quantity.
                # For "IOGURTE NESTLE 1,250KG CX 12", the 'Emb' is 12 and 'Qtde' is 2.
                # The JSON shows 24. So it's Emb * Qtde.
                # For "PRESUNTO SULFRIOS FAT 150G CX 30 1", Emb is 30, Qtde is 1. JSON shows 30.
                # So, it seems `quantidade_total` should be `int(match.group(4)) * int(match.group(5))`
                
                # Let's re-extract quantity based on this observation
                emb_val = int(match.group(4))
                qtde_val = int(match.group(5))
                calculated_quantidade_total = emb_val * qtde_val

                produtos.append({
                    "descricao": descricao,
                    "codigo_referencia": codigo_referencia,
                    "ean": ean,
                    "unidade_embalagem": unidade_embalagem,
                    "quantidade_total": calculated_quantidade_total,
                    "valor_unitario": valor_unitario,
                    "valor_total": valor_total
                })

        pedidos.append({
            "numero_pedido": numero_pedido,
            "total_pedido_validacao": total_pedido_validacao,
            "fornecedor": {
                "nome": fornecedor_name,
                "cnpj_cpf": fornecedor_cnpj
            },
            "cliente": {
                "nome": cliente_name,
                "cnpj_cpf": cliente_cnpj
            },
            "produtos": produtos
        })

        data["pedidos"] = pedidos
        return data

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
        83814814: TemplateMoniariParser(),
    }

    @staticmethod
    def get_parser_for_text(text: str) -> Optional[BaseParser]:
        """
        Escaneia o texto procurando CNPJs conhecidos.
        Se achar um CNPJ que tem template, retorna o template.
        """
        # Regex para extrair todos os CNPJs do texto
        # Remove pontuação para comparar
        found_cnpjs = re.findall(r'\d{2}\.?\d{3}\.?\d{3}/?\d{4}', text)
        
        clean_cnpjs = [re.sub(r'\D', '', c) for c in found_cnpjs]
        logger.info(f"CNPJs encontrados no texto: {clean_cnpjs}")
        
        # Verifica se algum CNPJ encontrado tem registro
        for cnpj in clean_cnpjs:
            cnpj_raiz = int(cnpj[:8]) # Usamos apenas a raiz para o registro
            if cnpj_raiz in ParserFactory._registry:
                return ParserFactory._registry[cnpj_raiz]
        
        return None