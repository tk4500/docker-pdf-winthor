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
        logger.info(f"Verificando janela de sincronização... Hora atual: {now}")
        

        db = SessionLocal()
        try:
                # Verifica se já houve uma sincronia de SUCESSO hoje
            hoje = now.date()
            client = WinthorClient(db)
            is_sync_clientes = db.query(models.SyncLog).filter(
                    models.SyncLog.tabela == 'clientes',
                    models.SyncLog.status == 'SUCESSO',
                    models.SyncLog.data_inicio >= hoje
            ).first()
            
            if not is_sync_clientes:
                logger.info("Sincronização de clientes ainda não realizada hoje.")
                client.sync_clientes()
            
            is_sync_produtos = db.query(models.SyncLog).filter(
                    models.SyncLog.tabela == 'produtos',
                    models.SyncLog.status == 'SUCESSO',
                    models.SyncLog.data_inicio >= hoje
            ).first()
            
            if not is_sync_produtos:
                logger.info("Sincronização de produtos ainda não realizada hoje.")
                client.sync_produtos()

        except Exception as e:
                logger.error(f"Erro no fallback da madrugada: {e}")
        finally:
                db.close()
        
        # Espera 1 hora antes de verificar o relógio novamente
        await asyncio.sleep(3600)