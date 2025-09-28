# agent_workflow.py

# Import necessary libraries and modules
import pandas as pd
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI 

# Import custom tools from the local module
from tools.analysis_tools import setup_analysis_tools 

# Renamed the main function
def create_data_analysis_workflow(dataframe: pd.DataFrame, api_key: str, model_name: str):
    """
    Creates and compiles the ReAct agent workflow for data analysis,
    exclusively using the Gemini model.

    Args:
        dataframe: The Pandas DataFrame the agent will analyze.
        api_key: The API key for the selected provider (Gemini).
        model_name: The model name (e.g., gemini-1.5-flash).

    Returns:
        A configured AgentExecutor ready for use, or an Exception upon failure.
    """
    llm = None
    try:
        # Safety settings to prevent API response blocking
        try:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety_settings = {
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        except ImportError:
            # Fallback for environments where google-generativeai types aren't available
            safety_settings = { 10: 4 } 

        # 1. Language Model Instance (Gemini)
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0,
            convert_system_message_to_human=True,
            safety_settings=safety_settings
        )
    except Exception as e:
        # Return the exception to be displayed in the UI
        return e

    # 2. Create the list of tools available to the agent
    tools = setup_analysis_tools(dataframe)

    # 3. Pull the base prompt for a ReAct chat agent
    prompt = hub.pull("hwchase17/react-chat")

    # 4. Custom instructions for the prompt (Content translated to Portuguese)
    prompt.template = """
Você é um Cientista de Dados Sênior altamente qualificado, operando com o modelo Gemini. Sua única responsabilidade é analisar o DataFrame Pandas chamado `df` com base na solicitação do usuário. Todo o seu raciocínio interno e sua resposta final DEVEM ser em **Português**.

**DIRETRIZES PARA EXECUÇÃO:**

1.  **Uso de Ferramentas (Obrigatório):** Para qualquer pergunta relacionada ao conteúdo, estrutura ou estatísticas dos dados, você **DEVE** usar a ferramenta `code_execution_tool`. Não use conhecimento prévio para inferir insights sobre os dados.
2.  **Saída do Código:** Todo código executado através da ferramenta **DEVE** usar a função Python `print()` para exibir os resultados na seção `Observation`.
3.  **Histórico de Chat:** Use o `Chat History` para manter o contexto e construir sobre os passos de análise anteriores.
4.  **Limite de Iteração:** Você tem um máximo de **7 passos** (ciclos Thought/Action/Observation) para chegar à conclusão definitiva. Se a resposta estiver clara antes do limite, prossiga para a `Final Answer`.

**VISUALIZAÇÃO E PLOTAGEM (Protocolo Estrito):**

* **Bibliotecas:** Use `matplotlib.pyplot` (`plt`) e/ou `seaborn` (`sns`).
* **Salvamento:** **SEMPRE** salve o gráfico no diretório temporário: `plt.savefig('charts/nome_unico_do_grafico.png')`. **NUNCA** use `plt.show()`.
* **Relatório:** Para exibir o gráfico na saída final, inclua a tag especial: **`[CHART_PATH:charts/caminho_para_o_grafico.png]`** dentro da sua `Final Answer`.

Use o seguinte formato ReAct estrito, garantindo que as palavras-chave estejam em **Inglês**:

Question: A pergunta de entrada do usuário
Thought: Seu processo de raciocínio interno (em Português)
Action: A ferramenta a ser invocada, deve ser uma de [{tool_names}]
Action Input: O código Python puro para a ação. **CRÍTICO**: NÃO inclua formatação de markdown como ```python ou ```.
Observation: O resultado da ferramenta
... (Este ciclo se repete até 7 vezes)
Thought: Tenho informações suficientes para fornecer a resposta final.
Final Answer: A resposta definitiva para a pergunta original (em Português), incluindo a tag do caminho do gráfico, se um gráfico foi gerado.

Comece!

Chat History:
{chat_history}

Question: {input}
Thought:{agent_scratchpad}
"""

    # 5. Create the ReAct agent
    agent = create_react_agent(llm, tools, prompt)

    # 6. Create the Agent Executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True, # Handles parsing errors, giving the agent a chance to correct itself.
        return_intermediate_steps=True,
        max_iterations=7, # Increased iterations for better complexity handling
        early_stopping_method="force",
    )

    return agent_executor