#!/usr/bin/env python3
"""
Shared MODFLOW-2005 configuration for test examples
"""
from pathlib import Path

MF2005_PATH = Path("/home/danilopezmella/flopy_expert/bin/mf2005")

def get_mf2005_exe():
    """Get MODFLOW-2005 executable path"""
    if not MF2005_PATH.exists():
        raise FileNotFoundError(f"MODFLOW-2005 not found at {MF2005_PATH}")
    return str(MF2005_PATH)

def check_mf2005_available():
    """Check if MODFLOW-2005 is available"""
    return MF2005_PATH.exists()