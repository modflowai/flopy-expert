#!/usr/bin/env python3
"""
PyEMU V02 Embedding Pipeline Runner

Entry point for running the professional PyEMU v02 embedding pipeline.
Follows established codebase patterns for root-level entry points.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

import config
from src.pyemu_embedding_pipeline import PyEMUEmbeddingPipelineV02


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="PyEMU Ultra-Discriminative Embedding Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_embedding_pyemu.py
  python run_embedding_pyemu.py --batch-size 3
        """
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of workflows to process per batch (default: 5)"
    )
    
    parser.add_argument(
        "--gemini-model",
        default="gemini-2.0-flash-exp",
        help="Gemini model for analysis generation (default: gemini-2.0-flash-exp)"
    )
    
    parser.add_argument(
        "--openai-model", 
        default="text-embedding-3-small",
        help="OpenAI model for embeddings (default: text-embedding-3-small)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("PYEMU ULTRA-DISCRIMINATIVE EMBEDDING PIPELINE")
    print("=" * 80)
    print(f"Batch Size: {args.batch_size}")
    print(f"Gemini Model: {args.gemini_model}")
    print(f"OpenAI Model: {args.openai_model}")
    print("=" * 80)
    
    try:
        # Create and run pipeline
        pipeline = PyEMUEmbeddingPipelineV02(
            neon_conn_string=config.NEON_CONNECTION_STRING,
            gemini_api_key=config.GEMINI_API_KEY,
            openai_api_key=config.OPENAI_API_KEY,
            batch_size=args.batch_size,
            gemini_model=args.gemini_model,
            openai_model=args.openai_model
        )
        
        await pipeline.run_pipeline()
        
        print("\n" + "=" * 80)
        print("✅ PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n⚠️ Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())