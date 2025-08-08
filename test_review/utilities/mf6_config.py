"""
Shared MODFLOW 6 configuration for all test examples
"""

import os
from pathlib import Path

# Path to MODFLOW 6 executable
MF6_PATH = Path("/home/danilopezmella/flopy_expert/bin/mf6")

# Make sure it's executable
if MF6_PATH.exists():
    os.chmod(MF6_PATH, 0o755)

def get_mf6_exe():
    """Get the path to MODFLOW 6 executable"""
    if not MF6_PATH.exists():
        raise FileNotFoundError(f"MODFLOW 6 not found at {MF6_PATH}")
    return str(MF6_PATH)