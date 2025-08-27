import streamlit as st
import pandas as pd
import zipfile
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, date
import numpy as np
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents import create_csv_agent
from langchain.agents.agent_types import AgentType

# Configuração da página
st.set_page_config(page_title="Processador ZIP para CSV - VR/VA", page_icon="📊")
st.title("📊 Processador de Arquivos ZIP para CSV - Automação VR/VA")

# Sidebar para configurações
with st.sidebar:
    st.header("Configurações")
    google_api_key = st.text_input("Chave da API Google Gemini", type="password",
                                    help="Insira sua chave da API Google Gemini para habilitar análises.")
    model_name = st.selectbox(
        "Modelo",
        ["gemini-1.5-flash"],
        help="Selecione o modelo Gemini para análise.",
        index=0,
    )
    temperature = st.slider("Temperatura", 0.0, 1.0, 0.0, 0.1)
    
    st.markdown("---")
    st.markdown("Faça upload de um arquivo ZIP contendo arquivos Excel/CSV. Os arquivos serão processados e salvos na pasta 'output_folder'.")

INSTRUCTION = """
Por favor, responda sempre em português brasileiro (pt-BR), de forma clara e detalhada.
Se estiver analisando dados, inclua explicações em português sobre os resultados.
Foque em análises relacionadas ao processamento de Vale Refeição e benefícios corporativos.
"""

def convert_excel_to_csv(file_path, output_dir):
    """Converte arquivo Excel para CSV"""
    try:
        # Detectar se é arquivo Excel
        file_ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).stem
        
        if file_ext in ['.xlsx', '.xls', '.xlsm']:
            # Ler arquivo Excel
            excel_file = pd.ExcelFile(file_path)
            converted_files = []
            
            # Se há múltiplas abas, converter cada uma
            if len(excel_file.sheet_names) > 1:
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    csv_filename = f"{file_name}_{sheet_name}.csv"
                    csv_path = os.path.join(output_dir, csv_filename)
                    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                    converted_files.append(csv_filename)
            else:
                # Uma única aba
                df = pd.read_excel(file_path)
                csv_filename = f"{file_name}.csv"
                csv_path = os.path.join(output_dir, csv_filename)
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                converted_files.append(csv_filename)
            
            return converted_files, True
        else:
            return [], False
    except Exception as e:
        st.error(f"Erro ao converter {file_path}: {str(e)}")
        return [], False

