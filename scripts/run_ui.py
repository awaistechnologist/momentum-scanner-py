#!/usr/bin/env python3
"""Launcher script for Streamlit UI that sets up Python path."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now run Streamlit
if __name__ == "__main__":
    import streamlit.web.cli as stcli
    import sys

    # Point to the UI app
    ui_app_path = project_root / "scanner" / "modes" / "ui_app.py"

    sys.argv = ["streamlit", "run", str(ui_app_path)]
    sys.exit(stcli.main())
