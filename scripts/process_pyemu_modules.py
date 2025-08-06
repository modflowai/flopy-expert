#!/usr/bin/env python3
"""
Process PyEmu MODULES (packages, functions, classes)
Creates searchable database of PyEmu API for uncertainty analysis
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import config
from src.pyemu_processing_pipeline import PyEMUProcessor

async def main():
    """Process PyEmu modules/API documentation"""
    
    print("🎯 PyEmu MODULES Processing")
    print("=" * 50)
    print("Processing: Uncertainty Analysis & PEST Tools")
    print("Repository: /home/danilopezmella/flopy_expert/pyemu")
    print()
    
    processor = PyEMUProcessor(
        repo_path="/home/danilopezmella/flopy_expert/pyemu",
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY,
        batch_size=config.BATCH_SIZE,
        gemini_model=config.GEMINI_MODEL
    )
    
    await processor.process_all()

if __name__ == "__main__":
    asyncio.run(main())