# 📊 AI Data Explorer - Autonomous Agent with Google Gemini

## 🌟 Overview
The **AI Data Explorer** is an intelligent platform that leverages the **Gemini 2.5 Flash** model to provide autonomous, code-based data analysis. Users can upload CSV or Excel files, and the agent writes and executes Python code (`pandas`, `matplotlib`, `seaborn`) to answer complex data questions and generate visualizations.

This project uses the **LangChain** framework and **Streamlit** to create a robust and user-friendly data analysis environment.

---

## ✨ Features
* **Gemini 1.5 Flash Powered:** Optimized for speed and complex reasoning.
* **Autonomous Code Execution:** The agent writes and runs Python code within a safe, persistent environment.
* **Localization:** User interface is in **Portuguese**, while the codebase structure (variables, functions, comments) is in **English** for professional maintenance.
* **Data Visualization:** Automatically generates and displays charts (`matplotlib`/`seaborn`) based on user requests.
* **Persistent Session:** Maintains chat history and data context.

---

## 🚀 How to Use

1.  **Setup and Data Upload:**
    * Enter your **Google Gemini API Key** in the sidebar.
    * Confirm the **Model Name** is set to `gemini-2.5-flash`.
    * Click **"Escolha um arquivo CSV ou Excel"** to upload your dataset.
2.  **Initialization:**
    * Click the **"Inicializar Agente"** button. A preview of your data will be shown upon success.
3.  **Analyze with AI:**
    * Type your question in Portuguese in the chat input field (e.g., *"Qual é a média da coluna 'Valor'?"* or *"Faça um histograma da coluna 'Idade'."*).
    * The agent will execute code and return the analysis or generated chart.

---

## 🔧 Requirements
The necessary dependencies are listed in the `requirements.txt` file:

* `streamlit`
* `pandas`
* `langchain`
* `langchain-google-genai`
* `matplotlib`
* `seaborn`
* `openpyxl` (for Excel support)

---

## 🛠️ Installation
To set up and run the project locally, assuming you have Python 3.9+ installed:

1.  **Clone the Repository (Placeholder):**
    ```bash
    git clone https://github.com/brunojlle/autonomous-agents.git
    cd autonomous-agents
    ```
2.  **Create and Activate Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate 
    ```
3.  **Install Dependencies:**
    Install all required libraries using the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the Application:**
    ```bash
    streamlit run data_analyst_app.py
    ```

---

## 📝 Notes
* You will need a **Google Gemini API key** to enable the analysis features.
* The agent's internal thinking and final answer are outputted in **Portuguese**, as per the configuration in `agent_workflow.py`.
* The application creates a temporary directory `temp_charts/` to store generated visualizations.

---

## 🤝 Contributing
Contributions, issue reports, and suggestions for improvements are welcome! Please feel free to open an issue or submit a pull request.