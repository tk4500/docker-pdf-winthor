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
        
        # Extrair Número do Pedido
        numero_pedido_match = re.search(r"Número do Pedido:\\s*(\\d+)", text)
        numero_pedido = numero_pedido_match.group(1) if numero_pedido_match else None

        # Extrair Fornecedor
        fornecedor_match = re.search(r"Fornecedor:\\s*\\d+\\s*-\\s*(.*?)\\s*Endereço:", text, re.DOTALL)
        fornecedor_nome = fornecedor_match.group(1).strip() if fornecedor_match else None
        
        fornecedor_cnpj_match = re.search(r"CNPJ:\\s*(\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2})", text)
        fornecedor_cnpj = fornecedor_cnpj_match.group(1).replace(".", "").replace("/", "").replace("-", "") if fornecedor_cnpj_match else None

        # Extrair Cliente
        cliente_nome_match = re.search(r"Empresa:\\s*(.*?)\\s*Endereço:", text)
        cliente_nome = cliente_nome_match.group(1).strip() if cliente_nome_match else None
        
        cliente_cnpj_match = re.search(r"N PJ:\\s*(\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{1})", text)
        cliente_cnpj = cliente_cnpj_match.group(1).replace(".", "").replace("/", "").replace("-", "") if cliente_cnpj_match else None

        # Extrair Total do Pedido
        total_pedido_match = re.search(r"Total\\s*\
\\s*(\\d{1,3}(?:\\.\\d{3})*,\\d{2})\\s*$", text, re.MULTILINE)
        total_pedido_str = total_pedido_match.group(1).replace(".", "").replace(",", ".") if total_pedido_match else None
        total_pedido_validacao = float(total_pedido_str) if total_pedido_str else None

        # Extrair Itens do Pedido
        produtos = []
        # Regex para capturar cada linha de produto, incluindo descrições multi-linha e os dados numéricos
        # A regex foi ajustada para lidar com a formatação peculiar dos números e descrições.
        # Ela busca o código, a descrição (que pode ter quebras de linha), UN/CX, quantidade, valor unitário e valor total.
        # A segunda linha de cada item (Ref: EAN:) é usada para extrair o EAN e, em alguns casos, a unidade de embalagem se não estiver na primeira linha.
        
        # Padrão para a primeira linha do item
        item_pattern_line1 = re.compile(
            r"^\\s*(\\d+)\\s+"  # Código de referência (Grupo 1)
            r"(.+?)\\s+"      # Descrição do produto (Grupo 2) - não guloso
            r"(UN|CX)\\s+"    # Unidade de embalagem (Grupo 3)
            r"(\\d+)\\s+"      # Quantidade total (Grupo 4)
            r"(\\d{1,3}(?:,\\d{3})*\\.\\d{2})\\s+" # Valor unitário (Grupo 5)
            r"(\\d{1,3}(?:,\\d{3})*\\.\\d{2})"   # Valor total (Grupo 6)
            , re.MULTILINE
        )

        # Padrão para a segunda linha do item (EAN e possível unidade de embalagem)
        item_pattern_line2 = re.compile(
            r"Ref:.*?EAN:\\s*(\\d+)\\s*(?:UN\\s*(\\d+))?" # EAN (Grupo 1), Unidade de embalagem (Grupo 2, opcional)
        )

        # Dividir o texto em seções para facilitar a extração dos itens
        items_section_match = re.search(r"ITENS DO PEDIDO\\s*Ite m Produto Descritivo.*?(\\d{1,3}(?:\\.\\d{3})*,\\d{2})\\s*$", text, re.DOTALL)
        items_section = items_section_match.group(0) if items_section_match else ""
        
        # Remover o cabeçalho da tabela de itens
        items_section = re.sub(r"ITENS DO PEDIDO\\s*Ite m Produto Descritivo.*?Preço Emb\\.", "", items_section, flags=re.DOTALL)
        
        # Remover a seção de totalização para não interferir na extração dos itens
        items_section = re.sub(r"TOTALIZAÇÃO DO PEDIDO.*", "", items_section, flags=re.DOTALL)

        # Processar cada item
        lines = items_section.strip().split('\
')
        i = 0
        while i < len(lines):
            line1_match = item_pattern_line1.match(lines[i])
            if line1_match:
                codigo_referencia = line1_match.group(1)
                descricao_base = line1_match.group(2).strip()
                unidade_embalagem = line1_match.group(3)
                quantidade_total = int(line1_match.group(4))
                valor_unitario = float(line1_match.group(5).replace(",", ""))
                valor_total = float(line1_match.group(6).replace(",", ""))
                
                ean = None
                
                # Procurar a linha do EAN, que pode estar na linha seguinte ou algumas linhas abaixo
                j = i + 1
                current_description = descricao_base
                while j < len(lines):
                    line2_match = item_pattern_line2.search(lines[j])
                    if line2_match:
                        ean = line2_match.group(1)
                        # Se a unidade de embalagem não foi capturada na primeira linha, tentar da segunda
                        if not unidade_embalagem and line2_match.group(2):
                            unidade_embalagem = line2_match.group(2)
                        break
                    
                    # Se a linha não é de EAN e não é o início de um novo item, pode ser continuação da descrição
                    if not item_pattern_line1.match(lines[j]):
                        current_description += " " + lines[j].strip()
                    else:
                        # É o início de um novo item, então a descrição terminou
                        break
                    j += 1
                
                # Limpar a descrição de caracteres indesejados e espaços extras
                current_description = re.sub(r'\\s+', ' ', current_description).strip()
                current_description = re.sub(r'UN\\s*\\d+\\s*$', '', current_description).strip() # Remove UN e quantidade do final se estiver lá
                current_description = re.sub(r'CX\\s*\\d+\\s*$', '', current_description).strip() # Remove CX e quantidade do final se estiver lá
                
                produtos.append({
                    "descricao": current_description,
                    "codigo_referencia": codigo_referencia,
                    "ean": ean,
                    "unidade_embalagem": unidade_embalagem,
                    "quantidade_total": quantidade_total,
                    "valor_unitario": valor_unitario,
                    "valor_total": valor_total
                })
                i = j # Avança o índice para a linha após o EAN
            else:
                i += 1 # Se não encontrou um item, avança para a próxima linha

        pedidos.append({
            "numero_pedido": numero_pedido,
            "total_pedido_validacao": total_pedido_validacao,
            "fornecedor": {
                "nome": fornecedor_nome,
                "cnpj_cpf": fornecedor_cnpj
            },
            "cliente": {
                "nome": cliente_nome,
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
        found_cnpjs = re.findall(r'\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}', text)
        
        clean_cnpjs = [re.sub(r'\D', '', c) for c in found_cnpjs]
        logger.info(f"CNPJs encontrados no texto: {clean_cnpjs}")
        
        # Verifica se algum CNPJ encontrado tem registro
        for cnpj in clean_cnpjs:
            cnpj_raiz = int(cnpj[:8]) # Usamos apenas a raiz para o registro
            if cnpj_raiz in ParserFactory._registry:
                return ParserFactory._registry[cnpj_raiz]
        
        return None