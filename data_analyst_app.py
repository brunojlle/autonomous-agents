# data_analyst_app.py

import streamlit as st
from dotenv import load_dotenv
from agent_workflow import create_data_analysis_workflow 
import os
import pandas as pd
import re

# Load environment variables
load_dotenv()

# --- Page Configuration and Session State ---

st.set_page_config(page_title="Plataforma Inteligente de Análise de Dados", layout="wide")

# Initialize session state if not present
def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Olá! Configure o LLM Gemini e carregue um arquivo CSV ou Excel para começar a explorar seus dados."}]
    if "agent_executor" not in st.session_state:
        st.session_state.agent_executor = None
    if "dataframe" not in st.session_state:
        st.session_state.dataframe = None

initialize_session_state()


# --- Application Layout (Sidebar and Chat) ---

st.title("📊 Explorador de Dados por IA")
st.write("Configure seu modelo Gemini 2.5 e carregue dados para uma análise poderosa baseada em código.")

with st.sidebar:
    st.header("⚙️ Configuração do LLM (Google Gemini)")

    # API key input field
    api_key = st.text_input("Insira sua Chave de API do Gemini:", type="password")

    # Model name input field
    model_name_default = "gemini-2.5-flash"
    model_name = st.text_input("Nome do Modelo:", value=model_name_default, placeholder=model_name_default)

    st.header("📂 Carregamento de Dados")
    uploaded_file = st.file_uploader("Escolha um arquivo CSV ou Excel", type=["csv", "xls", "xlsx"])

    # Button to create/update the agent
    if st.button("Inicializar Agente"):
        if not api_key:
            st.warning("Por favor, insira sua chave de API do Gemini.")
        elif not model_name:
            st.warning(f"Por favor, insira o nome do modelo. Sugestão: `{model_name_default}`")
        elif uploaded_file is None:
            st.warning("Por favor, carregue um arquivo CSV ou Excel.")
        else:
            with st.spinner("Processando arquivo e configurando agente..."):
                try:
                    # Load DataFrame based on file extension
                    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
                    if file_extension == ".csv":
                        dataframe = pd.read_csv(uploaded_file)
                    elif file_extension in [".xls", ".xlsx"]:
                        dataframe = pd.read_excel(uploaded_file)
                    else:
                        st.error("Formato de arquivo não suportado. Use CSV ou Excel.")
                        st.stop()
                    st.session_state.dataframe = dataframe
                    
                    # Create the agent with the provided settings
                    executor = create_data_analysis_workflow(dataframe, api_key, model_name) 
                    
                    if isinstance(executor, Exception):
                        st.error(f"Erro ao criar o agente: {executor}")
                        st.session_state.agent_executor = None
                    else:
                        st.session_state.agent_executor = executor
                        # Reset chat for the new analysis
                        st.session_state.messages = [{"role": "assistant", "content": f"Agente configurado com `{model_name}` e arquivo `{uploaded_file.name}` carregado. Como posso ajudar na sua análise de dados?"}]
                        st.success("Agente inicializado com sucesso!")
                        st.dataframe(dataframe.head())

                except Exception as e:
                    st.error(f"Erro ao processar os dados: {e}")
                    st.session_state.dataframe = None
                    st.session_state.agent_executor = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# --- Chat Logic ---

if prompt := st.chat_input("Qual é a sua pergunta sobre os dados?"):
    if st.session_state.agent_executor is None:
        st.warning("Por favor, configure o LLM e carregue um arquivo na barra lateral primeiro.")
        st.stop()

    # Add user message to history and screen
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Invoke the agent
    with st.chat_message("assistant"):
        with st.spinner("Analisando dados..."):
            # Prepare agent input, including chat history
            agent_input = {
                "input": prompt,
                "chat_history": [msg for msg in st.session_state.messages if msg['role'] != 'assistant' or 'steps:' not in msg['content']]
            }

            try:
                # Invoke the agent
                response = st.session_state.agent_executor.invoke(agent_input)

                # Display agent reasoning steps
                with st.expander("Ver Fluxo de Raciocínio do Agente", expanded=False):
                    intermediate_steps = response.get("intermediate_steps", [])
                    if not intermediate_steps:
                        st.write("Nenhum passo intermediário executado (ex: resposta direta fornecida).")
                    else:
                        for i, step in enumerate(intermediate_steps):
                            st.subheader(f"🔄 Ciclo {i+1}")
                            action, observation = step

                            # 1. Agent Thought
                            st.markdown("##### 1. Pensamento")
                            st.text(action.log.strip())

                            # 2. Action Executed
                            st.markdown("##### 2. Ação")
                            st.markdown(f"**Ferramenta:** `{action.tool}`")
                            st.markdown("**Entrada da Ação (Código Executado):**")
                            st.code(action.tool_input, language="python")

                            # 3. Observation (Result of Action)
                            st.markdown("##### 3. Observação")
                            st.markdown(observation)
                            
                            if i < len(intermediate_steps) - 1:
                                st.divider()

                # Display final response
                final_answer = response.get("output", "Desculpe, não foi possível gerar uma resposta.")         

                # Handle iteration limit gracefully
                if "Agent stopped due to iteration limit" in final_answer:
                    st.warning("A análise se tornou muito complexa e atingiu o limite de iterações. Aqui está o último passo conhecido:")
                    intermediate_steps = response.get("intermediate_steps", [])
                    if intermediate_steps:
                        last_action, last_observation = intermediate_steps[-1]
                        st.markdown("##### Pensamento")
                        st.text(last_action.log.strip())
                        st.markdown("##### Observação")
                        st.markdown(last_observation)
                    st.session_state.messages.append({"role": "assistant", "content": "A análise não foi concluída dentro do limite de tempo."})
                else:
                    # Logic to robustly extract and display charts
                    chart_tag = "[CHART_PATH:"
                    if chart_tag in final_answer:
                        parts = final_answer.split(chart_tag)
                        if parts[0].strip():
                            st.write(parts[0])
                        for part in parts[1:]:
                            if ']' in part:
                                image_path, text_after = part.split(']', 1)
                                image_path = image_path.strip()
                                try:
                                    st.image(image_path, caption="Gráfico gerado pela IA.", use_column_width=True)
                                except Exception as img_e:
                                    st.error(f"Erro ao exibir o gráfico em '{image_path}': {img_e}")
                                if text_after.strip():
                                    st.write(text_after)
                            else:
                                st.write(f"{chart_tag}{part}")
                    else:
                        st.write(final_answer)
                    st.session_state.messages.append({"role": "assistant", "content": final_answer})
            except Exception as e:
                st.error("Ocorreu um erro durante a execução do agente. Veja os detalhes abaixo:")
                st.exception(e)
                st.session_state.messages.append({"role": "assistant", "content": f"Erro de execução: {e}"})