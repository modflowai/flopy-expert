#!/usr/bin/env python3
"""
Process MFUSG modules that were missed in the original processing.
This will add SMS and other MODFLOW-USG modules to the database.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
import hashlib
from datetime import datetime
import ast
import re
import subprocess

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import config
import psycopg2
import google.genai as genai
from openai import AsyncOpenAI


@dataclass
class ModuleInfo:
    """Information about a FloPy module"""
    file_path: str
    relative_path: str
    model_family: str
    package_code: str
    module_docstring: str
    source_code: str
    classes: List[str]
    functions: List[str]
    file_hash: str
    last_modified: datetime
    git_commit_hash: str = None
    git_branch: str = None
    git_commit_date: datetime = None


class MFUSGProcessor:
    def __init__(self):
        self.gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.conn_string = config.NEON_CONNECTION_STRING
        self.repo_path = Path('/home/danilopezmella/flopy_expert/flopy')
        
    def get_git_info(self) -> Dict[str, Any]:
        """Get current git information"""
        try:
            cwd = self.repo_path
            commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd).decode().strip()
            branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=cwd).decode().strip()
            commit_date = subprocess.check_output(['git', 'show', '-s', '--format=%ci', 'HEAD'], cwd=cwd).decode().strip()
            commit_date = datetime.fromisoformat(commit_date.replace(' +', '+').replace(' -', '-'))
            
            return {
                'commit_hash': commit_hash,
                'branch': branch,
                'commit_date': commit_date
            }
        except:
            return {'commit_hash': None, 'branch': None, 'commit_date': None}
    
    def extract_module_info(self, file_path: Path) -> ModuleInfo:
        """Extract information from a Python module"""
        content = file_path.read_text(encoding='utf-8')
        relative_path = str(file_path.relative_to(self.repo_path))
        
        # Parse AST
        tree = ast.parse(content)
        
        # Extract docstring
        module_docstring = ast.get_docstring(tree) or ""
        
        # Extract classes and functions
        classes = []
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef) and node.name not in ['__init__', '__repr__', '__str__']:
                functions.append(node.name)
        
        # Extract package code from class names or file name
        package_code = None
        file_stem = file_path.stem.upper()
        
        # Try to extract from class names
        for class_name in classes:
            if class_name.startswith('MfUsg'):
                code = class_name[5:].upper()  # Remove MfUsg prefix
                if len(code) >= 2 and len(code) <= 4:
                    package_code = code
                    break
        
        # Fallback to file name
        if not package_code and file_stem.startswith('MFUSG'):
            package_code = file_stem[5:]
        elif not package_code:
            package_code = file_stem
        
        # Get git info
        git_info = self.get_git_info()
        
        return ModuleInfo(
            file_path=str(file_path),
            relative_path=relative_path,
            model_family='mfusg',
            package_code=package_code,
            module_docstring=module_docstring,
            source_code=content[:5000],  # First 5000 chars
            classes=classes,
            functions=functions,
            file_hash=hashlib.sha256(content.encode()).hexdigest(),
            last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
            git_commit_hash=git_info['commit_hash'],
            git_branch=git_info['branch'],
            git_commit_date=git_info['commit_date']
        )
    
    async def analyze_with_gemini(self, module_info: ModuleInfo) -> Dict[str, Any]:
        """Use Gemini to analyze module semantics"""
        prompt = f"""
Analyze this MODFLOW-USG (Unstructured Grid) Python module and provide detailed semantic understanding.

Module: {module_info.relative_path}
Package Code: {module_info.package_code}
Classes: {', '.join(module_info.classes[:5])}
Functions: {', '.join(module_info.functions[:5])}

Module Docstring:
{module_info.module_docstring[:1000]}

Source Code Sample:
{module_info.source_code[:2000]}

Provide analysis in this format:

## Purpose
Describe the primary purpose and functionality of this module in the context of MODFLOW-USG groundwater modeling. What specific aspect of unstructured grid modeling does it handle?

## User Scenarios  
List 3-5 specific scenarios when a user would need this module:
- Scenario 1
- Scenario 2
- Scenario 3

## Related Concepts
List 3-5 related MODFLOW-USG concepts or packages:
- Related concept 1
- Related concept 2
- Related concept 3

## Typical Errors
List 3-5 common errors or issues users might encounter:
- Error 1
- Error 2
- Error 3

