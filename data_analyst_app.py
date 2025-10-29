import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from agent_workflow import create_data_analysis_workflow

st.set_page_config(page_title="Plataforma Inteligente de Análise de Notas Fiscais", layout="wide")

st.title("📊 Plataforma Inteligente de Análise de Notas Fiscais Eletrônicas (XML)")

# --- Configuração do Modelo ---
with st.sidebar:
    st.header("⚙️ Configuração do Modelo Gemini")
    api_key = st.text_input("Chave da API Gemini", type="password")
    model_name_default = "gemini-2.5-flash"
    model_name = st.text_input("Nome do modelo", value=model_name_default)

# --- Upload de XMLs ---
with st.sidebar:
    st.header("📂 Carregamento de Arquivos XML")
    uploaded_files = st.file_uploader(
        "Envie um ou mais arquivos XML de NF-e",
        type=["xml"],
        accept_multiple_files=True
    )

    if st.button("Inicializar Agente"):
        if not api_key:
            st.warning("Insira sua chave de API do Gemini.")
        elif not model_name:
            st.warning(f"Insira o nome do modelo. Sugestão: `{model_name_default}`")
        elif not uploaded_files:
            st.warning("Envie pelo menos um arquivo XML.")
        else:
            with st.spinner("Processando XMLs e criando agente..."):
                try:
                    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
                    all_data = []

                    for uploaded_file in uploaded_files:
                        tree = ET.parse(uploaded_file)
                        root = tree.getroot()

                        ide = root.find(".//nfe:ide", ns)
                        emit = root.find(".//nfe:emit", ns)
                        dest = root.find(".//nfe:dest", ns)
                        total = root.find(".//nfe:ICMSTot", ns)
                        dets = root.findall(".//nfe:det", ns)

                        for det in dets:
                            prod = det.find("nfe:prod", ns)

                            row = {
                                "arquivo": uploaded_file.name,
                                "numero_nfe": ide.findtext("nfe:nNF", default="", namespaces=ns) if ide is not None else "",
                                "data_emissao": ide.findtext("nfe:dhEmi", default="", namespaces=ns) if ide is not None else "",
                                "emitente_nome": emit.findtext("nfe:xNome", default="", namespaces=ns) if emit is not None else "",
                                "emitente_cnpj": emit.findtext("nfe:CNPJ", default="", namespaces=ns) if emit is not None else "",
                                "destinatario_nome": dest.findtext("nfe:xNome", default="", namespaces=ns) if dest is not None else "",
                                "destinatario_cnpj": dest.findtext("nfe:CNPJ", default="", namespaces=ns) if dest is not None else "",
                                "produto_codigo": prod.findtext("nfe:cProd", default="", namespaces=ns) if prod is not None else "",
                                "produto_nome": prod.findtext("nfe:xProd", default="", namespaces=ns) if prod is not None else "",
                                "quantidade": prod.findtext("nfe:qCom", default="", namespaces=ns) if prod is not None else "",
                                "valor_unitario": prod.findtext("nfe:vUnCom", default="", namespaces=ns) if prod is not None else "",
                                "valor_total_produto": prod.findtext("nfe:vProd", default="", namespaces=ns) if prod is not None else "",
                                "valor_total_nfe": total.findtext("nfe:vNF", default="", namespaces=ns) if total is not None else "",
                            }
                            all_data.append(row)

                    dataframe = pd.DataFrame(all_data)
                    st.session_state.dataframe = dataframe

                    executor = create_data_analysis_workflow(dataframe, api_key, model_name)
                    st.session_state.agent_executor = executor
                    st.session_state.messages = []
                    st.session_state.chat_history = []

                    st.success("Agente configurado e XMLs carregados com sucesso.")
                    st.dataframe(dataframe.head())

                except Exception as e:
                    st.error(f"Erro ao processar os XMLs: {e}")
                    st.session_state.dataframe = None
                    st.session_state.agent_executor = None

# --- Chat ---
if "agent_executor" in st.session_state and st.session_state.agent_executor:
    st.header("💬 Chat de Análise de NF-e")

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    user_input = st.chat_input("Digite sua pergunta sobre as notas fiscais...")

    if user_input:
        st.chat_message("user").write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.spinner("Analisando..."):
            try:
                response = st.session_state.agent_executor.invoke({
                    "input": user_input,
                    "chat_history": st.session_state.chat_history
                })

                # Tratamento seguro: verifica se há saída válida
                answer = response.get("output") if isinstance(response, dict) else None
                if not answer:
                    raise ValueError("Nenhum resultado retornado pelo modelo.")

                st.chat_message("assistant").write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

                st.session_state.chat_history.append(("user", user_input))
                st.session_state.chat_history.append(("assistant", answer))

            except Exception as e:
                st.error(f"Erro durante a análise: {e}")
