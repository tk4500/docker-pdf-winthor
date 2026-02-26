from sqlalchemy.orm import Session
from models import Produto, ProdutoAlias, Cliente
import logging
from winthor_client import WinthorClient

logger = logging.getLogger("Validator")

class OrderValidator:
    def __init__(self, db: Session):
        self.db = db
        self.winthor_client = WinthorClient(db) 

    def validar_lote_pedidos(self, dados_parsed: dict) -> dict:
        """
        Recebe: { "metodo": "IA", "dados": { "pedidos": [...] } }
        Retorna: JSON enriquecido com status e IDs do Winthor.
        """
        pedidos_output = []
        
        # Garante que acessamos a lista correta (alguns parsers retornam direto, outros dentro de 'dados')
        lista_pedidos_raw = dados_parsed.get("dados", {}).get("pedidos", [])
        if not lista_pedidos_raw:
             # Fallback caso a estrutura venha diferente
             lista_pedidos_raw = dados_parsed.get("pedidos", [])

        for pedido_raw in lista_pedidos_raw:
            pedido_validado = self._validar_pedido_individual(pedido_raw)
            pedidos_output.append(pedido_validado)

        return {
            "metodo_processamento": dados_parsed.get("metodo_processamento"),
            "pedidos": pedidos_output,
            "resumo": {
                "total_pedidos": len(pedidos_output),
                "pedidos_validos": sum(1 for p in pedidos_output if p['status_pedido'] == 'VALIDO'),
                "pedidos_atencao": sum(1 for p in pedidos_output if p['status_pedido'] != 'VALIDO')
            }
        }

    def _validar_pedido_individual(self, pedido: dict) -> dict:
        """Processa um único pedido e seus itens"""
        erros_pedido = []
        itens_validados = []
        if pedido.get('dados_cliente'):
            cliente_db = self.db.query(Cliente).filter(Cliente.id == pedido['dados_cliente'].get('id_winthor')).first()
            cnpj_cliente = cliente_db.cnpj_cpf if cliente_db else pedido.get('dados_cliente', {}).get('cnpj_original')
            if not cliente_db:
                cliente_db = self.db.query(Cliente).filter(Cliente.cnpj_cpf.ilike(cnpj_cliente[:12])).first()  # Tenta buscar por CNPJ sem os últimos dígitos
                if cliente_db:
                    cnpj_cliente = cliente_db.cnpj_cpf
        else:
            cnpj_cliente = "".join(filter(str.isdigit, pedido.get('cliente', {}).get('cnpj_cpf', '')))
            cliente_db = self.db.query(Cliente).filter(Cliente.cnpj_cpf == cnpj_cliente).first()
            if not cliente_db:
                cliente_db = self.db.query(Cliente).filter(Cliente.cnpj_cpf.ilike(cnpj_cliente[:12])).first()  # Tenta buscar por CNPJ sem os últimos dígitos
                if cliente_db:
                    cnpj_cliente = cliente_db.cnpj_cpf
        # 1. Validar Cliente
        client_id = cliente_db.id if cliente_db else None
        info_cliente = {
            "encontrado": bool(cliente_db),
            "id_winthor": client_id,
            "razao_social": cliente_db.razao_social if cliente_db else pedido.get('cliente', {}).get('nome'),
            "cnpj_original": cnpj_cliente
        }
        
        if not cliente_db:
            erros_pedido.append("Cliente não cadastrado no Winthor")

        # 2. Validar Itens
        total_calculado_sistema = 0.0
        
        for item in pedido.get('produtos', []):
            item_status = "OK"
            item_msgs = []
            id_produto_winthor = None
            prod_db = None
            
            # A. Busca Produto (Ordem: EAN -> Alias -> CodigoRef)
            ean = "".join(filter(str.isdigit, str(item.get('ean', ''))))
            id_raw = "".join(filter(str.isdigit, str(item.get('id_produto_winthor', ''))))
            cod_ref = str(item.get('codigo_referencia', ''))
            
            
            if id_raw:
                prod_db = self.db.query(Produto).filter(Produto.id == int(id_raw)).first()
            if not prod_db and ean:
                prod_db = self.db.query(Produto).filter(Produto.ean == ean).first()

            if not prod_db and cliente_db:
                alias_db = self.db.query(ProdutoAlias).filter(
                    ProdutoAlias.id_cliente == cliente_db.id,
                    ProdutoAlias.codigo_cliente == cod_ref
                ).first()
                if alias_db:
                    prod_db = self.db.query(Produto).filter(Produto.id == alias_db.id_produto).first()
                    item_msgs.append("Produto encontrado via Alias")

            if prod_db:
                id_produto_winthor = prod_db.id
            else:
                item_status = "NAO_ENCONTRADO"
                item_msgs.append("Produto não encontrado (EAN/Alias desconhecido)")
                
            # B. Validação Matemática
            qtd = float(item.get('quantidade_total', 0))
            vlr_unit = float(item.get('valor_unitario', 0))
            vlr_total_pdf = float(item.get('valor_total', 0))
            
            total_linha_calc = round(qtd * vlr_unit, 2)
            
            # Tolerância de 1 centavo
            if abs(total_linha_calc - vlr_total_pdf) > 0.05:
                
                corrigido = False
                
                if qtd > 0:
                    vlr_unit_impl = vlr_total_pdf / qtd
                    aceitavel = False
                    vlr_padrao = self.winthor_client.get_price_from_id(id_produto_winthor, client_id)
                    if vlr_padrao:
                        variacao = abs(vlr_unit_impl - vlr_padrao) / vlr_padrao
                        if variacao <= 0.40:  # Até 40% de variação aceitável
                            aceitavel = True
                    else:
                        inteiritude = vlr_total_pdf / vlr_unit
                        variacao = abs(inteiritude - round(inteiritude)) / round(inteiritude) if round(inteiritude) > 0 else 1
                        if variacao <= 0.01:  # Até 1% de variação aceitável para inteiritude
                            aceitavel = True
                    if aceitavel:
                        vlr_unit = round(vlr_unit_impl, 2)
                        total_linha_calc = round(qtd * vlr_unit, 2)
                        if item_status == "OK": item_status = "CORRIGIDO_AUTO"
                        item_msgs.append(f"Valor unitário ajustado para {vlr_unit} com base no total do PDF")
                        corrigido = True
                # Se status era OK, vira ATENCAO. Se era NAO_ENCONTRADO, mantem.
                if not corrigido:
                    if item_status == "OK": item_status = "DIVERGENCIA_VALOR"
                    item_msgs.append(f"Cálculo diverge: PDF {vlr_total_pdf} vs Calc {total_linha_calc}")
                
            total_calculado_sistema += total_linha_calc

            # Monta item validado
            itens_validados.append({
                **item, # Copia dados originais
                "id_produto_winthor": id_produto_winthor,
                "valor_unitario": vlr_unit,
                "valor_total_calculado": total_linha_calc,
                "status_item": item_status,
                "mensagens": item_msgs
            })
            
            if item_status not in ["OK", "CORRIGIDO_AUTO"]:
                erros_pedido.append(f"Item {item.get('descricao')} -> {item_status}")

        # 3. Definição Status Geral do Pedido
        status_pedido = "VALIDO"
        if erros_pedido:
            # Se tem erro de produto não encontrado ou cliente, é falha de cadastro
            status_pedido = "REVISAO_CADASTRO" if any(x in str(erros_pedido) for x in ["NAO_ENCONTRADO", "Cliente não"]) else "ATENCAO"
        
        # Verifica total geral
        total_pdf = float(pedido.get('total_pedido_validacao', 0))
        if abs(total_pdf - total_calculado_sistema) > 0.50: # 50 centavos de tolerancia geral
            status_pedido = "DIVERGENCIA_TOTAL"
            erros_pedido.append(f"Total do pedido diverge: PDF {total_pdf} vs Soma Itens {total_calculado_sistema}")

        return {
            "numero_pedido": pedido.get("numero_pedido"),
            "status_pedido": status_pedido,
            "erros_globais": erros_pedido,
            "dados_cliente": info_cliente,
            "itens": itens_validados,
            "totais": {
                "pdf": total_pdf,
                "calculado": round(total_calculado_sistema, 2)
            }
        }
