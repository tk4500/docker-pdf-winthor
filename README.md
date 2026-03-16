
# Docker PDF Winthor

Sistema automatizado para importação de pedidos em PDF para o Winthor, utilizando IA (Gemini API) para processamento e conversão inteligente de formatos.

## 📋 Visão Geral

Este projeto oferece uma solução completa para:
- **Extração de dados** de PDFs de pedidos via OCR
- **Processamento inteligente** usando IA (Gemini) para parsing automático
- **Reconhecimento de padrões** com templates customizáveis
- **Conversão de formatos** para a API do Winthor
- **Sincronização bidirecional** de clientes e produtos
- **Gestão de pedidos** com validação e rastreamento

## 🎯 Funcionalidades Principais

### Processamento de Pedidos
- Upload de PDFs com processamento em background
- Extração de texto otimizada com limite de páginas
- Parsing automático via IA ou templates conhecidos
- Divisão inteligente de múltiplos pedidos (Req 10)
- Validação contra base de dados local

### Integração Winthor
- Sincronização de **clientes** e **produtos**
- Envio de pedidos com regras de negócio
- Suporte a **bonificações** (Req 8)
- Conversão de unidades entre sistemas (unitário ↔ caixa)
- Cancelamento de pedidos enviados
- Recuperação de preços e estoque em tempo real

### Criação Manual
- Interface para criar pedidos manualmente
- Busca de clientes e produtos
- Auto-processamento opcional
- Edição antes do envio final

### Sincronização
- Importação de pedidos antigos do Winthor
- Enriquecimento de dados de produtos
- Mapping automático de IDs entre sistemas

## 🛠️ Stack Tecnológico

### Backend
- **FastAPI** - API REST
- **SQLAlchemy** - ORM
- **PostgreSQL** - Banco de dados
- **Gemini API** - Processamento com IA
- **Requests** - Integração Winthor

### Frontend
- **React** - Interface web
- **React Router** - Navegação
- **Axios** - HTTP client
- **Lucide React** - Ícones

### DevOps
- **Docker** - Containerização
- **Docker Compose** - Orquestração

## 📦 Estrutura do Projeto

```
docker-pdf-winthor/
├── backend/
│   ├── main.py                    # API FastAPI
│   ├── models.py                  # Modelos SQLAlchemy
│   ├── schemas.py                 # Pydantic schemas
│   ├── winthor_client.py          # Cliente Winthor API
│   ├── background_jobs.py         # Processamento async
│   ├── validator_service.py       # Validação de pedidos
│   ├── llm_service.py             # Integração Gemini
│   ├── pdf_processor.py           # Extração de PDFs
│   ├── learning_service.py        # ML para aliases
│   └── parsers/                   # Templates de parsing
├── frontend/
│   └── src/
│       ├── pages/                 # PedidoManual, PedidoEdit, etc
│       ├── components/            # ClientSearch, ProductSearch
│       └── api.js                 # Cliente HTTP
└── docker-compose.yml
```

## 🚀 Quick Start

### Pré-requisitos
- Docker & Docker Compose
- Gemini API Key
- Credenciais Winthor

### Variáveis de Ambiente (.env)
```env
# Gemini
GEMINI_API_KEY=seu_token_aqui

# Winthor
WINTHOR_BASE_URL=https://api.winthor.com
WINTHOR_USERNAME=usuario
WINTHOR_PASSWORD=senha

# Database
DATABASE_URL=postgresql://user:pass@db:5432/winthor_db

# JWT
SECRET_KEY=sua_chave_secreta
```

### Iniciar
```bash
docker-compose up -d
```

Acesse:
- Frontend: `http://localhost`
- API: `http://localhost/api/docs`

## 📡 Endpoints Principais

### Pedidos
- `POST /pedidos/upload` - Upload PDF para processamento
- `POST /pedidos/manual` - Criar pedido manualmente
- `POST /pedidos/finalizar/{job_id}` - Enviar para Winthor
- `GET /pedidos/{job_id}` - Detalhar pedido
- `DELETE /pedidos/{job_id}` - Cancelar pedido

### Sincronização
- `POST /sync/clientes` - Sincronizar clientes
- `POST /sync/produtos` - Sincronizar produtos
- `POST /sync/importar-pedidos-antigos` - Importar do Winthor

### Debug
- `POST /debug/pdf-to-text` - Extrair texto do PDF
- `POST /debug/pdf-to-json-ai` - Testar IA
- `POST /debug/generate-code` - Gerar código parser

## 🔐 Permissões

- `order:create` - Criar pedidos
- `order:read` - Ler pedidos próprios
- `order:read_all` - Ler todos pedidos
- `order:approve` - Aprovar/enviar
- `order:cancel` - Cancelar pedidos
- `sync:winthor` - Sincronizar dados
- `admin` - Acesso total

## 🔄 Fluxo de Processamento

```
PDF Upload
    ↓
Extração de Texto (PDFProcessor)
    ↓
Template Reconhecido? → Parsing Template
    ↓ Não
PDF Pequeno? → Parsing IA (Gemini)
    ↓ Não
Erro: PDF muito grande
    ↓
Validação contra BD Local
    ↓
Análise de Aprendizado (Aliases)
    ↓
Auto-Process? → Envio Winthor
    ↓ Não
Aguardar Aprovação Manual
    ↓
Envio Winthor (com regras)
    ↓
Armazenar orderId para Cancelamento
```

## 💡 Recursos Avançados

- **Req 5**: Auto-processamento com avanço automático de fluxo
- **Req 8**: Suporte a bonificações com `chargingId="BNF"`
- **Req 9**: Forçar processamento IA ignorando templates
- **Req 10**: Divisão inteligente de múltiplos pedidos em sub-jobs

## 🐛 Troubleshooting

**Erro 401 Winthor**: Token expirado → reautenticação automática  
**PDF muito grande**: Máx 10 páginas para IA → Use templates  
**Produto não encontrado**: Execute sincronização `/sync/produtos`

## 📝 Licença

MIT
