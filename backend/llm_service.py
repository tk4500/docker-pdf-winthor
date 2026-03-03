import os
import json
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger("LLMService")


class LLMService:
    def __init__(self):
        # Carrega chaves e limpa espaços
        keys_str = os.getenv("GEMINI_API_KEYS", "")
        self.api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]

        if not self.api_keys:
            logger.warning("Nenhuma chave GEMINI_API_KEYS encontrada no .env!")

        # Lista de Prioridade de Modelos (Do melhor/mais novo para o fallback)
        self.models = [
            "gemini-3-flash-preview",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemma-3-27b-it",
        ]
        self.last_used_model = None 

        # Se você quiser forçar exatamente os nomes que mandou (atenção que nomes preview mudam rápido):
        # self.models = ["gemini-3-flash-preview", "gemini-2.5-flash", "gemma-3-27b-it"]

    def _get_schema(self):
        """
        Define a estrutura: { "pedidos": [ ...lista de pedidos... ] }
        """
        # Definição do objeto PEDIDO individual
        pedido_schema = types.Schema(
            type=types.Type.OBJECT,
            required=["cliente", "produtos", "total_pedido_validacao"],
            properties={
                "numero_pedido": types.Schema(type=types.Type.STRING),
                "total_pedido_validacao": types.Schema(type=types.Type.NUMBER),
                "fornecedor": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "nome": types.Schema(type=types.Type.STRING),
                        "cnpj_cpf": types.Schema(type=types.Type.STRING),
                    },
                ),
                "cliente": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "nome": types.Schema(type=types.Type.STRING),
                        "cnpj_cpf": types.Schema(type=types.Type.STRING),
                    },
                ),
                "produtos": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        required=["descricao", "quantidade_total", "valor_unitario", "valor_total"],
                        properties={
                            "descricao": types.Schema(type=types.Type.STRING),
                            "codigo_referencia": types.Schema(type=types.Type.STRING),
                            "ean": types.Schema(type=types.Type.STRING),
                            "unidade_embalagem": types.Schema(type=types.Type.STRING),
                            "quantidade_total": types.Schema(type=types.Type.NUMBER),
                            "valor_unitario": types.Schema(type=types.Type.NUMBER),
                            "valor_total": types.Schema(type=types.Type.NUMBER),
                        },
                    ),
                ),
            },
        )

        # Schema Raiz encapsulando a lista
        return types.Schema(
            type=types.Type.OBJECT,
            properties={
                "pedidos": types.Schema(
                    type=types.Type.ARRAY,
                    items=pedido_schema
                )
            },
            required=["pedidos"]
        )

    def _get_toolconfig(self):
        """Define a configuração de ferramenta (tool config) para geração de conteúdo"""
        return types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="NONE")
        )

    def parse_pedido_text(self, text_content: str) -> dict:
        """
        Executa a rotação de chaves e modelos até conseguir uma resposta válida.
        """

        prompt_text = f"""
        Você é um sistema OCR de alta precisão.
        O texto abaixo pode conter UM ou MAIS pedidos de compra diferentes.
        Separe-os cuidadosamente.
        
        Regras:
        1. Se houver múltiplos números de pedidos ou cabeçalhos diferentes, crie objetos de pedido separados na lista.
        2. O texto preserva o layout visual. Use o espaçamento para distinguir colunas.
        3. 'Qtde' geralmente é quantidade de caixas. 'Emb' é quantas unidades por caixa. 
           Se houver 'Emb', a quantidade_total = Qtde * Emb. Se não, é apenas Qtde.
        4. Converta valores monetários para ponto flutuante (ex: 84,24 -> 84.24).
        5. Identifique EANs (códigos de barra).
        6. CNPJ tem 14 numeros e CPF tem 11, ambos podem ter formatações diferentes (com ou sem pontos, traços, etc), mas extraia todos os numeros para o campo cnpj_cpf.
        TEXTO DO PDF:
        {text_content}
        """

        # Configurações de Segurança (Permitir tudo, pois é processamento de dados)
        safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"
            ),
        ]
        
        thinking_config = types.ThinkingConfig(
            thinking_budget=0,
        )
        # --- Lógica de Rotação ---
        last_error = None

        for model in self.models:
            logger.info(f"Tentando modelo: {model}")

            for api_key in self.api_keys:
                try:
                    client = genai.Client(api_key=api_key)
                    
                    response_type = "application/json"
                    if model == "gemma-3-27b-it":
                        response_type = None

                    # Configuração da Geração
                    generate_config = types.GenerateContentConfig(
                        temperature=0.1,
                        thinking_config=thinking_config,
                        response_mime_type=response_type,
                        response_schema=self._get_schema(),
                        safety_settings=safety_settings,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                        tool_config=self._get_toolconfig()
                    )
                    
                        
                    # Chamada Síncrona (Stream=False é melhor para JSON parse)
                    response = client.models.generate_content(
                        model=model, contents=prompt_text, config=generate_config
                    )
                    self.last_used_model = model
                    logger.info(response)

                    # Retorna o JSON parseado nativamente pelo Python
                    # O SDK do Google já deve retornar um objeto se response_mime_type="application/json"
                    # mas as vezes vem como string no .text
                    try:
                        if model == "gemma-3-27b-it":
                            text = response.candidates[0].content.parts[0].text
                            response.text = text.replace("\n```json", "").replace("```", "").strip()
                        return json.loads(response.text)
                    except:
                        if hasattr(response, 'parsed'):
                            if response.parsed != None:
                                return response.parsed
                            else:
                                text = response.candidates[0].content.parts[0].text
                                response.text = text.replace("\n```json", "").replace("```", "").strip()
                        return json.loads(response.text)

                except Exception as e:
                    logger.warning(
                        f"Falha com modelo {model} e chave ...{api_key[-4:]}: {e}"
                    )
                    last_error = e
                    continue  # Tenta próxima chave

            # Se acabou as chaves para este modelo, tenta o próximo modelo no loop externo

        # Se chegou aqui, falhou tudo
        logger.error("Todas as tentativas de LLM falharam.")
        return {
            "error": "Falha crítica no processamento IA",
            "details": str(last_error),
        }
