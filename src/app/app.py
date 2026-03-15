import sys
import os
from streamlit.web import cli as stcli

if __name__ == "__main__":
    # Ensure the src directory is in the path so internal imports work
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
    
    sys.argv = [
        "streamlit",
        "run",
        os.path.join("src", "app", "app.py"),
        *sys.argv[1:],
    ]
    sys.exit(stcli.main())