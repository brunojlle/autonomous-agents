# data_analyst_app.py

import streamlit as st
from dotenv import load_dotenv
from agent_workflow import create_data_analysis_workflow 
import os
import pandas as pd
import re
import xml.etree.ElementTree as ET

def parse_nfe_xml(uploaded_file) -> pd.DataFrame:
    """
    Robust NF-e XML parser that is namespace-agnostic.
    Each <det> (item) becomes a row; invoice-level fields are repeated.
    Works with default namespaces by comparing local tag names.
    """
    def local(tag: str) -> str:
        return tag.split('}')[-1] if '}' in tag else tag

    def find_child_by_local(parent, name):
        if parent is None:
            return None
        for child in parent:
            if local(child.tag) == name:
                return child
        return None

    def find_all_by_local(parent, name):
        return [el for el in parent.iter() if local(el.tag) == name]

    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    raw = uploaded_file.read()
    if isinstance(raw, bytes):
        try:
            raw = raw.decode('utf-8')
        except Exception:
            raw = raw.decode('latin-1', errors='replace')

    try:
        root = ET.fromstring(raw)
    except Exception as e:
        try:
            uploaded_file.seek(0)
            root = ET.parse(uploaded_file).getroot()
        except Exception as e2:
            raise RuntimeError(f"Erro ao parsear XML: {e} / {e2}")

    rows = []
    inf_nodes = find_all_by_local(root, "infNFe")
    if not inf_nodes:
        inf_nodes = find_all_by_local(root, "infNFe")

    for inf in inf_nodes:
        ide = find_child_by_local(inf, "ide")
        emit = find_child_by_local(inf, "emit")
        dest = find_child_by_local(inf, "dest")

        total = None
        for el in inf.iter():
            if local(el.tag) == "ICMSTot":
                total = el
                break

        def text_from(parent, tagname):
            if parent is None:
                return None
            ch = find_child_by_local(parent, tagname)
            return ch.text.strip() if ch is not None and ch.text else None

        invoice = {
            "cNF": text_from(ide, "cNF"),
            "nNF": text_from(ide, "nNF"),
            "dhEmi": text_from(ide, "dhEmi"),
            "emit_CNPJ": text_from(emit, "CNPJ"),
            "emit_xNome": text_from(emit, "xNome"),
            "dest_CNPJ": text_from(dest, "CNPJ"),
            "dest_xNome": text_from(dest, "xNome"),
            "vNF": text_from(total, "vNF"),
        }

        dets = [d for d in inf if local(d.tag) == "det"]
        if not dets:
            dets = [d for d in inf.iter() if local(d.tag) == "det"]

        if not dets:
            row = invoice.copy()
            row.update({"nItem": None})
            rows.append(row)
            continue

        for det in dets:
            nItem = det.attrib.get("nItem")
            prod = find_child_by_local(det, "prod")
            if prod is None:
                row = invoice.copy()
                row.update({"nItem": nItem})
                rows.append(row)
                continue

            row = invoice.copy()
            row.update({
                "nItem": nItem,
                "prod_cProd": text_from(prod, "cProd"),
                "prod_xProd": text_from(prod, "xProd"),
                "prod_NCM": text_from(prod, "NCM"),
                "prod_qCom": text_from(prod, "qCom"),
                "prod_uCom": text_from(prod, "uCom"),
                "prod_vUnCom": text_from(prod, "vUnCom"),
                "prod_vProd": text_from(prod, "vProd"),
            })
            rows.append(row)

    df = pd.DataFrame(rows)
    df["source_file"] = getattr(uploaded_file, "name", None)
    return df

# Load environment variables
load_dotenv()

# --- Page Configuration and Session State ---

st.set_page_config(page_title="Plataforma Inteligente de Análise de Dados", layout="wide")

# Initialize session state if not present
def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Olá! Configure o LLM Gemini e carregue um ou mais arquivos XML para começar a explorar seus dados."}]
    if "agent_executor" not in st.session_state:
        st.session_state.agent_executor = None
    if "dataframe" not in st.session_state:
        st.session_state.dataframe = None

initialize_session_state()


# --- Application Layout (Sidebar and Chat) ---

st.title("📊 Explorador de Dados por IA")
st.write("Configure seu modelo Gemini e carregue arquivos XML (um ou vários) para análise baseada em código.")

with st.sidebar:
    st.header("⚙️ Configuração do LLM (Google Gemini)")

    # API key input field
    api_key = st.text_input("Insira sua Chave de API do Gemini:", type="password")

    # Model name input field
    model_name_default = "gemini-2.5-flash"
    model_name = st.text_input("Nome do Modelo:", value=model_name_default, placeholder=model_name_default)

    st.header("📂 Carregamento de Arquivos XML")
    # Accept multiple XML files only
    uploaded_files = st.file_uploader("Escolha um ou mais arquivos XML", type=["xml"], accept_multiple_files=True)

    # Button to create/update the agent
    if st.button("Inicializar Agente"):
        if not api_key:
            st.warning("Por favor, insira sua chave de API do Gemini.")
        elif not model_name:
            st.warning(f"Por favor, insira o nome do modelo. Sugestão: `{model_name_default}`")
        elif not uploaded_files:
            st.warning("Por favor, carregue pelo menos um arquivo XML.")
        else:
            with st.spinner("Processando arquivos XML e configurando agente..."):
                dataframes = []
                errors = []

                # Loop through uploaded files and parse each one
                for uploaded_file in uploaded_files:
                    try:
                        try:
                            uploaded_file.seek(0)
                        except Exception:
                            pass

                        parsed_df = parse_nfe_xml(uploaded_file)
                        if parsed_df is None or parsed_df.empty:
                            errors.append(f"{getattr(uploaded_file, 'name', str(uploaded_file))}: nenhum registro extraído do XML.")
                        else:
                            dataframes.append(parsed_df)
                    except Exception as e_file:
                        errors.append(f"{getattr(uploaded_file, 'name', str(uploaded_file))}: {e_file}")

                # Report errors if any
                if errors:
                    st.error("Ocorreram erros ao ler os seguintes arquivos XML:")
                    for err in errors:
                        st.error(err)
                    st.session_state.dataframe = None
                    st.session_state.agent_executor = None

                # No dataframes produced
                elif not dataframes:
                    st.error("Nenhum DataFrame foi gerado a partir dos arquivos XML fornecidos.")
                    st.session_state.dataframe = None
                    st.session_state.agent_executor = None

                # All good: concat and create agent
                else:
                    try:
                        dataframe = pd.concat(dataframes, ignore_index=True, sort=False)
                        st.session_state.dataframe = dataframe

                        executor = create_data_analysis_workflow(dataframe, api_key, model_name)
                        if isinstance(executor, Exception):
                            st.error(f"Erro ao criar o agente: {executor}")
                            st.session_state.agent_executor = None
                        else:
                            st.session_state.agent_executor = executor
                            file_count = len(uploaded_files)
                            st.session_state.messages = [{"role": "assistant", "content": f"Agente configurado com `{model_name}`. {file_count} arquivo(s) carregado(s). Como posso ajudar na sua análise de dados?"}]
                            st.success("Agente inicializado com sucesso!")
                            st.dataframe(dataframe.head())
                    except Exception as e:
                        st.error(f"Erro ao processar os dados: {e}")
                        st.session_state.dataframe = None
                        st.session_state.agent_executor = None
                        st.stop()

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