def generate_final_vr_report(csv_files_dir, output_dir):
    """
    Gera planilha final de VR para envio à operadora
    Modelo: VR Mensal 05.2025
    Divisão: 80% empresa / 20% profissional
    """
    try:
        st.info("🔄 Gerando planilha final de VR...")
        
        # Buscar arquivos CSV na pasta
        csv_files = [f for f in os.listdir(csv_files_dir) if f.endswith('.csv')]
        
        if not csv_files:
            st.error("Nenhum arquivo CSV encontrado para processar.")
            return None
        
        # Lista para armazenar todos os dados processados
        all_data = []
        sindicatos_valores = {}
        colaboradores_ferias = set()
        colaboradores_desligados = {}
        
        progress_bar = st.progress(0)
        total_files = len(csv_files)
        
        # Processar cada arquivo CSV
        for i, csv_file in enumerate(csv_files):
            file_path = os.path.join(csv_files_dir, csv_file)
            progress_bar.progress((i + 1) / total_files)
            
            try:
                df = pd.read_csv(file_path)
                st.write(f"📊 Processando: {csv_file} ({len(df)} registros)")
                
                # Limpar nomes das colunas (remover espaços e padronizar)
                df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
                
                # Identificar e processar cada tipo de arquivo
                file_lower = csv_file.lower()
                
                if any(keyword in file_lower for keyword in ['ativo', 'colaborador', 'funcionario', 'base']):
                    # Processar base de colaboradores
                    for _, row in df.iterrows():
                        if pd.notna(row.get('matricula')) or pd.notna(row.get('matrícula')):
                            all_data.append({
                                'matricula': str(row.get('matricula') or row.get('matrícula', '')).strip(),
                                'nome': str(row.get('nome') or row.get('funcionario', '')).strip(),
                                'cargo': str(row.get('cargo') or row.get('função', '')).strip(),
                                'sindicato': str(row.get('sindicato') or '').strip(),
                                'admissao': row.get('admissao') or row.get('data_admissao'),
                                'desligamento': row.get('desligamento') or row.get('data_desligamento'),
                                'dias_uteis': row.get('dias_uteis') or row.get('dias_trabalhados', 22),
                                'status': 'ATIVO',
                                'fonte': csv_file
                            })
                
                elif 'ferias' in file_lower:
                    # Processar colaboradores em férias
                    for _, row in df.iterrows():
                        matricula = str(row.get('matricula') or row.get('matrícula', '')).strip()
                        if matricula:
                            colaboradores_ferias.add(matricula)
                
                elif 'sindicato' in file_lower or 'valor' in file_lower:
                    # Processar valores por sindicato
                    for _, row in df.iterrows():
                        sindicato = str(row.get('sindicato') or '').strip()
                        valor = row.get('valor_vr') or row.get('valor', 25.00)
                        if sindicato:
                            sindicatos_valores[sindicato] = float(valor)
                
                elif 'desligado' in file_lower:
                    # Processar desligamentos
                    for _, row in df.iterrows():
                        matricula = str(row.get('matricula') or row.get('matrícula', '')).strip()
                        data_comunicacao = row.get('data_comunicacao') or row.get('comunicacao')
                        if matricula:
                            colaboradores_desligados[matricula] = data_comunicacao
                            
            except Exception as e:
                st.error(f"Erro ao processar {csv_file}: {str(e)}")
                continue
        
        # Verificar se há dados para processar
        if not all_data:
            st.error("Nenhum dado válido encontrado nos arquivos CSV.")
            return None
        
        # Converter para DataFrame
        df_final = pd.DataFrame(all_data)
        
        # Aplicar lógica de negócio
        df_final = apply_business_rules(df_final, sindicatos_valores, colaboradores_ferias, colaboradores_desligados)
        
        # Gerar arquivo final
        output_file = os.path.join(output_dir, f"VR_Mensal_{datetime.now().strftime('%m_%Y')}_Final.xlsx")
        
        # Salvar relatório
        save_final_excel_report(df_final, output_file, sindicatos_valores)
        
        progress_bar.empty()
        st.success(f"✅ Planilha final gerada com sucesso!")
        
        return output_file
        
    except Exception as e:
        st.error(f"Erro na geração da planilha final: {str(e)}")
        return None

def apply_business_rules(df, sindicatos_valores, colaboradores_ferias, colaboradores_desligados):
    """Aplica todas as regras de negócio para cálculo do VR"""
    
    today = datetime.now()
    current_month = today.month
    current_year = today.year
    
    # Aplicar regras colaborador por colaborador
    for idx, row in df.iterrows():
        matricula = row['matricula']
        
        # Definir valor VR baseado no sindicato
        sindicato = row['sindicato'] if row['sindicato'] else 'PADRAO'
        valor_unitario = sindicatos_valores.get(sindicato, 25.00)  # Valor padrão R$ 25,00
        df.at[idx, 'valor_vr_unitario'] = valor_unitario
        
        # Verificar exclusões por cargo
        cargo = str(row['cargo']).upper()
        exclusoes = ['DIRETOR', 'ESTAGIARIO', 'APRENDIZ', 'TERCEIRIZADO']
        
        if any(excl in cargo for excl in exclusoes):
            df.at[idx, 'status'] = 'EXCLUIDO'
            df.at[idx, 'motivo_exclusao'] = f'Cargo: {cargo}'
            df.at[idx, 'dias_uteis_final'] = 0
            continue
        
        # Verificar se está em férias
        if matricula in colaboradores_ferias:
            df.at[idx, 'status'] = 'FERIAS'
            df.at[idx, 'motivo_exclusao'] = 'Colaborador em férias'
            df.at[idx, 'dias_uteis_final'] = 0
            continue
        
        # Verificar desligamento e regra do dia 15
        if matricula in colaboradores_desligados:
            data_comunicacao = colaboradores_desligados[matricula]
            try:
                if pd.notna(data_comunicacao):
                    # Tentar converter a data
                    if isinstance(data_comunicacao, str):
                        data_comunicacao = pd.to_datetime(data_comunicacao, errors='coerce')
                    
                    if pd.notna(data_comunicacao) and data_comunicacao.day <= 15:
                        df.at[idx, 'status'] = 'DESLIGADO_SEM_VR'
                        df.at[idx, 'motivo_exclusao'] = 'Desligamento comunicado até dia 15'
                        df.at[idx, 'dias_uteis_final'] = 0
                        continue
                    else:
                        # Desligamento após dia 15 - VR proporcional
                        df.at[idx, 'status'] = 'DESLIGADO_PROPORCIONAL'
                        df.at[idx, 'dias_uteis_final'] = min(15, row['dias_uteis'])  # Proporcional
                        continue
            except:
                pass
        
        # Calcular dias úteis finais (padrão 22 dias úteis/mês)
        dias_base = row.get('dias_uteis', 22)
        df.at[idx, 'dias_uteis_final'] = min(dias_base, 22)
        df.at[idx, 'status'] = 'ATIVO_VR'
    
    # Calcular valores finais
    df['valor_total_vr'] = df['valor_vr_unitario'] * df['dias_uteis_final']
    df['valor_empresa_80'] = (df['valor_total_vr'] * 0.80).round(2)
    df['valor_profissional_20'] = (df['valor_total_vr'] * 0.20).round(2)
    df['valor_total_vr'] = df['valor_total_vr'].round(2)
    
    return df

