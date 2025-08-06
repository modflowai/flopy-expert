#!/usr/bin/env python3
"""
Process FloPy EXAMPLES (tutorials/workflows)
Extracts modeling patterns from jupyter notebooks
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import config
from src.flopy_workflow_processor import WorkflowProcessor

async def main():
    """Process FloPy tutorial examples/workflows"""
    
    print("📚 FloPy EXAMPLES Processing")
    print("=" * 50)
    print("Processing: Tutorial Notebooks & Workflows")
    print("Directory: /home/danilopezmella/flopy_expert/flopy/.docs/Notebooks")
    print()
    
    processor = WorkflowProcessor(
        tutorials_path="/home/danilopezmella/flopy_expert/flopy/.docs/Notebooks",
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY
    )
    
    await processor.process_all_workflows()

if __name__ == "__main__":
    asyncio.run(main())