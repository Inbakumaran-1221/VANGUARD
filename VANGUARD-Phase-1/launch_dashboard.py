#!/usr/bin/env python3
"""Launch Streamlit dashboard with correct Python path"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Set environment for Streamlit
os.environ['PYTHONPATH'] = str(project_root)

# Launch dashboard
if __name__ == "__main__":
    import streamlit.cli
    sys.argv = ["streamlit", "run", str(project_root / "src" / "dashboard.py")]
    streamlit.cli.main()
