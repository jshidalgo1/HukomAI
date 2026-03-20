import sys
import os
from streamlit.web import cli as stcli

if __name__ == "__main__":
    # Ensure the root directory is in the path so 'src' can be imported
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Run the streamlit app located in src/app/app.py
    sys.argv = [
        "streamlit",
        "run",
        os.path.join("src", "app", "app.py"),
        *sys.argv[1:],
    ]
    sys.exit(stcli.main())
