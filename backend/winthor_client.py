import json
import math
from urllib import response
import requests
import logging
from sqlalchemy.orm import Session
from models import Configuracao, Cliente, Produto, ProdutoConversao
import os
from datetime import datetime

logger = logging.getLogger("WinthorClient")
logging.basicConfig(level=logging.INFO)


class WinthorClient:
    def __init__(self, db: Session, current_user=None):
        self.db = db
        self.current_user = current_user
        self.session = requests.Session()
        self.base_url = self._get_config(
            "WINTHOR_BASE_URL", os.getenv("WINTHOR_BASE_URL")
        )
        self.token = None
        # Garante que branch_id seja int ou string conforme api pede, aqui convertemos pra int por segurança
        try:
            self.branch_id = int(
                self._get_config(
                    "WINTHOR_FILIAL_ID", os.getenv("WINTHOR_FILIAL_ID", "1")
                )
            )
        except:
            self.branch_id = 1
        try:
            self.authenticate()
        except Exception as e:
            logger.error(f"Erro ao autenticar no Winthor durante inicialização: {e}")

    def _get_config(self, key, default=None):
        conf = self.db.query(Configuracao).filter(Configuracao.chave == key).first()
        if conf:
            return conf.valor
        return default
    
    def authenticate_user(self, login: str, senha_hash: str) -> bool:
        """
        Tenta autenticar um usuário específico no Winthor para validar suas credenciais.
        Retorna True se as credenciais estiverem corretas (HTTP 200).
        """
        url = f"{self.base_url}/winthor/autenticacao/v1/login"
        try:
            # Tenta o login. Não salvamos o token aqui para não sobrescrever o token 
            # de integração global que o sistema usa nas outras rotas.
            response = requests.post(url, json={"login": login, "senha": senha_hash})
            
            # Se retornar 200 OK, a senha está correta
            if response.status_code == 200:
                return True
            return False
        except Exception as e:
            logger.error(f"Falha na tentativa de login via Winthor para {login}: {e}")
            return False

    def authenticate(self):
        login = self._get_config("WINTHOR_LOGIN", os.getenv("WINTHOR_LOGIN"))
        senha = self._get_config("WINTHOR_PASSWORD", os.getenv("WINTHOR_PASSWORD"))
        if self.current_user and self.current_user.winthor_password:
            logger.info(f"Autenticando Winthor para usuário {self.current_user.username}...")
            login = self.current_user.username
            senha = self.current_user.winthor_password
        else:
            logger.info("Autenticando Winthor com credenciais globais...")
        url = f"{self.base_url}/winthor/autenticacao/v1/login"

        try:
            response = self.session.post(url, json={"login": login, "senha": senha})
            response.raise_for_status()
            data = response.json()
            self.token = data.get("accessToken")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            logger.info("Autenticado no Winthor.")
        except Exception as e:
            logger.error(f"Erro Auth Winthor: {e}")
            raise

    def get_ean_from_id(self, produto_id: int):
        produto = self.db.query(Produto).filter(Produto.id == produto_id).first()
        if produto:
            return produto.ean
        else:
            url = f"{self.base_url}/api/purchases/v1/products/{produto_id}"
            params = {
                "branchId": self.branch_id,
            }
            try:
                response = self.session.get(url, params=params)
                if response.status_code == 401:
                    self.authenticate()
                    response = self.session.get(url, params=params)

                response.raise_for_status()
                data = response.json()

                item_data = data
                if isinstance(data, list):
                    if data:
                        item_data = data[0]
                    else:
                        return None
                elif isinstance(data, dict) and "items" in data:
                    if data["items"]:
                        item_data = data["items"][0]
                    else:
                        return None

                novo_ean = item_data.get("barCode")
                return str(novo_ean) if novo_ean else None
            except Exception as e:
                logger.error(f"Erro ao buscar EAN do produto {produto_id}: {e}")
                return None

    def _set_customer_to_chargingId(self):
        logger.info("Buscando clientes para mapear chargingId...")
        if not self.token:
            self.authenticate()
        url = f"{self.base_url}/api/wholesale/v1/orders/list"
        params = {
            "branchId": self.branch_id,
            "page": 1,
            "pageSize": 100,
            "daysOfSearch": 365,
            "order": "lastChange",
            "orderStatus": "F",
            "saleOrigin": "T",
            "viewDocument": False,
        }
        hasNext = True
        non_charging_id_customers = self.db.query(Cliente).filter(Cliente.chargingId == None).all()
        while hasNext:
            try:
                response = self.session.get(url, params=params)
                if response.status_code == 401:
                    self.authenticate()
                    response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                logger.info(
                    f"Página {params['page']} de pedidos retornada para mapear chargingId."
                )
                lista = data if isinstance(data, list) else data.get("items", [])

                for ped in lista:
                    c_id = ped.get("customer", {}).get("id")
                    if c_id and any(c.id == c_id for c in non_charging_id_customers):
                        chargingId = ped.get("chargingId")
                        if chargingId and chargingId != "BNF":
                            index = next(i for i, c in enumerate(non_charging_id_customers) if c.id == c_id)
                            cliente_db = non_charging_id_customers.pop(index)
                            if cliente_db:
                                cliente_db.chargingId = chargingId
                                self.db.commit()
                                logger.info(
                                    f"Cliente {c_id} atualizado com chargingId {chargingId}."
                                )
                                
                params["page"] += 1
                hasNext = data.get("hasNext") or (
                    len(lista) > 0
                )
            except Exception as e:
                logger.error(f"Erro ao mapear chargingId: {e}")
                break

    def _get_charging_id(self, cliente_id: int):
        logger.info(f"Buscando chargingId para cliente {cliente_id}...")
        if not self.token:
            self.authenticate()

        url = f"{self.base_url}/api/wholesale/v1/orders/list"
        params = {
            "branchId": self.branch_id,
            "page": 36,
            "pageSize": 100,
            "daysOfSearch": 700,
            "order": "lastChange",
            "orderStatus": "F",
            "saleOrigin": "T",
            "viewDocument": False,
        }
        hasNext = True
        while hasNext:
            try:
                response = self.session.get(url, params=params)
                if response.status_code == 401:
                    self.authenticate()
                    response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                logger.info(
                    f"Página {params['page']} de pedidos retornada para busca de chargingId."
                )
                lista = data if isinstance(data, list) else data.get("items", [])

                ped = next(
                    (
                        pedido
                        for pedido in lista
                        if pedido.get("customer", {}).get("id") == cliente_id
                    ),
                    None,
                )
                if ped:
                    chargingId = ped.get("chargingId")
                    logger.info(
                        f"chargingId encontrado para cliente {cliente_id}: {chargingId}"
                    )
                    if chargingId != "BNF":
                        return chargingId

                params["page"] += 1
                hasNext = data.get("hasNext") or (
                    len(lista) > 0
                )  # Continua se tiver next ou se ainda tiver itens (fallback)
            except Exception as e:
                logger.error(f"Erro ao buscar pedidos para cliente {cliente_id}: {e}")
        return 341  # Retorna ID de cobrança padrão se não encontrar nenhum pedido do cliente

    def get_cliente(self, cliente_id: int):
        if not self.token:
            self.authenticate()
        url = f"{self.base_url}/api/wholesale/v1/customer/"
        params = {
            "customerId": cliente_id
        }
        try:
            response = self.session.get(url, params=params)
            if response.status_code == 401:
                self.authenticate()
                response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            logger.error(f"Erro ao buscar cliente {cliente_id}: {e}")
            return str(e)

    def sync_clientes(self):
        if not self.token:
            self.authenticate()

        page = 1
        page_size = 50
        hasNext = True
        total_upserted = 0

        url = f"{self.base_url}/api/wholesale/v1/customer/list"
        self._set_customer_to_chargingId()

        while hasNext:
            params = {
                "branchId": self.branch_id,
                "page": page,
                "pageSize": page_size,
                "withDeliveryAddress": False,
            }

            try:
                response = self.session.get(url, params=params)
                if response.status_code == 401:
                    self.authenticate()
                    response = self.session.get(url, params=params)

                response.raise_for_status()
                data = response.json()

                # Adaptação para caso venha lista direta ou objeto com items
                lista = data if isinstance(data, list) else data.get("items", [])
                logger.info(
                    f"Sync Clientes - Página {page} retornou {len(lista)} itens."
                )
                if not lista:
                    hasNext = False
                    break

                for item in lista:
                    try:
                        c_id = int(item.get("id"))  # Garante ID inteiro

                        # Limpa CNPJ
                        raw_cnpj = str(item.get("personIdentificationNumber", ""))
                        cnpj_limpo = "".join(filter(str.isdigit, raw_cnpj))

                        # Verifica se existe pelo ID
                        cliente_db = (
                            self.db.query(Cliente).filter(Cliente.id == c_id).first()
                        )

                        if cliente_db:
                            # ATUALIZA (Update)
                            cliente_db.cnpj_cpf = cnpj_limpo
                            cliente_db.razao_social = item.get("name")
                            cliente_db.plano_pag_padrao = item.get("paymentPlanId")
                            cliente_db.sellerId = item.get("sellerId")
                            cliente_db.chargingId = (
                                cliente_db.chargingId
                                if cliente_db.chargingId
                                else self._get_charging_id(c_id)
                            )
                            cliente_db.regionId = item.get("regionId")
                            self.db.commit()
                        else:
                            # INSERE (Insert)
                            novo_cliente = Cliente(
                                id=c_id,
                                cnpj_cpf=cnpj_limpo,
                                razao_social=item.get("name"),
                                plano_pag_padrao=item.get("paymentPlanId"),
                                sellerId=item.get("sellerId"),
                                regionId=item.get("regionId"),
                            )
                            self.db.add(novo_cliente)
                            self.db.commit()
                        total_upserted += 1

                    except Exception as e_item:
                        logger.error(f"Erro processar item cliente: {e_item}")
                        continue

                self.db.commit()  # Comita o lote da página
                logger.info(
                    f"Página {page} processada. Total até agora: {total_upserted}"
                )

                if len(lista) < page_size:
                    hasNext = False
                else:
                    page += 1

            except Exception as e:
                logger.error(f"Erro fatal sync clientes pg {page}: {e}")
                self.db.rollback()
                break

        return {"status": "sucesso", "total_processado": total_upserted}

    def sync_produtos(self):
        if not self.token:
            self.authenticate()

        page = 1
        page_size = 50
        hasNext = True
        total_upserted = 0
        url = f"{self.base_url}/api/purchases/v1/products/"

        while hasNext:
            params = {
                "branchId": self.branch_id,
                "page": page,
                "pageSize": page_size,
                "callOrigin": "T",
            }

            try:
                response = self.session.get(url, params=params)
                if response.status_code == 401:
                    self.authenticate()
                    response = self.session.get(url, params=params)

                response.raise_for_status()
                data = response.json()
                lista = data if isinstance(data, list) else data.get("items", [])
                logger.info(
                    f"Sync Produtos - Página {page} retornou {len(lista)} itens."
                )
                if not lista:
                    hasNext = False
                    break

                for item in lista:
                    try:
                        p_id = int(item.get("id"))

                        # Tenta pegar EAN de varios lugares
                        ean = item.get("barCode")

                        produto_db = (
                            self.db.query(Produto).filter(Produto.id == p_id).first()
                        )

                        if produto_db:
                            # Update
                            if item.get("name"):
                                produto_db.nome = item.get("name")
                            else:
                                if item.get("title"):
                                    produto_db.nome = item.get("title")
                            if ean: 
                                produto_db.ean = ean
                            if item.get("unity"):
                                produto_db.unidade = item.get("unity")
                            self.db.commit()
                        else:
                            # Insert
                            novo_prod = Produto(
                                id=p_id,
                                nome=item.get("name") or item.get("title"),
                                ean=ean or "",
                                unidade=item.get("unity") or "UN",
                            )
                            self.db.add(novo_prod)

                        total_upserted += 1
                    except Exception as e_prod:
                        logger.error(f"Erro item produto: {e_prod}")
                        continue

                self.db.commit()
                logger.info(f"Prod Página {page} processada. Total: {total_upserted}")

                if len(lista) < page_size:
                    hasNext = False
                else:
                    page += 1

            except Exception as e:
                logger.error(f"Erro fatal sync produtos: {e}")
                self.db.rollback()
                break

        return {"status": "sucesso", "total_processado": total_upserted}

    def importar_pedidos_por_ids(self, lista_ids: list):
        """
        Recebe uma lista de IDs de pedidos (ex: [6066661, 6066662]).
        Consulta cada um na API, extrai Cliente e Produtos e salva no banco.
        """
        if not self.token:
            self.authenticate()

        # Endpoint baseados no seu exemplo
        url = f"{self.base_url}/api/wholesale/v1/orders/"

        resultados = {
            "sucesso": [],
            "erro": [],
            "clientes_atualizados": 0,
            "produtos_atualizados": 0,
        }

        for order_id in lista_ids:
            try:
                params = {"branchId": self.branch_id, "orderId": order_id}

                logger.info(f"Minerando dados do pedido {order_id}...")
                response = self.session.get(url, params=params)

                # Renovação de Token
                if response.status_code == 401:
                    self.authenticate()
                    response = self.session.get(url, params=params)

                if response.status_code == 404:
                    logger.warning(f"Pedido {order_id} não encontrado.")
                    resultados["erro"].append(f"ID {order_id} não encontrado")
                    continue

                response.raise_for_status()
                data = response.json()

                # O retorno pode ser uma lista (por ser filtro) ou objeto direto
                # Pelo seu exemplo parece objeto direto, mas filtros costumam retornar listas.
                # Vamos garantir:
                pedido_data = None
                if isinstance(data, list):
                    if data:
                        pedido_data = data[0]
                else:
                    pedido_data = data

                if not pedido_data:
                    resultados["erro"].append(f"ID {order_id} retorno vazio")
                    continue

                # --- 1. MINERAR CLIENTE ---
                cust_data = pedido_data.get("customer", {})
                if cust_data:
                    c_id = cust_data.get("id")
                    if c_id:
                        # Limpa CNPJ
                        raw_cnpj = str(cust_data.get("personIdentificationNumber", ""))
                        cnpj_limpo = "".join(filter(str.isdigit, raw_cnpj))

                        # Upsert Cliente
                        cliente_db = (
                            self.db.query(Cliente).filter(Cliente.id == c_id).first()
                        )
                        if not cliente_db:
                            cliente_db = Cliente(id=c_id)
                            self.db.add(cliente_db)
                            resultados["clientes_atualizados"] += 1

                        # Atualiza dados sempre
                        cliente_db.cnpj_cpf = cnpj_limpo
                        cliente_db.razao_social = cust_data.get("name")
                        cliente_db.plano_pag_padrao = cust_data.get("paymentPlanId")
                        cliente_db.sellerId = cust_data.get("sellerId")
                        cliente_db.chargingId = pedido_data.get(
                            "chargingId"
                        )  # Novo campo de cobrança
                        self.db.commit()
                # # --- 2. MINERAR PRODUTOS ---
                # itens = pedido_data.get("listOfOrderItem", [])
                # for item in itens:
                #     p_id = item.get("productId")
                #     if p_id:
                #         # Tenta pegar EAN do packingId ou SKUKey
                #         # Ex: packingId: 7898329390079
                #         ean = str(item.get("packingId") or "")

                #         prod_db = (
                #             self.db.query(Produto).filter(Produto.id == p_id).first()
                #         )
                #         if not prod_db:
                #             # Criamos o produto. Como não tem nome no JSON, usamos placeholder
                #             prod_db = Produto(
                #                 id=p_id,
                #                 nome=f"Produto {p_id} (Importado via Pedido)",
                #                 unidade="UN",  # Default, pois JSON não mostra unidade explícita
                #             )
                #             self.db.add(prod_db)
                #             resultados["produtos_atualizados"] += 1

                #         # Atualiza EAN se disponível e se o banco estiver vazio/antigo
                #         if ean and (not prod_db.ean or prod_db.ean == "SEM_EAN"):
                #             prod_db.ean = ean

                self.db.commit()
                resultados["sucesso"].append(order_id)

            except Exception as e:
                logger.error(f"Erro ao processar pedido {order_id}: {e}")
                self.db.rollback()
                resultados["erro"].append(f"ID {order_id}: {str(e)}")

        return resultados

    def enriquecer_produtos_locais(self, apenas_incompletos: bool = False):
        """
        Itera sobre os produtos do banco local e busca detalhes atualizados
        na API do Winthor endpoint: /api/purchases/v1/products/{id}
        """
        if not self.token:
            self.authenticate()

        # Seleciona produtos
        query = self.db.query(Produto)

        # Se quiser atualizar só os que vieram da importação de pedidos (sem nome)
        if apenas_incompletos:
            query = query.filter(Produto.nome == "" or Produto.ean == "")

        produtos_para_atualizar = query.all()

        logger.info(
            f"Iniciando enriquecimento de {len(produtos_para_atualizar)} produtos..."
        )

        atualizados = 0
        erros = 0

        for prod in produtos_para_atualizar:
            try:
                # Monta a URL conforme sua imagem: /products/{Código do produto}
                url = f"{self.base_url}/api/purchases/v1/products/{prod.id}"

                params = {
                    "branchId": self.branch_id,
                }

                response = self.session.get(url, params=params)

                # Tratamento de Token Expirado
                if response.status_code == 401:
                    self.authenticate()
                    response = self.session.get(url, params=params)

                if response.status_code == 404:
                    logger.warning(
                        f"Produto ID {prod.id} não encontrado na API de Detalhes."
                    )
                    continue

                response.raise_for_status()
                data = response.json()

                # A API retorna o objeto direto ou uma lista?
                # Endpoint de ID geralmente retorna objeto, mas Winthor as vezes retorna lista de 1 item.
                item_data = data
                if isinstance(data, list):
                    if data:
                        item_data = data[0]
                    else:
                        continue
                elif isinstance(data, dict) and "items" in data:
                    # Caso venha paginado mesmo pedindo ID
                    if data["items"]:
                        item_data = data["items"][0]
                    else:
                        continue

                # --- ATUALIZAÇÃO DOS DADOS ---

                # 1. Nome/Descrição
                if item_data.get("name"):
                    prod.nome = item_data.get("name")

                # 2. Unidade
                if item_data.get("unity"):
                    prod.unidade = item_data.get("unity")

                # 3. EAN (Tenta achar o melhor EAN disponível)
                # Winthor costuma ter lista de 'packagings' ou 'gtin' direto
                novo_ean = item_data.get("barCode")

                if novo_ean:
                    prod.ean = str(novo_ean)

                atualizados += 1

                # Commit a cada 50 para não segurar o banco
                if atualizados % 50 == 0:
                    self.db.commit()
                    logger.info(f"Processados {atualizados} produtos...")

            except Exception as e:
                logger.error(f"Erro ao atualizar produto {prod.id}: {e}")
                erros += 1
                continue

        self.db.commit()
        return {
            "total_processado": len(produtos_para_atualizar),
            "atualizados": atualizados,
            "erros": erros,
        }

    def enviar_pedido(self, pedido_validado: dict):
        """
        Envia o pedido aplicando regras finais:
        1. Conversão de Unidade (Unitário -> Caixa) via tabela ProdutoConversao.
        2. Atualização de EAN (Usa o que está no banco, ignora o do JSON).
        """
        try:
            if not self.token:
                self.authenticate()
        except Exception as e:
            logger.error(f"Erro ao autenticar antes de enviar pedido: {e}")
            raise Exception("Falha na autenticação com Winthor.")
        url = f"{self.base_url}/api/wholesale/v1/orders/"

        # 1. Preparar Cabeçalho
        try:
            cliente_dados = pedido_validado.get("dados_cliente", {})
            id_cliente = cliente_dados.get("id_winthor")
        except Exception as e:
            logger.error(f"Erro ao extrair dados do cliente do pedido: {e}")
            raise Exception("Dados do cliente inválidos ou ausentes no pedido.")

        cliente_db = self.db.query(Cliente).filter(Cliente.id == id_cliente).first()
        if not cliente_db:
            raise Exception(f"Cliente {id_cliente} não encontrado no banco local.")
        try:
            chargingId = (
                cliente_dados.get("chargingId")
                if cliente_dados.get("chargingId")
                else cliente_db.chargingId
            )
        except Exception as e:
            logger.error(f"Erro ao determinar chargingId para cliente {id_cliente}: {e}")
            raise Exception("Não foi possível determinar chargingId para o cliente do pedido.")
        
        sellerId = cliente_db.sellerId if cliente_db.sellerId else 0
        plano_pag = cliente_db.plano_pag_padrao if cliente_db.plano_pag_padrao else 1

        data_atual = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # 2. Preparar Itens (Com Conversão e Validação)
        itens_winthor = []
        seq = 1

        lista_itens = pedido_validado.get("itens", [])

        for item in lista_itens:
            id_origem = item.get("id_produto_winthor")
            if not id_origem:
                continue

            qtd_inicial = float(item.get("quantidade_total", 0))
            preco_inicial = float(item.get("valor_unitario", 0))
            valor_total = float(item.get("valor_total", 0))

            # --- REGRA 2: Conversão de Unidades (O Caso Chamyto) ---
            # Verifica se existe regra de conversão para este produto
            regra_conv = (
                self.db.query(ProdutoConversao)
                .filter(ProdutoConversao.id_produto_origem == id_origem)
                .first()
            )

            id_final = id_origem
            qtd_final = qtd_inicial
            preco_final = preco_inicial

            if regra_conv:
                logger.info(
                    f"Aplicando conversão no item {id_origem} -> {regra_conv.id_produto_destino} (Fator {regra_conv.fator})"
                )

                # Ex: 24 unidades / fator 6 = 4 caixas
                # math.floor trunca para baixo (25 vira 4)
                qtd_convertida = math.floor(qtd_inicial / regra_conv.fator)

                if qtd_convertida <= 0:
                    logger.warning(
                        f"Item {id_origem} ignorado: Qtd {qtd_inicial} insuficiente para fator {regra_conv.fator}"
                    )
                    continue  # Pula o item se não der nem 1 caixa

                # Atualiza valores
                id_final = regra_conv.id_produto_destino
                qtd_final = qtd_convertida
                preco_final = preco_inicial * regra_conv.fator
                valor_unitario_ajustado = valor_total / qtd_final if qtd_final > 0 else preco_final
                if abs(valor_unitario_ajustado - preco_final) > 0.01:  # Se o ajuste for significativo, loga
                    logger.info(
                        f"Ajuste de preço no item {id_origem}: Unitário original {preco_final:.2f} -> Ajustado {valor_unitario_ajustado:.2f} para manter valor total."
                    )
                preco_final = valor_unitario_ajustado

            # --- REGRA 1: Force EAN do Banco ---
            # Busca o produto FINAL (já convertido) no banco para pegar o EAN mais atual
            produto_db = self.db.query(Produto).filter(Produto.id == id_final).first()

            if not produto_db:
                logger.error(f"Produto {id_final} não encontrado no banco para envio.")
                continue  # Ou raise Exception dependendo da rigidez

            ean_final = produto_db.ean
            if not ean_final or ean_final == "SEM_EAN":
                # Tenta buscar na hora se não tiver (fallback)
                ean_final = self.get_ean_from_id(id_final) or "0"

            # Formato Winthor: "EAN-ID" ou apenas "ID"
            # É mais seguro mandar EAN-ID se tiver EAN, senão só ID
            sku_key = (
                f"{ean_final}-{id_final}"
                if ean_final and ean_final != "0"
                else str(id_final)
            )
            
            original = self.get_price_from_id(id_final, id_cliente)

            item_payload = {
                "productSKUERPReferenceKey": sku_key,
                "quantity": qtd_final,
                "sellPrice": round(preco_final, 8),  # Arredonda preço calculado
                "position": seq,
            }
            
            if original:
                item_payload["realCost"] = round(float(original), 8)
                discount = (preco_final - float(original)) * 100 / float(original)  if float(original) > 0 else 0
                discountValue = float(original) - preco_final
                if abs(discount) > 5:  # Loga desconto se for significativo
                    logger.info(f"Desconto significativo no item {id_final}: {discount:.2f}%")
                    logger.info(f"Preço original: {original:.2f}, Preço final: {preco_final:.2f}")
                item_payload["discountValue"] = round(discountValue, 6)
            itens_winthor.append(item_payload)
            seq += 1
            
        total = pedido_validado.get("totais", {}).get("pdf", 0)
        if total and total > 0:
            payload_total = sum(i["quantity"] * i["sellPrice"] for i in itens_winthor)
            if abs(payload_total - total) > 0.10:
                logger.info(f"Ajuste de preço total: Payload {payload_total:.2f} vs Total Pedido {total:.2f}.")
        total = round(payload_total, 2) if payload_total > 0 else total
            

        if not itens_winthor:
            raise Exception("Nenhum item válido gerado após validação e conversão.")

        # 3. Montar Payload Final
        sale_type = (
            5 if pedido_validado.get("is_bonificacao") else 1
        )  # Req 8: Bonificação
        
        unique_id = "".join(c for c in pedido_validado.get('numero_pedido') if c.isdigit())
        try:
            payload = {
            "branchId": str(self.branch_id),
            "customer": {"id": int(id_cliente)},
            "saleOrigin": "F",
            "chargingId": chargingId,
            "saleType": sale_type,
            "paymentPlanId": int(plano_pag),
            "createData": data_atual,
            "listOfOrderItem": itens_winthor,
            "seller": sellerId,
            "observation": f"PED {pedido_validado.get('numero_pedido')}",
            "shippingTrackingCodeSale": pedido_validado.get('numero_pedido'),
            }
            if unique_id:
                payload["uniqueSequencialNumber"] = unique_id
            if data_atual:
                payload["dateUniqueSequentialNumber"] = data_atual
            if total and total > 0:
                payload["TotalPrice"] = total
        except Exception as e:
            logger.error(f"Erro ao montar payload para envio do pedido: {e}")
            raise Exception("Falha ao preparar dados do pedido para envio.")

        # 4. Enviar
        logger.info(
            f"Enviando pedido Winthor (Bonif={pedido_validado.get('is_bonificacao')}). Itens: {len(itens_winthor)}"
        )
        try:
            # logger.info(f"Payload do pedido para Winthor: {json.dumps(payload, indent=2)}")
            response = self.session.post(url, json=payload)

            if response.status_code == 401:
                self.authenticate()
                response = self.session.post(url, json=payload)

            if not response.ok:
                logger.error(f"Erro ao enviar pedido: {response}")
                raise Exception(f"Erro Winthor {response.status_code}: {response.text}")

            return response.json()

        except Exception as e:
            logger.error(f"Falha no envio Winthor: {e}")
            raise e

    def cancelar_pedido_winthor(self, winthor_order_id: str):
        """
        Cancela um pedido no Winthor via API.
        """
        if not self.token:
            self.authenticate()
        logger.info(
            f"Iniciando cancelamento do pedido Winthor ID {winthor_order_id}..."
        )
        url = f"{self.base_url}/api/wholesale/v1/orders/"

        params = {"id": winthor_order_id, "reasonCancellation": "CancelImporter"}
        try:
            response = self.session.delete(url, params=params)

            if response.status_code == 401:
                self.authenticate()
                response = self.session.delete(url, params=params)
            if not response.ok:
                raise Exception(
                    f"Erro ao cancelar pedido {winthor_order_id}: {response.text}"
                )
            if response.status_code == 204 or not response.content:
                return {
                    "status": "sucesso",
                    "mensagem": "Pedido cancelado (sem retorno de conteúdo)",
                }
            logger.info(f"Pedido {winthor_order_id} cancelado com sucesso no Winthor.")
            return response.json()

        except Exception as e:
            logger.error(f"Falha ao cancelar pedido {winthor_order_id}: {e}")
            raise e
    def get_price_from_id(self, produto_id: int, customer_id: int):
        if self.token is None:
            self.authenticate()
        costumer_db = self.db.query(Cliente).filter(Cliente.id == customer_id).first()
        if not costumer_db:
            logger.error(f"Cliente {customer_id} não encontrado no banco local.")
            return None
        regionId = costumer_db.regionId
        url = f"{self.base_url}/api/wholesale/v1/price/list"
        params = {
            "branchId": self.branch_id,
            "productSKUERPReferenceKey": produto_id,
            "multiRegionPrice": True,            
        }
        try:
            response = self.session.get(url, params=params)
            if response.status_code == 401:
                self.authenticate()
                response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            lista = data if isinstance(data, list) else data.get("items", [])
            price = next(
                (
                    preco
                    for preco in lista
                    if preco.get("priceRegion") == regionId
                ),
                None,
            )
            if price:
                return price.get("price")
            else:
                return lista[0].get("price") if len(lista) > 0 else None
        except Exception as e:
            logger.error(f"Erro ao buscar preço do produto {produto_id}: {e}")
            return None