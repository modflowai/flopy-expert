#!/usr/bin/env python3
"""
Process FloPy MODULES (packages, functions, classes)
Creates searchable database of FloPy API documentation
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import config
from src.flopy_processing_pipeline import FloPyProcessor

async def main():
    """Process FloPy modules/API documentation"""
    
    print("📦 FloPy MODULES Processing")
    print("=" * 50)
    print("Processing: Packages, Functions, Classes")
    print("Repository: /home/danilopezmella/flopy_expert/flopy")
    print()
    
    processor = FloPyProcessor(
        repo_path="/home/danilopezmella/flopy_expert/flopy",
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY,
        batch_size=config.BATCH_SIZE,
        gemini_model=config.GEMINI_MODEL
    )
    
    await processor.process_all()

if __name__ == "__main__":
    asyncio.run(main())