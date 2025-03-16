import os
import json
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
import logging
import time

# Configuração de logs
logging.basicConfig(
    filename='appcoleta.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Carrega variáveis do ambiente
load_dotenv()

def obter_token():
    try:
        auth_data = {
            'username': os.getenv('user'),
            'password': os.getenv('password'),
            'grant_type': os.getenv('grant_type'),
            'client_secret': os.getenv('client_secret_integrim'),
            'client_id': os.getenv('client_id_integrim')
        }
        
        response = requests.post(os.getenv('auth_url'), data=auth_data)
        if response.status_code == 200:
            token = response.json()['access_token']
            logging.info('Token obtido com sucesso')
            return token
        else:
            logging.error(f'Erro ao obter token. Status code: {response.status_code}')
            return None
    except Exception as e:
        logging.error(f'Erro ao obter token: {str(e)}')
        return None

def exibir_dados(df):
    # Métricas principais com status
    st.subheader('Dados da Coleta')
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Registros", len(df))
    with col2:
        st.metric("Produtos com Sobra", len(df[df['status_estoque'] == 'SOBRA']))
    with col3:
        st.metric("Produtos com Falta", len(df[df['status_estoque'] == 'FALTA']))
    with col4:
        st.metric("Produtos Iguais", len(df[df['status_estoque'] == 'IGUAL']))
    
    # Legenda
    st.info("""
    📊 Legenda:
    - 🔵 SOBRA: Quantidade coletada maior que estoque atual
    - 🔴 FALTA: Quantidade coletada menor que estoque atual
    - 🟢 IGUAL: Quantidade coletada igual ao estoque atual
    """)
    
    # Filtro de status
    status_filtro = st.radio(
        "Filtrar por status do estoque:",
        options=['TODOS', 'SOBRA', 'FALTA', 'IGUAL'],
        horizontal=True,
        key='status_filter'
    )
    
    # Aplica o filtro nos dados
    if status_filtro != 'TODOS':
        df_display = df[df['status_estoque'] == status_filtro].copy()
    else:
        df_display = df.copy()
    
    # Formata as colunas numéricas
    if 'qtdcoleta' in df_display.columns:
        df_display['qtdcoleta'] = df_display['qtdcoleta'].round(3)
    if 'qtdatualestoque' in df_display.columns:
        df_display['qtdatualestoque'] = df_display['qtdatualestoque'].round(3)
    if 'dtferença' in df_display.columns:
        df_display['dtferença'] = df_display['dtferença'].round(3)
    
    # Renomeia as colunas
    df_display.rename(columns={
        'idsubproduto': 'Cod Produto',
        'descricaoproduto': 'Produto',
        'fabricante': 'Marca',
        'qtdcoleta': 'Qtd Coletada',
        'qtdatualestoque': 'Qtd Estoque',
        'dtferença': 'Qtd Diferença',
        'status_estoque': 'Status Estoque'
    }, inplace=True)
    
    # Função para destacar status
    def highlight_status(row):
        if row['Status Estoque'] == 'SOBRA':
            return ['background-color: #90CAF9; color: black'] * len(row)  # Azul
        elif row['Status Estoque'] == 'FALTA':
            return ['background-color: #EF9A9A; color: black'] * len(row)  # Vermelho
        return ['background-color: #A5D6A7; color: black'] * len(row)      # Verde
    
    # Exibe a tabela estilizada com cabeçalho formatado
    st.subheader('Tabela de Dados')
    st.dataframe(
        df_display.style
            .apply(highlight_status, axis=1)
            .set_table_styles([
                {'selector': 'th',
                 'props': [
                     ('background-color', '#2C3E50'),
                     ('color', 'white'),
                     ('font-weight', 'bold'),
                     ('text-align', 'center'),
                     ('padding', '10px'),
                     ('font-size', '14px')
                 ]},
                {'selector': 'td',
                 'props': [
                     ('text-align', 'center')
                 ]}
            ])
            .format({
                'Qtd Coletada': '{:.3f}',
                'Qtd Estoque': '{:.3f}',
                'Qtd Diferença': '{:.3f}'
            }),
        use_container_width=True,
        hide_index=True
    )

def main():
    st.set_page_config(page_title="Dashboard de Coleta", layout="wide")
    st.title('Dashboard de Coleta de Estoque')

    # Criando colunas para os filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Dicionário com as opções de local
        locais_estoque = {
            "1 - LOJA": 1,
            "2 - DEPOSITO": 2
        }
        
        local_selecionado = st.selectbox(
            'Selecione o Local de Estoque',
            options=list(locais_estoque.keys())
        )
        local_estoque = locais_estoque[local_selecionado]

    with col2:
        data_inicial = st.date_input(
            'Data Inicial da Coleta',
            value=datetime.now(),
            format="DD/MM/YYYY"
        )
    
    with col3:
        data_final = st.date_input(
            'Data Final da Coleta',
            value=datetime.now(),
            format="DD/MM/YYYY"
        )

    # Checkbox para atualização automática
    auto_refresh = st.checkbox('Ativar atualização automática (15 segundos)', value=False)
    
    # Placeholder para a tabela
    table_placeholder = st.empty()
    
    # Botão para buscar dados
    if st.button('Buscar Dados') or ('auto_update' in st.session_state and auto_refresh):
        token = obter_token()
        if token:
            try:
                headers = {'Authorization': f'Bearer {token}'}
                payload = {
                    "page": 1,
                    "clausulas": [
                        {
                            "campo": "idlocal",
                            "operadorlogico": "AND",
                            "operador": "IGUAL",
                            "valor": local_estoque
                        },
                        {
                            "campo": "dtinicoleta",
                            "operadorlogico": "AND",
                            "operador": "IGUAL",
                            "valor": data_inicial.strftime('%Y-%m-%d')
                        },
                        {
                            "campo": "dtfimcoleta",
                            "operadorlogico": "AND",
                            "operador": "IGUAL",
                            "valor": data_final.strftime('%Y-%m-%d')
                        }
                    ]
                }
                
                response = requests.post(os.getenv('data_url'), json=payload, headers=headers)
                if response.status_code == 200:
                    dados = response.json()
                    
                    # Verifica se há dados retornados
                    if not dados.get('data'):
                        st.warning('Não foram encontradas coletas de estoque para o período selecionado.')
                        if 'dados_completos' in st.session_state:
                            del st.session_state.dados_completos
                        return
                    
                    if isinstance(dados.get('data'), list):
                        df = pd.DataFrame(dados['data'])
                    else:
                        df = pd.DataFrame([dados['data']])
                    
                    # Verifica se as colunas necessárias existem
                    colunas_necessarias = ['qtdcoleta', 'qtdatualestoque']
                    if not all(col in df.columns for col in colunas_necessarias):
                        st.error('Os dados retornados não contêm as informações necessárias de coleta.')
                        if 'dados_completos' in st.session_state:
                            del st.session_state.dados_completos
                        return
                    
                    # Adiciona coluna de status do estoque
                    df['status_estoque'] = 'IGUAL'
                    df.loc[df['qtdcoleta'] > df['qtdatualestoque'], 'status_estoque'] = 'SOBRA'
                    df.loc[df['qtdcoleta'] < df['qtdatualestoque'], 'status_estoque'] = 'FALTA'
                    
                    # Armazena dados na sessão
                    st.session_state.dados_completos = df
                    
                    # Configura atualização automática
                    if auto_refresh:
                        st.session_state.auto_update = True
                        time.sleep(15)
                        st.rerun()
                    else:
                        st.session_state.auto_update = False
                        
            except Exception as e:
                st.error(f'Erro ao buscar dados: {str(e)}')
                if 'dados_completos' in st.session_state:
                    del st.session_state.dados_completos

    # Exibe os dados se existirem na sessão
    if 'dados_completos' in st.session_state:
        exibir_dados(st.session_state.dados_completos)

if __name__ == "__main__":
    main()