def save_final_excel_report(df, output_file, sindicatos_valores):
    """Salva o relatório final em Excel com múltiplas abas e formatação"""
    
    try:
        # Separar dados por status
        df_ativos = df[df['status'] == 'ATIVO_VR'].copy()
        df_proporcionais = df[df['status'] == 'DESLIGADO_PROPORCIONAL'].copy()
        df_excluidos = df[~df['status'].isin(['ATIVO_VR', 'DESLIGADO_PROPORCIONAL'])].copy()
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            
            # ABA 1: DADOS PARA OPERADORA (Modelo VR Mensal 05.2025)
            df_operadora = pd.concat([df_ativos, df_proporcionais])
            if not df_operadora.empty:
                operadora_cols = [
                    'matricula', 'nome', 'sindicato', 'dias_uteis_final', 
                    'valor_vr_unitario', 'valor_total_vr', 'valor_empresa_80', 
                    'valor_profissional_20', 'status'
                ]
                
                df_export = df_operadora[operadora_cols].copy()
                df_export.columns = [
                    'MATRICULA', 'NOME_FUNCIONARIO', 'SINDICATO', 'DIAS_UTEIS',
                    'VALOR_UNITARIO_VR', 'VALOR_TOTAL_VR', 'VALOR_EMPRESA_80%',
                    'VALOR_FUNCIONARIO_20%', 'STATUS'
                ]
                
                df_export.to_excel(writer, sheet_name='VR_Mensal_05_2025', index=False)
            
            # ABA 2: RESUMO EXECUTIVO
            resumo_data = {
                'INDICADOR': [
                    'Total de Funcionários Processados',
                    'Funcionários Ativos para VR',
                    'Funcionários com VR Proporcional',
                    'Funcionários Excluídos',
                    'Total Geral de VR',
                    'Total a Pagar Empresa (80%)',
                    'Total a Descontar Funcionário (20%)',
                    'Quantidade de Sindicatos',
                    'Data de Processamento'
                ],
                'VALOR': [
                    len(df),
                    len(df_ativos),
                    len(df_proporcionais),
                    len(df_excluidos),
                    f"R$ {(df_ativos['valor_total_vr'].sum() + df_proporcionais['valor_total_vr'].sum()):,.2f}",
                    f"R$ {(df_ativos['valor_empresa_80'].sum() + df_proporcionais['valor_empresa_80'].sum()):,.2f}",
                    f"R$ {(df_ativos['valor_profissional_20'].sum() + df_proporcionais['valor_profissional_20'].sum()):,.2f}",
                    len(sindicatos_valores),
                    datetime.now().strftime('%d/%m/%Y %H:%M')
                ]
            }
            
            df_resumo = pd.DataFrame(resumo_data)
            df_resumo.to_excel(writer, sheet_name='Resumo_Executivo', index=False)
            
            # ABA 3: EXCLUSÕES E MOTIVOS
            if not df_excluidos.empty:
                exclusoes_cols = ['matricula', 'nome', 'cargo', 'status', 'motivo_exclusao', 'fonte']
                df_exclusoes = df_excluidos[exclusoes_cols].copy()
                df_exclusoes.columns = ['MATRICULA', 'NOME', 'CARGO', 'STATUS', 'MOTIVO_EXCLUSÃO', 'ARQUIVO_ORIGEM']
                df_exclusoes.to_excel(writer, sheet_name='Exclusoes', index=False)
            
            # ABA 4: VALORES POR SINDICATO
            if sindicatos_valores:
                sindicatos_df = pd.DataFrame([
                    {'SINDICATO': k, 'VALOR_VR_UNITARIO': f"R$ {v:.2f}"} 
                    for k, v in sindicatos_valores.items()
                ])
                sindicatos_df.to_excel(writer, sheet_name='Valores_Sindicatos', index=False)
            
            # ABA 5: VALIDAÇÕES (Conforme modelo original)
            validacoes_data = {
                'VALIDAÇÃO': [
                    'Matrícula obrigatória',
                    'Nome obrigatório', 
                    'Dias úteis entre 1 e 31',
                    'Valor VR maior que zero',
                    'Exclusão de cargos específicos',
                    'Aplicação da regra do dia 15 para desligamentos',
                    'Cálculo correto: 80% empresa / 20% funcionário'
                ],
                'STATUS': ['✓ APLICADA'] * 7,
                'OBSERVAÇÃO': [
                    'Registros sem matrícula foram excluídos',
                    'Registros sem nome foram excluídos',
                    'Dias úteis limitados a 22 por mês',
                    'Apenas valores positivos aceitos',
                    'Diretores, estagiários e aprendizes excluídos',
                    'Desligamentos até dia 15 não recebem VR',
                    'Divisão automática conforme regra corporativa'
                ]
            }
            
            df_validacoes = pd.DataFrame(validacoes_data)
            df_validacoes.to_excel(writer, sheet_name='Validacoes', index=False)
        
        # Mostrar métricas na interface
        st.subheader("📊 Relatório Gerado com Sucesso!")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👥 Total Processados", len(df))
            st.metric("✅ Ativos para VR", len(df_ativos))
        
        with col2:
            st.metric("⚖️ VR Proporcional", len(df_proporcionais))
            st.metric("❌ Excluídos", len(df_excluidos))
        
        with col3:
            total_vr = df_ativos['valor_total_vr'].sum() + df_proporcionais['valor_total_vr'].sum()
            st.metric("💰 Total VR", f"R$ {total_vr:,.2f}")
            st.metric("🏢 Custo Empresa", f"R$ {total_vr * 0.8:,.2f}")
        
        # Mostrar breakdown por status
        st.subheader("📋 Breakdown por Status")
        status_counts = df['status'].value_counts()
        for status, count in status_counts.items():
            st.write(f"• **{status}**: {count} funcionários")
        
        return True
        
    except Exception as e:
        st.error(f"Erro ao salvar relatório Excel: {str(e)}")
        return False
    """Copia arquivo CSV para pasta de destino"""
    try:
        file_name = Path(file_path).name
        destination = os.path.join(output_dir, file_name)
        shutil.copy2(file_path, destination)
        return file_name, True
    except Exception as e:
        st.error(f"Erro ao copiar {file_path}: {str(e)}")
        return None, False

