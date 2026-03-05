# backend/scheduler.py
import time
import logging
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from winthor_client import WinthorClient

logger = logging.getLogger("Scheduler")

async def task_sincronizacao_madrugada():
    """
    Item 6 e 7: Verifica a cada 1 hora se estamos na madrugada 
    e se a sincronização já foi feita hoje.
    """
    while True:
        now = datetime.now()
        
        # Define a janela de execução (ex: entre 01:00 e 04:00 da manhã)
        if 1 <= now.hour <= 4:
            db = SessionLocal()
            try:
                # Verifica se já houve uma sincronia de SUCESSO hoje
                hoje = now.date()
                ja_fez = db.query(models.SyncLog).filter(
                    models.SyncLog.status == 'SUCESSO',
                    models.SyncLog.data_inicio >= hoje
                ).first()

                if not ja_fez:
                    logger.info("Iniciando sincronização automática de madrugada...")
                    # Executa a sincronia
                    client = WinthorClient(db)
                    
                    # Log inicial para Clientes
                    log_cli = models.SyncLog(tabela='clientes', status='PROCESSANDO')
                    db.add(log_cli)
                    db.commit()
                    
                    res_cli = client.sync_clientes()
                    
                    log_cli.status = 'SUCESSO'
                    log_cli.total_registros = res_cli.get('total_processado', 0)
                    log_cli.data_fim = datetime.utcnow()
                    
                    # Log inicial para Produtos
                    log_prod = models.SyncLog(tabela='produtos', status='PROCESSANDO')
                    db.add(log_prod)
                    db.commit()
                    
                    res_prod = client.sync_produtos()
                    
                    log_prod.status = 'SUCESSO'
                    log_prod.total_registros = res_prod.get('total_processado', 0)
                    log_prod.data_fim = datetime.utcnow()
                    
                    db.commit()
                    logger.info("Sincronização de madrugada concluída.")
                else:
                    logger.info("Sincronização diária já realizada anteriormente.")
            
            except Exception as e:
                logger.error(f"Erro no fallback da madrugada: {e}")
            finally:
                db.close()
        
        # Espera 1 hora antes de verificar o relógio novamente
        await asyncio.sleep(3600)