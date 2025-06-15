import streamlit as st
import pandas as pd
import zipfile
import os
import tempfile
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents import create_csv_agent
from langchain.agents.agent_types import AgentType

# Configuração da página
st.set_page_config(page_title="Analisador Completo de CSV", page_icon="📊")
st.title("📊 Analisador Completo de CSV com Google Gemini")

# Sidebar para configurações
with st.sidebar:
    st.header("Configurações")
    google_api_key = st.text_input("Chave da API Google Gemini", type="password", 
                                    help="Insira sua chave da API Google Gemini para habilitar as perguntas.")
    model_name = st.selectbox(
        "Modelo",
        ["gemini-1.5-flash"],
        help="Selecione o modelo Gemini para análise.",
        index=0,
    )
    temperature = st.slider("Temperatura", 0.0, 1.0, 0.0, 0.1)
    st.markdown("---")
    st.markdown("Faça upload de um arquivo ZIP contendo arquivos CSV para análise completa.")

# Upload do arquivo ZIP
uploaded_file = st.file_uploader("Upload de arquivo ZIP com CSVs", type="zip")

# Processamento do arquivo ZIP
if uploaded_file is not None:
    # Criar diretório temporário
    temp_dir = tempfile.mkdtemp()
    
    # Extrair arquivos ZIP
    with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Listar arquivos CSV extraídos
    csv_files = [f for f in os.listdir(temp_dir) if f.endswith('.csv')]
    
    if not csv_files:
        st.error("Nenhum arquivo CSV encontrado no ZIP.")
    else:
        st.success(f"Arquivos CSV encontrados: {', '.join(csv_files)}")
        
        # Carregar DataFrames completos
        selected_file = st.selectbox("Selecione um arquivo para visualizar", csv_files)
        file_path = os.path.join(temp_dir, selected_file)
        
        try:
            # Carregar o arquivo completo
            df_full = pd.read_csv(file_path)
            
            # Mostrar informações completas
            st.subheader(f"Visualização do arquivo: {selected_file}")
            st.metric("Total de linhas", len(df_full))
            st.metric("Total de colunas", len(df_full.columns))
            
            # Exibir dados completos
            st.dataframe(df_full)
                
        except Exception as e:
            st.error(f"Erro ao ler o arquivo CSV: {e}")
        
        # Inicializar o agente se a chave da API foi fornecida
        if google_api_key:
            try:
                # Configurar o modelo Gemini
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=google_api_key,
                    temperature=temperature
                )
                
                # Criar agente com todos os CSVs
                agent = create_csv_agent(
                    llm,
                    [os.path.join(temp_dir, f) for f in csv_files],
                    verbose=True,
                    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    allow_dangerous_code=True
                )
                
                # Interface de perguntas
                st.markdown("---")
                st.header("Análise Completa dos Dados")
                
                question = st.text_area("Faça sua pergunta sobre os dados completos:", 
                                     height=100,
                                     placeholder="Ex: Quais são as estatísticas descritivas de todos os arquivos?")
                
                if st.button("Enviar Pergunta"):
                    with st.spinner("Processando dados completos..."):
                        try:
                            response = agent.run(question)
                            st.subheader("Resposta:")
                            st.write(response)
                        except Exception as e:
                            st.error(f"Erro ao processar a pergunta: {e}")
            except Exception as e:
                st.error(f"Erro ao criar o agente: {e}")
        else:
            st.warning("Por favor, insira sua chave da API Google Gemini para habilitar as perguntas.")
else:
    st.info("Por favor, faça upload de um arquivo ZIP contendo arquivos CSV.")

# Limpeza (opcional)
if uploaded_file and 'temp_dir' in locals():
    # Remover arquivos temporários (descomente se quiser)
    # import shutil
    # shutil.rmtree(temp_dir)
    pass