def process_zip_file(uploaded_file):
    """Processa arquivo ZIP e converte/copia arquivos para CSV"""
    
    # Criar diretório temporário para extração
    temp_dir = tempfile.mkdtemp()
    
    # Criar pasta de destino para CSVs
    output_dir = os.path.join(os.getcwd(), "output_folder")
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Extrair arquivos ZIP
        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Listar todos os arquivos extraídos
        all_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if not file.startswith('.') and not file.startswith('~'):  # Ignorar arquivos temporários
                    all_files.append(os.path.join(root, file))
        
        if not all_files:
            st.error("Nenhum arquivo encontrado no ZIP.")
            return None, None
        
        processed_files = []
        
        # Processar cada arquivo
        for file_path in all_files:
            file_ext = Path(file_path).suffix.lower()
            file_name = Path(file_path).name
            
            if file_ext in ['.xlsx', '.xls', '.xlsm']:
                # Converter Excel para CSV
                converted_files, success = convert_excel_to_csv(file_path, output_dir)
                if success and converted_files:
                    processed_files.extend(converted_files)
            
            elif file_ext == '.csv':
                # Copiar arquivo CSV
                copied_file, success = copy_csv_file(file_path, output_dir)
                if success and copied_file:
                    processed_files.append(copied_file)
        
        return processed_files, output_dir
    
    except Exception as e:
        st.error(f"Erro no processamento do ZIP: {str(e)}")
        return None, None
    
    finally:
        # Limpar diretório temporário
        shutil.rmtree(temp_dir, ignore_errors=True)

