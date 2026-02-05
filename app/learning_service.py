from sqlalchemy.orm import Session
from models import ProdutoAlias, ProcessamentoPedido
import logging

logger = logging.getLogger("LearningService")

def aprender_aliases(db: Session, job_id: str, pedido_corrigido: dict):
    """
    Compara o JSON original (gerado pela IA) com o JSON corrigido pelo usuário.
    Se o usuário vinculou manualmente um produto, cria um Alias.
    """
    # 1. Buscar o processamento original
    job = db.query(ProcessamentoPedido).filter(ProcessamentoPedido.id == job_id).first()
    if not job or not job.resultado_json:
        return

    # A estrutura do job.resultado_json['pedidos'] é uma lista.
    # Vamos assumir que estamos processando o primeiro pedido da lista ou casar por numero_pedido
    # Para simplificar, vamos iterar sobre os itens corrigidos.
    
    id_cliente = pedido_corrigido.get("dados_cliente", {}).get("id_winthor")
    if not id_cliente:
        return

    novos_aliases = 0

    for item in pedido_corrigido.get("itens", []):
        # O campo chave que vem do PDF é o 'codigo_referencia' ou a 'descricao' ou 'ean' que falhou
        # Vamos usar 'codigo_referencia' como chave principal de alias, se existir
        
        codigo_pdf = item.get("codigo_referencia")
        id_produto_final = item.get("id_produto_winthor")
        
        # Só aprendemos se tivermos o Código do PDF e o ID final
        if codigo_pdf and id_produto_final:
            
            # Verifica se já existe esse alias para evitar duplicidade
            existe = db.query(ProdutoAlias).filter(
                ProdutoAlias.id_cliente == id_cliente,
                ProdutoAlias.codigo_cliente == codigo_pdf
            ).first()

            if not existe:
                # CRIA O ALIAS
                novo_alias = ProdutoAlias(
                    id_cliente=id_cliente,
                    id_produto=id_produto_final,
                    codigo_cliente=codigo_pdf,
                    tipo="CODIGO_INTERNO" # Assumimos que o codigo_ref do PDF é interno deles
                )
                db.add(novo_alias)
                novos_aliases += 1
                logger.info(f"Aprendizado: Cliente {id_cliente} Cod '{codigo_pdf}' -> Prod {id_produto_final}")

    if novos_aliases > 0:
        db.commit()
        return f"{novos_aliases} novos vínculos aprendidos."
    return "Nenhum vínculo novo necessário."