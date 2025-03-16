# Imagem base Python
FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de requisitos
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Expõe a porta que o Streamlit usa
EXPOSE 8501

# Variáveis de ambiente para o Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Comando para executar a aplicação
CMD ["streamlit", "run", "appcoleta.py", "--server.port=8501", "--server.address=0.0.0.0"] 