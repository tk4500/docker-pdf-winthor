# /docker-pdf-winthor/frontend/Dockerfile

# ESTÁGIO 1: Build (Pode ser Angular, React ou Vue)
FROM node:18-alpine as build
WORKDIR /app

# Copia pacotes e instala dependências
COPY package*.json ./
RUN npm install

# Copia o resto do código e compila
COPY . .
# Se for Angular geralmente é 'npm run build', ajuste se necessário
RUN npm run build 

# ESTÁGIO 2: Nginx (Produção)
FROM nginx:alpine
# Copia a configuração do Nginx que criamos
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copia os arquivos gerados no build para a pasta do Nginx
# ATENÇÃO: Se usar Angular, a pasta gerada costuma ser dist/nome-do-projeto/browser
# Se usar React/Vue (Vite), geralmente é apenas /dist
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]