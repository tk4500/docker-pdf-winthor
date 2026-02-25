from typing import List
import logging
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import cast, String, or_
from datetime import datetime, timedelta
from fastapi import Form 
# Imports Locais
from validator_service import OrderValidator
import hashlib
import models
import schemas
from database import engine, get_db
from security_service import PermissionChecker
from auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user, 
    get_current_admin, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Serviços e Workers
from winthor_client import WinthorClient
from pdf_processor import PDFProcessor
from llm_service import LLMService
from parsers.registry import ParserFactory
from learning_service import aprender_aliases
from background_jobs import processar_arquivo_background, job_enriquecer_produtos, MAX_PAGES_FOR_AI

# Inicialização
models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Winthor PDF Parser API")
logger = logging.getLogger("API")
logging.basicConfig(level=logging.INFO)
# ==============================================================================
# 1. AUTENTICAÇÃO E SETUP
# ==============================================================================

@app.get("/", tags=["Health"])
def root():
    return {"message": "API Winthor PDF Parser está rodando."}

@app.post("/token", response_model=schemas.Token, tags=["Auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    local_auth_success = False
    if user and verify_password(form_data.password, user.hashed_password):
        local_auth_success = True
    if not local_auth_success:
        logger.info(f"Autenticação local falhou para {form_data.username}, tentando Winthor...")
        if not user or user.winthor_password is not None:
            winthor_hash = hashlib.md5(form_data.password.encode('utf-8').upper()).hexdigest().upper()
            logger.info(f"Hash MD5 do Winthor para comparação: {winthor_hash}")
            winthor_client = WinthorClient(db, current_user=user if user else None)
            is_winthor_valid = winthor_client.authenticate_user(form_data.username, winthor_hash)
            
            if is_winthor_valid:
                logger.info(f"Autenticação no Winthor bem-sucedida para {form_data.username}")
                if not user:
                    logger.info(f"Criando novo usuário local para {form_data.username} com senha do Winthor.")
                    # Cria um novo usuário importado do Winthor
                    # Opcional: Você pode buscar uma Role padrão aqui, ex: db.query(models.Role).filter_by(name="Vendedor").first()
                    user = models.User(
                        username=form_data.username,
                        hashed_password=get_password_hash(form_data.password), # Salva no padrão base bcrypt
                        winthor_password=winthor_hash,
                        role_id = 4,
                        email=f"{form_data.username}@winthor.local" # Placeholder
                    )
                    db.add(user)
                else:
                    logger.info(f"Atualizando senha do usuário existente {form_data.username} com hash do Winthor.")
                    # Atualiza o usuário existente (sincroniza as senhas)
                    user.hashed_password = get_password_hash(form_data.password)
                    user.winthor_password = winthor_hash
                
                db.commit()
                db.refresh(user)
                local_auth_success = True
            else:
                logger.warning(f"Autenticação no Winthor falhou para {form_data.username}")
    if not local_auth_success:
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # --- CORREÇÃO AQUI ---
    # Verifica se existe role e pega o NOME (string), senão usa string vazia ou default
    role_name = user.role.name if user.role else "SemPermissao"
    
    access_token = create_access_token(
        data={"sub": user.username, "role": role_name}, # Passamos a String, não o Objeto
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "username": user.username,
        "role": role_name # Aqui também retorna a string
    }

# ==============================================================================
# 2. ADMINISTRAÇÃO (USUÁRIOS, ROLES, CONFIGS)
# ==============================================================================

@app.post("/admin/users", tags=["Admin"], dependencies=[Depends(get_current_admin)])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Usuário já existe")
    
    hashed = get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed, email=user.email)
    db.add(new_user)
    db.commit()
    return {"status": "Usuário criado", "username": new_user.username}

@app.put("/admin/users/{username}/role", tags=["Admin"], dependencies=[Depends(PermissionChecker("users:manage"))])
def assign_role_to_user(username: str, role_name: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not user or not role:
        raise HTTPException(status_code=404, detail="Usuário ou Role não encontrado")
    
    user.role = role
    db.commit()
    return {"msg": "Role atualizada"}

@app.post("/admin/roles", tags=["Admin"], dependencies=[Depends(PermissionChecker("users:manage"))])
def create_role(role_data: schemas.RoleCreate, db: Session = Depends(get_db)):
    if db.query(models.Role).filter(models.Role.name == role_data.name).first():
        raise HTTPException(status_code=400, detail="Role já existe")
    
    perms = db.query(models.Permission).filter(models.Permission.slug.in_(role_data.permissions_slugs)).all()
    new_role = models.Role(name=role_data.name, permissions=perms)
    db.add(new_role)
    db.commit()
    return {"msg": f"Role {new_role.name} criada."}

@app.get("/admin/permissions", tags=["Admin"], dependencies=[Depends(PermissionChecker("users:manage"))])
def list_permissions(db: Session = Depends(get_db)):
    return db.query(models.Permission).all()

@app.post("/admin/configs", tags=["Admin"], dependencies=[Depends(PermissionChecker("config:edit"))])
def set_config(config: schemas.ConfigItem, db: Session = Depends(get_db)):
    conf = db.query(models.Configuracao).filter(models.Configuracao.chave == config.chave).first()
    if not conf:
        conf = models.Configuracao(chave=config.chave, valor=config.valor, descricao=config.descricao)
        db.add(conf)
    else:
        conf.valor = config.valor
        if config.descricao: conf.descricao = config.descricao
    db.commit()
    return {"msg": "Configuração salva"}

@app.get("/admin/configs", tags=["Admin"], dependencies=[Depends(PermissionChecker("config:view"))])
def list_configs(db: Session = Depends(get_db)):
    return db.query(models.Configuracao).all()

# ==============================================================================
# 3. BUSCAS E DADOS MESTRES
# ==============================================================================

@app.get("/clientes/busca", tags=["Busca"], dependencies=[Depends(get_current_user)]) 
def buscar_cliente(termo: str, db: Session = Depends(get_db)):
    termo_busca = f"%{termo}%"
    return db.query(models.Cliente).filter(
        (models.Cliente.razao_social.ilike(termo_busca)) | 
        (cast(models.Cliente.cnpj_cpf, String).ilike(termo_busca))
    ).limit(20).all()

@app.get("/clientes/{client_id}", tags=["Busca"], dependencies=[Depends(get_current_user)]) 
def buscar_cliente_id(client_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    winthor_client = WinthorClient(db, current_user=current_user)
    return winthor_client.get_cliente(client_id)

@app.post("/sync/regionId", tags=["Sync"], dependencies=[Depends(PermissionChecker("sync:winthor"))])
def sincronizar_region_id(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    clientes = db.query(models.Cliente).filter(models.Cliente.regionId == None).all()
    winthor_client = WinthorClient(db, current_user=current_user)
    for cliente in clientes:
        c = winthor_client.get_cliente(cliente.id)
        region_id = c.get("regionId") if c else None
        if region_id:
            cliente.regionId = region_id
    db.commit()
    return {"msg": f"Sincronização de regionId concluída para {len(clientes)} clientes."}

@app.put("/clientes/salvar", tags=["Salvar"], dependencies=[Depends(PermissionChecker("client:save"))]) 
def salvar_cliente(cliente: schemas.ClienteUpdate, db: Session = Depends(get_db)):
    
    cliente_banco = db.query(models.Cliente).filter(models.Cliente.id == cliente.id).first()
    if not cliente_banco: raise HTTPException(status_code=404, detail="Cliente não encontrado")

    if cliente.chargingId:
        cliente_banco.chargingId = cliente.chargingId
    if cliente.cnpj_cpf:
        cliente_banco.cnpj_cpf = cliente.cnpj_cpf
    if cliente.plano_pag_padrao:
        cliente_banco.plano_pag_padrao = cliente.plano_pag_padrao
    if cliente.razao_social:
        cliente_banco.razao_social = cliente.razao_social
    if cliente.regionId:
        cliente_banco.regionId = cliente.regionId
    if cliente.sellerId:
        cliente_banco.sellerId = cliente.sellerId
    db.commit()
    cliente_banco = db.query(models.Cliente).filter(models.Cliente.id == cliente.id).first()

    return cliente_banco

@app.get("/produtos/busca", tags=["Busca"], dependencies=[Depends(get_current_user)])
def buscar_produto(termo: str, db: Session = Depends(get_db)):
    termo_busca = f"%{termo}%"
    filtros = [models.Produto.nome.ilike(termo_busca), models.Produto.ean.ilike(termo_busca)]
    if termo.isdigit():
        filtros.append(models.Produto.id == int(termo))
    
    return db.query(models.Produto).filter(or_(*filtros)).limit(20).all()

# ==============================================================================
# 4. PROCESSAMENTO DE PEDIDOS (FLUXO PRINCIPAL)
# ==============================================================================

@app.post("/pedidos/manual", tags=["Pedidos"], dependencies=[Depends(PermissionChecker("order:create"))])
def criar_pedido_manual(
    dados: schemas.PedidoCreateManual, 
    db: Session = Depends(get_db), 
    user: models.User = Depends(get_current_user)
):
    # Cria estrutura compatível com o validador
    novo_job = models.ProcessamentoPedido(
        user_id=user.id,
        nome_arquivo=f"Manual - Cli {dados.cliente_id}",
        origem_entrada="MANUAL",
        auto_process=dados.options.auto_process,
        is_bonificacao=dados.options.is_bonificacao,
        status_global="PENDENTE_VALIDACAO"
    )
    db.add(novo_job)
    db.commit()
    
    # Monta JSON simulado como se viesse da IA
    produtos_mock = []
    for item in dados.itens:
        produtos_mock.append({
            "id_produto_winthor": item['id_produto'], # Já vem com ID
            "quantidade_total": item['quantidade'],
            "valor_unitario": item['valor'],
            "valor_total": float(item['valor']) * float(item['quantidade'])
        })
        
    json_manual = {
        "dados_cliente": {"id_winthor": dados.cliente_id}, # Validador vai enriquecer
        "produtos": produtos_mock,
        "total_pedido_validacao": sum(item['valor_total'] for item in produtos_mock)
    }
    
    # Chama validação (síncrona para manual)
    from background_jobs import validar_job_existente
    validar_job_existente(novo_job, json_manual, db, user)
    
    return {"job_id": novo_job.id, "status": novo_job.status_global}


@app.post("/pedidos/upload-async", tags=["Pedidos"], dependencies=[Depends(PermissionChecker("order:create"))])
async def upload_pedido_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_process: bool = Form(False),
    is_bonificacao: bool = Form(False),
    force_ai: bool = Form(False),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    contents = await file.read()
    
    novo_job = models.ProcessamentoPedido(
        user_id=user.id,
        nome_arquivo=file.filename,
        status_global="PENDENTE",
        auto_process=auto_process,
        is_bonificacao=is_bonificacao,
        force_ai=force_ai
    )
    db.add(novo_job)
    db.commit()
    
    background_tasks.add_task(processar_arquivo_background, novo_job.id, contents, file.filename, db, user)
    return {"job_id": novo_job.id, "status": "Processamento iniciado"}

@app.post("/pedidos/upload-json-bulk", tags=["Pedidos"], dependencies=[Depends(PermissionChecker("order:create"))])
async def upload_json_bulk(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    jobs_ids = []
    for file in files:
        content = await file.read()
        import json
        try:
            data = json.loads(content)
            # Lógica similar ao manual... cria job e valida
            # ...
            jobs_ids.append("id_gerado")
        except:
            continue
    return {"jobs": jobs_ids}

@app.get("/pedidos/status/{job_id}", tags=["Processamento"], dependencies=[Depends(PermissionChecker("order:validate"))])
def verificar_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(models.ProcessamentoPedido).filter(models.ProcessamentoPedido.id == job_id).first()
    if not job: raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return {
        "job_id": job.id,
        "status": job.status_global,
        "criado_em": job.data_criacao,
        "finalizado_em": job.data_finalizacao,
        "erro": job.mensagem_erro,
        "resultado": job.resultado_json if job.resultado_json else None,
    }

@app.delete("/pedidos/{job_id}", tags=["Pedidos"], dependencies=[Depends(PermissionChecker("order:cancel"))])
def cancelar_pedido(job_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    job = db.query(models.ProcessamentoPedido).filter(models.ProcessamentoPedido.id == job_id).first()
    if not job: raise HTTPException(404, "Pedido não encontrado")
    
    # Se já foi enviado pro Winthor, tenta cancelar lá
    if job.status_global == "ENVIADO_WINTHOR" and job.resultado_json and job.resultado_json.get("retorno_winthor"):
        client = WinthorClient(db, current_user=user)
        try:
            client.cancelar_pedido_winthor(job.resultado_json["retorno_winthor"].get("orderId")) # Precisa implementar no Client
            job.status_global = "CANCELADO_WINTHOR"
        except Exception as e:
            raise HTTPException(500, f"Erro ao cancelar no Winthor: {str(e)}")
    else:
        # Soft delete ou status cancelado
        job.status_global = "CANCELADO"
    
    db.commit()
    return {"msg": "Pedido cancelado"}


@app.post("/pedidos/finalizar/{job_id}", tags=["Steps"], dependencies=[Depends(PermissionChecker("order:approve"))])
def finalizar_pedido(
    job_id: str, 
    payload: schemas.PedidoFinalInput, 
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user) # Verifica permissão
):
    job = db.query(models.ProcessamentoPedido).filter(models.ProcessamentoPedido.id == job_id).first()
    if not job: raise HTTPException(status_code=404, detail="Job não encontrado")
    validator = OrderValidator(db)
    retorno = validator._validar_pedido_individual(payload.pedido) # Revalida para garantir que o que está sendo enviado é válido
    if retorno['status_pedido'] != "VALIDO":
        job.status_global = "REVALIDACAO_FALHOU"
        job.mensagem_erro = f"Revalidação falhou: Status {retorno['status_pedido']}"
        job.pedido = retorno
        db.commit()
        raise HTTPException(status_code=400, detail=f"Pedido não passou na revalidação final: {retorno['status_pedido']}")
    try:
        msg_aprendizado = aprender_aliases(db, job_id, payload.pedido)
        client = WinthorClient(db, current_user=user)
        resposta_winthor = client.enviar_pedido(payload.pedido)

        job.status_global = "ENVIADO_WINTHOR"
        job.mensagem_erro = None
        job.resultado_json = {
            "pedido_enviado": payload.pedido,
            "retorno_winthor": resposta_winthor,
            "log_aprendizado": msg_aprendizado,
        }
        job.data_finalizacao = datetime.utcnow()
        db.commit()

        return {"status": "sucesso", "winthor_order_id": resposta_winthor.get("orderId"), "aprendizado": msg_aprendizado}
    except Exception as e:
        job.status_global = "ERRO_ENVIO"
        job.mensagem_erro = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Erro ao enviar: {str(e)}")


@app.post("/pedidos/{job_id}/revalidar", tags=["Steps"], dependencies=[Depends(PermissionChecker("order:validate"))])
def revalidar_pedido(job_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    job = db.query(models.ProcessamentoPedido).filter(models.ProcessamentoPedido.id == job_id).first()
    
    if not job: raise HTTPException(status_code=404, detail="Job não encontrado")
    if not job.resultado_json:
        raise HTTPException(status_code=400, detail="Job não possui JSON para revalidar")
    from background_jobs import validar_job_existente
    validar_job_existente(job, job.resultado_json, db, user)
    
    return {"msg": "Revalidado"}

@app.post("/pedidos/list-advanced", tags=["Pedidos"], dependencies=[Depends(get_current_user)])
def list_jobs_filtered(
    filtro: schemas.JobListFilter, 
    skip: int = 0, limit: int = 50, 
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    query = db.query(models.ProcessamentoPedido)
    
    # Req 3: Segurança de Usuário
    if user.role.name != "Administrador" and user.role.name != "Auditor":
        query = query.filter(models.ProcessamentoPedido.user_id == user.id)
    
    if filtro.status: query = query.filter(models.ProcessamentoPedido.status_global == filtro.status)
    
    # Filtra apenas pais ou filhos independentes (para não poluir a lista com o pai que splitou)
    # Opcional: mostrar tudo
    
    total = query.count()
    jobs = query.order_by(models.ProcessamentoPedido.data_criacao.desc()).offset(skip).limit(limit).all()
    
    return {"total": total, "items": jobs}

@app.get("/pedidos/historico", tags=["Processamento"], dependencies=[Depends(PermissionChecker("order:read_all"))])
def listar_historico(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(models.ProcessamentoPedido).order_by(models.ProcessamentoPedido.data_criacao.desc()).offset(skip).limit(limit).all()

# ==============================================================================
# 5. SINCRONIZAÇÃO WINTHOR
# ==============================================================================

@app.post("/sync/clientes", tags=["Sync"], dependencies=[Depends(PermissionChecker("sync:winthor"))])
def sincronizar_clientes(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return WinthorClient(db, current_user=current_user).sync_clientes()

@app.post("/sync/produtos", tags=["Sync"], dependencies=[Depends(PermissionChecker("sync:winthor"))])
def sincronizar_produtos(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return WinthorClient(db, current_user=current_user).sync_produtos()

@app.post("/sync/importar-pedidos-antigos", tags=["Sync"], dependencies=[Depends(PermissionChecker("sync:winthor"))])
def importar_pedidos_manuais(payload: schemas.ListaPedidosSync, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return WinthorClient(db, current_user=current_user).importar_pedidos_por_ids(payload.ids)

@app.post("/sync/enriquecer-produtos", tags=["Sync"], dependencies=[Depends(PermissionChecker("sync:winthor"))])
def enriquecer_produtos(background_tasks: BackgroundTasks, apenas_incompletos: bool = False, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    background_tasks.add_task(job_enriquecer_produtos, db, apenas_incompletos, user)
    return {"mensagem": "Processo de atualização detalhada iniciado em background."}

# ==============================================================================
# 6. DEBUG E UTILITÁRIOS (Acesso Restrito)
# ==============================================================================

@app.post("/debug/pdf-to-text", tags=["Debug"], dependencies=[Depends(get_current_admin)])
async def debug_pdf_extraction(file: UploadFile = File(...)):
    contents = await file.read()
    processor = PDFProcessor()
    texto_extraido = processor.extract_text_optimized(contents)
    return {"status": "sucesso", "preview": texto_extraido}

@app.post("/debug/pdf-to-json-ai", tags=["Debug"], dependencies=[Depends(get_current_admin)])
async def debug_pdf_to_json(file: UploadFile = File(...)):
    contents = await file.read()
    processor = PDFProcessor()
    texto_extraido = processor.extract_text_optimized(contents)
    llm = LLMService()
    return {"json_gerado": llm.parse_pedido_text(texto_extraido["text"]), "modelo": llm.last_used_model}

@app.post("/pedidos/processar", tags=["Debug"], dependencies=[Depends(get_current_admin)])
async def processar_pedido_sincrono(file: UploadFile = File(...)):
    """Rota síncrona antiga para testes rápidos, requer Admin"""
    contents = await file.read()
    processor = PDFProcessor()
    extraction = processor.extract_text_optimized(contents)
    texto = extraction["text"]
    
    parser = ParserFactory.get_parser_for_text(texto)
    if parser: return parser.parse(texto)
    
    if extraction["pages"] > MAX_PAGES_FOR_AI:
        raise HTTPException(status_code=400, detail="PDF muito grande")
        
    llm = LLMService()
    return {"dados": llm.parse_pedido_text(texto), "metodo": f"IA_{llm.last_used_model}"}
