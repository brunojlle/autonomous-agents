# 📊 CSV Analyst - Autonomous Agent with Google Gemini

## 🌟 Overview
CSV Analyst is an intelligent agent powered by Google Gemini that allows you to upload ZIP files containing CSV datasets and perform natural language queries to analyze your data. The application is hosted on Streamlit Cloud and available at https://autonomous-agents.streamlit.app/.

## ✨ Features
- ZIP File Processing: Upload ZIP archives containing multiple CSV files
- Complete Data Loading: All rows from your CSVs are loaded for comprehensive analysis
- Natural Language Interface: Ask questions about your data in plain English
- Google Gemini Integration: Advanced AI capabilities for data understanding
- Full Data Visualization: View complete datasets with row and column counts

## How to Use

1. Upload your data:
- Prepare a ZIP file containing your CSV datasets
- Click "Upload de arquivo ZIP com CSVs" to upload your file

2. View your data:
- Select a file from the dropdown to view it completely
- See total row and column counts

3. Analyze with AI:
- Enter your Google Gemini API key in the sidebar
- Type your question in the analysis section (e.g., "What are the descriptive statistics?")
- Click "Enviar Pergunta" to get insights

## 🔧 Requirements
- Python 3.10+
- Streamlit
- pandas
- langchain
- langchain-google-genai

## 🛠️ Installation
To run locally:

```bash
git clone https://github.com/brunojlle/autonomous-agents
cd autonomous-agents
pip install -r requirements.txt
streamlit run main.py
```

## 🌐 Live Demo
Try the live version at:
https://autonomous-agents.streamlit.app/

## 📝 Notes
- You'll need a Google Gemini API key to use the analysis features
- Large files may take longer to process
- The app processes all rows in your CSV files

## 🤝 Contributing
Contributions are welcome! Please open an issue or pull request for any improvements.