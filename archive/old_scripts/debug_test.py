import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from create_flopy_knowledge_base import FloPyKnowledgeBuilder

# Load environment variables
load_dotenv()

async def main():
    # Get configuration from environment
    REPO_PATH = os.getenv('REPO_PATH', 'flopy')
    NEON_CONN = os.getenv('NEON_CONNECTION_STRING')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    print("Testing with flopy/version.py only...")
    
    # Build knowledge base with just one file
    builder = FloPyKnowledgeBuilder(REPO_PATH, NEON_CONN, GEMINI_API_KEY, OPENAI_API_KEY)
    
    # Get just one simple file
    test_file = Path(REPO_PATH) / 'flopy' / 'version.py'
    
    if not test_file.exists():
        print(f"Test file {test_file} does not exist")
        return
    
    print(f"Processing: {test_file}")
    
    # Extract module information
    try:
        module_info = builder.extract_module_info(test_file)
        print(f"Extracted: {module_info.relative_path} - {module_info.model_family} - {module_info.package_code}")
        print(f"Docstring: {module_info.module_docstring[:100]}...")
    except Exception as e:
        print(f"Error extracting: {e}")
        return
    
    # Analyze with Gemini
    print("Analyzing with Gemini...")
    try:
        gemini_results = await builder.analyze_modules_with_gemini([module_info])
        print(f"Gemini analysis result keys: {gemini_results[0].keys() if gemini_results else 'None'}")
        print(f"Analysis: {gemini_results[0] if gemini_results else 'None'}")
    except Exception as e:
        print(f"Error with Gemini: {e}")
        return
    
    # Test embeddings
    print("Testing OpenAI embeddings...")
    try:
        test_embedding = await builder.create_embeddings("test text")
        print(f"Embedding created: {len(test_embedding)} characters")
    except Exception as e:
        print(f"Error with embeddings: {e}")
        return
    
    print("Debug test complete!")

if __name__ == "__main__":
    asyncio.run(main())