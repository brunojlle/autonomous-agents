# tools/analysis_tools.py

import pandas as pd
from langchain.tools import tool
from io import StringIO
import sys
import os
import matplotlib
# Set the Matplotlib backend to 'Agg' to prevent GUI issues in non-interactive environments
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import traceback

# Define a persistent scope for code execution
_global_code_scope = {}

@tool
def code_execution_tool(code: str) -> str:
    """
    Executes Python code to explore and analyze data within a Pandas DataFrame.
    The DataFrame is available as the variable `df`. Use `print()` to return results.
    Example: print(df.info())
    """
    global _global_code_scope

    # Clear the state of any previous plot to prevent plot overlap
    if 'plt' in _global_code_scope:
        _global_code_scope['plt'].clf()

    # Clean up input code to remove potential markdown formatting (```python or ```)
    cleaned_code = code.strip()
    if cleaned_code.startswith("```python"):
        cleaned_code = cleaned_code[9:]
    elif cleaned_code.startswith("```"):
        cleaned_code = cleaned_code[3:]

    if cleaned_code.endswith("```"):
        cleaned_code = cleaned_code[:-3]

    cleaned_code = cleaned_code.strip()

    try:
        # Redirect standard output (stdout) to capture prints
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        # Execute the code in the persistent scope
        exec(cleaned_code, _global_code_scope)

        # Restore standard output
        sys.stdout = old_stdout
        output = captured_output.getvalue()

        if output:
            return f"Execution successful. Output:\n```\n{output}\n```"
        else:
            return "Code executed successfully, but produced no output. Use the `print()` function to surface results."

    except Exception:
        # Restore standard output in case of error
        sys.stdout = old_stdout
        # Capture the full traceback and return it as a formatted string
        error_trace = traceback.format_exc()
        return f"Error executing code. Details:\n```\n{error_trace}\n```"

def setup_analysis_tools(dataframe: pd.DataFrame):
    """
    Helper function that sets up and configures the tools for the agent.
    """
    # Initialize the scope with the DataFrame and libraries
    global _global_code_scope
    _global_code_scope = {
        'df': dataframe,
        'pd': pd,
        'plt': plt,
        'sns': sns
    }
    # Ensure the directory for saving charts exists.
    if not os.path.exists("charts"):
        os.makedirs("charts")

    # Return the list of tools
    return [code_execution_tool]