Focus on MODFLOW-USG specific features like unstructured grids, connected linear networks, and advanced solver capabilities.
"""
        
        try:
            response = await asyncio.to_thread(
                self.gemini_client.models.generate_content,
                model="gemini-2.5-pro",
                contents=prompt
            )
            
            text = response.text
            
            # Extract sections
            purpose_match = re.search(r'## Purpose\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
            purpose = purpose_match.group(1).strip() if purpose_match else ""
            
            scenarios_match = re.search(r'## User Scenarios\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
            scenarios = []
            if scenarios_match:
                scenarios_text = scenarios_match.group(1)
                scenarios = [line.strip()[2:].strip() for line in scenarios_text.split('\n') 
                           if line.strip().startswith('- ')]
            
            concepts_match = re.search(r'## Related Concepts\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
            concepts = []
            if concepts_match:
                concepts_text = concepts_match.group(1)
                concepts = [line.strip()[2:].strip() for line in concepts_text.split('\n') 
                          if line.strip().startswith('- ')]
            
            errors_match = re.search(r'## Typical Errors\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
            errors = []
            if errors_match:
                errors_text = errors_match.group(1)
                errors = [line.strip()[2:].strip() for line in errors_text.split('\n') 
                         if line.strip().startswith('- ')]
            
            return {
                'semantic_purpose': purpose,
                'user_scenarios': scenarios,
                'related_concepts': concepts,
                'typical_errors': errors
            }
            
        except Exception as e:
            print(f"Gemini analysis failed: {e}")
            # Fallback analysis
            return {
                'semantic_purpose': f"MODFLOW-USG {module_info.package_code} package for unstructured grid modeling. {module_info.module_docstring[:200]}",
                'user_scenarios': ["Unstructured grid modeling", "MODFLOW-USG simulations"],
                'related_concepts': ["MODFLOW-USG", "Unstructured grids", module_info.package_code],
                'typical_errors': ["Configuration errors", "Grid setup issues"]
            }
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding using OpenAI"""
        response = await self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    async def process_module(self, file_path: Path) -> bool:
        """Process a single MFUSG module"""
        try:
            # Extract module info
            module_info = self.extract_module_info(file_path)
            print(f"  Processing {module_info.relative_path}...")
            
            # Analyze with Gemini
            analysis = await self.analyze_with_gemini(module_info)
            
            # Create embedding text
            embedding_parts = [
                f"{module_info.package_code} {module_info.model_family}",
                module_info.module_docstring[:500],
                analysis['semantic_purpose'],
                ' '.join(analysis['user_scenarios']),
                ' '.join(analysis['related_concepts'])
            ]
            embedding_text = ' '.join(filter(None, embedding_parts))
            
            # Create embedding
            embedding = await self.create_embedding(embedding_text)
            
            # Save to database
            with psycopg2.connect(self.conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO flopy_modules (
                            id, file_path, relative_path, model_family, package_code,
                            module_docstring, source_code, semantic_purpose,
                            user_scenarios, related_concepts, typical_errors,
                            embedding_text, embedding, file_hash, last_modified,
                            git_commit_hash, git_branch, git_commit_date
                        ) VALUES (
                            gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (file_path) DO UPDATE SET
                            package_code = EXCLUDED.package_code,
                            semantic_purpose = EXCLUDED.semantic_purpose,
                            user_scenarios = EXCLUDED.user_scenarios,
                            related_concepts = EXCLUDED.related_concepts,
                            typical_errors = EXCLUDED.typical_errors,
                            embedding_text = EXCLUDED.embedding_text,
                            embedding = EXCLUDED.embedding,
                            file_hash = EXCLUDED.file_hash,
                            last_modified = EXCLUDED.last_modified,
                            processed_at = NOW()
                    """, (
                        module_info.file_path,
                        module_info.relative_path,
                        module_info.model_family,
                        module_info.package_code,
                        module_info.module_docstring,
                        module_info.source_code,
                        analysis['semantic_purpose'],
                        analysis['user_scenarios'],
                        analysis['related_concepts'],
                        analysis['typical_errors'],
                        embedding_text,
                        embedding,
                        module_info.file_hash,
                        module_info.last_modified,
                        module_info.git_commit_hash,
                        module_info.git_branch,
                        module_info.git_commit_date
                    ))
                    conn.commit()
                    print(f"    ✓ Saved {module_info.package_code}")
                    return True
                    
        except Exception as e:
            print(f"    ✗ Error: {e}")
            return False


async def process_mfusg_modules():
    """Process all MFUSG modules"""
    # Get all Python files in mfusg directory
    mfusg_path = Path('/home/danilopezmella/flopy_expert/flopy/flopy/mfusg')
    mfusg_files = list(mfusg_path.glob('*.py'))
    
    # Filter out __init__.py and test files
    mfusg_files = [
        f for f in mfusg_files 
        if f.name != '__init__.py' and not f.name.startswith('test_')
    ]
    
    print(f"Found {len(mfusg_files)} MFUSG modules to process:")
    for f in sorted(mfusg_files):
        print(f"  - {f.name}")
    
    print("\nStarting processing...")
    print("-" * 60)
    
    # Initialize processor
    processor = MFUSGProcessor()
    
    # Process each module
    total_success = 0
    total_failed = 0
    
    for file_path in mfusg_files:
        success = await processor.process_module(file_path)
        if success:
            total_success += 1
        else:
            total_failed += 1
        
        # Small delay to avoid API rate limits
        await asyncio.sleep(2)
    
    print("\n" + "=" * 60)
    print(f"✅ MFUSG Processing Complete!")
    print(f"   Successful: {total_success}")
    print(f"   Failed: {total_failed}")
    print(f"   Total: {len(mfusg_files)}")
    
    # Verify SMS was processed
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT relative_path, package_code, LEFT(semantic_purpose, 100) as purpose
                FROM flopy_modules 
                WHERE relative_path LIKE '%sms%' AND model_family = 'mfusg'
            """)
            sms_result = cur.fetchone()
            
            if sms_result:
                print(f"\n✅ SMS Module successfully added:")
                print(f"   Path: {sms_result[0]}")
                print(f"   Code: {sms_result[1]}")
                print(f"   Purpose: {sms_result[2]}...")
            else:
                print("\n⚠️  Warning: SMS module not found after processing")


async def main():
    await process_mfusg_modules()


if __name__ == "__main__":
    asyncio.run(main())