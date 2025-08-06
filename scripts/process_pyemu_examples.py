#!/usr/bin/env python3
"""
Process PyEmu EXAMPLES (notebooks/tutorials)
Extracts uncertainty analysis patterns from example notebooks
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

import config
from pyemu_workflow_processor import PyEmuWorkflowProcessor

async def main():
    """Process PyEmu example notebooks"""
    
    print("📊 PyEmu EXAMPLES Processing")
    print("=" * 50)
    print("Processing: Uncertainty Analysis Notebooks")
    print("Directory: /home/danilopezmella/flopy_expert/pyemu/examples")
    print()
    
    processor = PyEmuWorkflowProcessor(
        examples_path="/home/danilopezmella/flopy_expert/pyemu/examples",
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY
    )
    
    await processor.process_all_workflows()

if __name__ == "__main__":
    asyncio.run(main())