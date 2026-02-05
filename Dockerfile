# Usa uma imagem leve do Python 3.10
FROM python:3.10-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema necessárias para compilar algumas libs
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos e instala
COPY ./app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código
COPY ./app /app

# Comando para rodar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]