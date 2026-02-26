import logging
import traceback
from datetime import datetime
import models
from sqlalchemy.orm import Session
from models import ProcessamentoPedido, ProcessamentoPedido as Job # Alias
from pdf_processor import PDFProcessor
from parsers.registry import ParserFactory
from llm_service import LLMService
from validator_service import OrderValidator
from winthor_client import WinthorClient
import uuid


logger = logging.getLogger("BackgroundJobs")

MAX_PAGES_FOR_AI = 10

# --- Funções Auxiliares Internas ---

def avanca_fluxo_automatico(job: Job, db: Session, user: models.User = None):
    """
    Req 5: Verifica se pode avançar para o próximo passo automaticamente
    """
    if not job.auto_process:
        logger.info(f"Job {job.id} não é de auto-processamento. Aguardando ação manual.")
        return

    # Se validou com sucesso, tenta enviar
    if job.status_global == "VALIDADO":
        try:
            finalizar_envio_winthor(job.id, db, None, user)
        except:
            pass # Erro já tratado dentro da função

def validar_job_existente(job: Job, dados_brutos_pedido: dict, db: Session, user: models.User = None):
    """Req 4: Endpoint isolado de validação chama isso"""
    try:
        job.status_global = "VALIDANDO_DADOS"
        db.commit()

        validator = OrderValidator(db)
        # Ajuste: Validator espera estrutura {dados: {pedidos: []}} ou dict direto
        wrapper = {"dados": {"pedidos": [dados_brutos_pedido]}}
        resultado_final = validator.validar_lote_pedidos(wrapper)
        
        # Verifica se o pedido está 100% (Status 'VALIDO' vem do Validator)
        # O validator retorna lista, pegamos o primeiro pois validar_job_existente é 1-1
        pedido_validado = resultado_final['pedidos'][0]
        status_interno = pedido_validado.get('status_pedido')
        
        job.resultado_json = resultado_final
        job.status_global = "AGUARDANDO_APROVACAO"
        
        if status_interno == "VALIDO":
            job.status_global = "VALIDADO" # Pronto para envio
            
        job.data_finalizacao = datetime.utcnow()
        db.commit()
        
        # Trigger Auto Process
        avanca_fluxo_automatico(job, db, user)

    except Exception as e:
        logger.error(f"Erro na validação do job {job.id}: {e}")
        job.status_global = "ERRO_VALIDACAO"
        job.mensagem_erro = str(e)
        db.commit()

def finalizar_envio_winthor(job_id: str, db: Session, pedido_manual: dict = None, user: models.User = None):
    """Req 4: Endpoint isolado de envio chama isso"""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    try:
        job.status_global = "ENVIANDO"
        db.commit()
        
        # Pega o payload. Se veio manual (finalizar_pedido endpoint) usa ele, senão pega do banco
        payload_final = pedido_manual if pedido_manual else job.resultado_json['pedidos'][0]
        client = WinthorClient(db, user)
        # Req 8: Passa flag de bonificação
        client.is_bonificacao = job.is_bonificacao 
        try:
            resposta = client.enviar_pedido(payload_final)
        except Exception as e:
            logger.error(f"Erro ao enviar pedido para Winthor: {e}")
            raise e
        job.status_global = "ENVIADO_WINTHOR"
        job.winthor_order_id = str(resposta.get("orderId"))
        job.mensagem_erro = None
        
        # Atualiza JSON com retorno mantendo dados antigos
        current_json = dict(job.resultado_json) if job.resultado_json else {}
        current_json['retorno_winthor'] = resposta
        job.resultado_json = current_json
        job.data_finalizacao = datetime.utcnow()
        
        db.commit()
        return resposta
        
    except Exception as e:
        logger.error(f"Erro ao enviar pedido para Winthor: {e}")
        job.status_global = "ERRO_ENVIO"
        job.mensagem_erro = str(e)
        db.commit()
        raise e

# --- Workers Exportados (Chamados pelo Main) ---

def processar_arquivo_background(job_id: str, file_content: bytes, filename: str, db: Session, user: models.User = None):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job: return

    try:
        # 1. Extração
        job.status_global = "EXTRAINDO_TEXTO"
        db.commit()

        processor = PDFProcessor()
        extraction = processor.extract_text_optimized(file_content)
        texto = extraction["text"]

        # 2. Parse (Template ou IA)
        job.status_global = "INTERPRETANDO_DADOS"
        db.commit()

        dados_brutos = {}
        
        # Req 9: Force AI
        parser = None
        if not job.force_ai:
            parser = ParserFactory.get_parser_for_text(texto)

        if parser:
            dados_brutos = parser.parse(texto)
            if isinstance(dados_brutos, dict): dados_brutos["metodo_processamento"] = "TEMPLATE"
        else:
            if extraction["pages"] > MAX_PAGES_FOR_AI:
                raise Exception(f"PDF muito grande. Limite: {MAX_PAGES_FOR_AI}.")
            
            llm = LLMService()
            dados_brutos = {
                "metodo_processamento": f"IA_{llm.last_used_model}",
                "dados": llm.parse_pedido_text(texto),
            }

        # --- Lógica de Split (Req 10) ---
        # Se a IA retornou múltiplos pedidos, criamos sub-jobs
        # Verifica se 'dados' existe e tem 'pedidos'
        lista_pedidos = dados_brutos.get("dados", {}).get("pedidos", [])
        if not lista_pedidos:
             # Tenta pegar da raiz caso parser template retorne direto
             lista_pedidos = dados_brutos.get("pedidos", [])

        if len(lista_pedidos) > 1:
            job.status_global = "MULTIPLOS_PEDIDOS_DETECTADOS"
            job.resultado_json = {"info": "Este arquivo gerou sub-pedidos."}
            
            for p_raw in lista_pedidos:
                sub_job = Job(
                    id=str(uuid.uuid4()),
                    job_pai_id=job.id, # Link com o pai
                    user_id=job.user_id,
                    nome_arquivo=f"{job.nome_arquivo} (Parte {p_raw.get('numero_pedido', 'Unknown')})",
                    origem_entrada=job.origem_entrada,
                    is_bonificacao=job.is_bonificacao,
                    auto_process=job.auto_process,
                    status_global="PENDENTE_VALIDACAO"
                )
                db.add(sub_job)
                
                # Já executamos a validação para o sub-job
                validar_job_existente(sub_job, p_raw, db, user)
                
            db.commit()
            return # Pai finalizado como container

        # Caso seja 1 pedido só, validamos o próprio job
        pedido_unico = lista_pedidos[0] if lista_pedidos else dados_brutos 
        validar_job_existente(job, pedido_unico, db, user)

    except Exception as e:
        traceback.print_exc()
        logger.error(f"Erro no processamento do arquivo para job {job.id}: {e}")
        job.status_global = "ERRO"
        job.mensagem_erro = str(e)
        job.data_finalizacao = datetime.utcnow()
        db.commit()

def job_enriquecer_produtos(db: Session, apenas_incompletos: bool, user: models.User= None):
    """Função worker para atualizar cadastro de produtos"""
    client = WinthorClient(db)
    try:
        client.enriquecer_produtos_locais(apenas_incompletos=apenas_incompletos)
        logger.info("Job de enriquecimento finalizado com sucesso.")
    except Exception as e:
        logger.error(f"Erro no job de enriquecimento: {e}")