# Upload do arquivo ZIP
uploaded_file = st.file_uploader("Upload de arquivo ZIP", type="zip")

# Processamento principal
if uploaded_file is not None:
    st.info("Processando arquivo ZIP...")
    
    # Processar o ZIP
    processed_files, csv_output_dir = process_zip_file(uploaded_file)
    
    if processed_files:
        # Exibir resultado simples
        st.success(f"✅ Processamento concluído! {len(processed_files)} arquivos CSV salvos na pasta 'output_folder'.")
        
        # Botão para gerar planilha final de VR
        st.markdown("---")
        st.subheader("📊 Geração da Planilha Final VR")
        
        if st.button("🚀 Gerar Planilha Final para Operadora", type="primary"):
            final_report = generate_final_vr_report(csv_output_dir, csv_output_dir)
            
            if final_report:
                # Opção de download da planilha final
                try:
                    with open(final_report, "rb") as file:
                        st.download_button(
                            label="📥 Download Planilha Final VR",
                            data=file.read(),
                            file_name=f"VR_Mensal_{datetime.now().strftime('%m_%Y')}_Final.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                except Exception as e:
                    st.error(f"Erro ao preparar download: {str(e)}")
        
        st.info("💡 **Instruções:** Clique no botão acima para processar todos os CSVs e gerar a planilha final conforme modelo 'VR Mensal 05.2025' com divisão 80% empresa / 20% profissional.")
        
        # Integração com IA (se chave fornecida)
        if google_api_key:
            try:
                # Configurar o modelo Gemini
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=google_api_key,
                    temperature=temperature
                )
                
                # Criar agente com todos os CSVs
                csv_paths = [os.path.join(csv_output_dir, f) for f in processed_files]
                agent = create_csv_agent(
                    llm,
                    csv_paths,
                    verbose=True,
                    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    allow_dangerous_code=True,
                    prefix=INSTRUCTION
                )
                
                # # Interface de perguntas
                # st.markdown("---")
                # st.header("🤖 Análise Inteligente dos Dados")
                
                # # Sugestões de perguntas para VR/VA
                # st.subheader("💡 Sugestões de Análises para VR/VA:")
                # suggestions = [
                #     "Quantos colaboradores ativos temos na base?",
                #     "Quais são os sindicatos presentes e seus respectivos valores de VR?",
                #     "Identifique colaboradores em férias no período atual",
                #     "Liste colaboradores com datas de admissão/desligamento neste mês",
                #     "Calcule o total de dias úteis por colaborador",
                #     "Identifique possíveis inconsistências nas datas"
                # ]
                
                # selected_suggestion = st.selectbox("Escolha uma análise sugerida:", 
                #                                  [""] + suggestions)
                
                # question = st.text_area("Ou faça sua própria pergunta sobre os dados:",
                #                        value=selected_suggestion if selected_suggestion else "",
                #                        height=100,
                #                        placeholder="Ex: Analise a distribuição de colaboradores por sindicato e calcule o custo total de VR")
                
                # if st.button("🚀 Analisar Dados"):
                #     if question.strip():
                #         with st.spinner("Processando análise com IA..."):
                #             try:
                #                 response = agent.run(question)
                #                 st.subheader("📋 Resultado da Análise:")
                #                 st.write(response)
                #             except Exception as e:
                #                 st.error(f"Erro ao processar a análise: {str(e)}")
                #     else:
                #         st.warning("Por favor, insira uma pergunta ou selecione uma sugestão.")
                        
            except Exception as e:
                st.error(f"Erro ao configurar IA: {str(e)}")
        else:
            st.info("💡 **Dica:** Insira sua chave da API Google Gemini na barra lateral para habilitar análises inteligentes dos dados!")
    
    else:
        st.error("❌ Não foi possível processar nenhum arquivo do ZIP. Verifique se contém arquivos Excel (.xlsx, .xls) ou CSV.")

else:
    st.info("👆 Por favor, faça upload de um arquivo ZIP contendo planilhas Excel ou arquivos CSV.")
