import asyncio
import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from create_flopy_knowledge_base import FloPyKnowledgeBuilder
import asyncpg
import hashlib

# Load environment variables
load_dotenv()

class IncrementalFloPyProcessor:
    def __init__(self):
        self.REPO_PATH = os.getenv('REPO_PATH', 'flopy')
        self.NEON_CONN = os.getenv('NEON_CONNECTION_STRING')
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        
        self.checkpoint_file = 'processor_checkpoint.json'
        self.processed_files_db = 'processed_files.json'
        
    async def setup_tracking_table(self):
        """Create a table to track processed files and their hashes"""
        conn = await asyncpg.connect(self.NEON_CONN)
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS file_processing_log (
                id SERIAL PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                last_modified TIMESTAMP,
                processed_at TIMESTAMP DEFAULT NOW(),
                status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
                error_message TEXT,
                module_id UUID REFERENCES modules(id)
            )
        ''')
        
        await conn.close()
    
    def get_file_hash(self, file_path: Path) -> str:
        """Get hash of file contents"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def load_checkpoint(self) -> Dict:
        """Load processing checkpoint"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {
            'last_processed_index': 0,
            'total_files': 0,
            'start_time': datetime.now().isoformat(),
            'completed_files': [],
            'failed_files': []
        }
    
    def save_checkpoint(self, checkpoint: Dict):
        """Save processing checkpoint"""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
    
    async def get_files_to_process(self) -> List[Path]:
        """Get list of files that need processing"""
        # Get all Python files
        all_files = list(Path(self.REPO_PATH).rglob("*.py"))
        
        # Filter out test files and other unwanted files
        filtered_files = [
            f for f in all_files 
            if 'test' not in str(f).lower() 
            and '__pycache__' not in str(f)
            and 'setup.py' not in str(f.name)
        ]
        
        # Check which files are already processed
        conn = await asyncpg.connect(self.NEON_CONN)
        
        files_to_process = []
        for file_path in filtered_files:
            try:
                current_hash = self.get_file_hash(file_path)
                
                # Check if file is in database
                row = await conn.fetchrow('''
                    SELECT file_hash, status 
                    FROM file_processing_log 
                    WHERE file_path = $1
                ''', str(file_path))
                
                if not row:
                    # New file
                    files_to_process.append(file_path)
                elif row['file_hash'] != current_hash:
                    # File has changed
                    files_to_process.append(file_path)
                elif row['status'] == 'failed':
                    # Previous processing failed
                    files_to_process.append(file_path)
                
            except Exception as e:
                print(f"Error checking {file_path}: {e}")
                files_to_process.append(file_path)
        
        await conn.close()
        
        return sorted(files_to_process)  # Sort for consistent ordering
    
    async def process_single_file(self, file_path: Path, builder: FloPyKnowledgeBuilder) -> bool:
        """Process a single file and return success status"""
        conn = await asyncpg.connect(self.NEON_CONN)
        
        try:
            # Update status to processing
            file_hash = self.get_file_hash(file_path)
            await conn.execute('''
                INSERT INTO file_processing_log (file_path, file_hash, status, last_modified)
                VALUES ($1, $2, 'processing', $3)
                ON CONFLICT (file_path) DO UPDATE SET
                    file_hash = EXCLUDED.file_hash,
                    status = 'processing',
                    last_modified = EXCLUDED.last_modified,
                    processed_at = NOW()
            ''', str(file_path), file_hash, datetime.fromtimestamp(file_path.stat().st_mtime))
            
            # Extract module info
            module_info = builder.extract_module_info(file_path)
            
            # Analyze with Gemini (with retry logic)
            gemini_results = None
            for attempt in range(3):
                try:
                    gemini_results = await builder.analyze_modules_with_gemini([module_info], batch_size=1)
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"Gemini failed after 3 attempts: {e}")
                    else:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            if not gemini_results:
                # Create minimal result if Gemini fails
                gemini_results = [{
                    'file_path': module_info.relative_path,
                    'semantic_purpose': module_info.module_docstring[:200] if module_info.module_docstring else '',
                    'user_scenarios': [],
                    'related_concepts': [],
                    'natural_language_queries': []
                }]
            
            # Store in database
            await builder.store_in_database([module_info], gemini_results)
            
            # Get the module ID
            module_id = await conn.fetchval('''
                SELECT id FROM modules WHERE file_path = $1
            ''', str(file_path))
            
            # Update status to completed
            await conn.execute('''
                UPDATE file_processing_log 
                SET status = 'completed', error_message = NULL, module_id = $1
                WHERE file_path = $2
            ''', module_id, str(file_path))
            
            await conn.close()
            return True
            
        except Exception as e:
            # Log error
            await conn.execute('''
                UPDATE file_processing_log 
                SET status = 'failed', error_message = $1
                WHERE file_path = $2
            ''', str(e)[:500], str(file_path))
            
            await conn.close()
            print(f"Error processing {file_path}: {e}")
            return False
    
    async def run(self, max_files: Optional[int] = None):
        """Run incremental processing"""
        print("=== FloPy Incremental Processor ===")
        
        # Setup tracking
        await self.setup_tracking_table()
        
        # Get files to process
        files_to_process = await self.get_files_to_process()
        
        if max_files:
            files_to_process = files_to_process[:max_files]
        
        total_files = len(files_to_process)
        print(f"Files to process: {total_files}")
        
        if total_files == 0:
            print("All files are up to date!")
            return
        
        # Load checkpoint
        checkpoint = self.load_checkpoint()
        checkpoint['total_files'] = total_files
        
        # Create builder
        builder = FloPyKnowledgeBuilder(
            self.REPO_PATH, 
            self.NEON_CONN, 
            self.GEMINI_API_KEY, 
            self.OPENAI_API_KEY
        )
        
        # Process files
        success_count = 0
        fail_count = 0
        
        for i, file_path in enumerate(files_to_process):
            print(f"\n[{i+1}/{total_files}] Processing: {file_path.relative_to(Path(self.REPO_PATH))}")
            
            success = await self.process_single_file(file_path, builder)
            
            if success:
                success_count += 1
                checkpoint['completed_files'].append(str(file_path))
                print(f"  ✓ Success")
            else:
                fail_count += 1
                checkpoint['failed_files'].append(str(file_path))
                print(f"  ✗ Failed")
            
            # Save checkpoint every 10 files
            if (i + 1) % 10 == 0:
                checkpoint['last_processed_index'] = i + 1
                self.save_checkpoint(checkpoint)
                print(f"\nCheckpoint saved. Progress: {i+1}/{total_files}")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(1)
        
        # Final checkpoint
        checkpoint['last_processed_index'] = total_files
        checkpoint['end_time'] = datetime.now().isoformat()
        self.save_checkpoint(checkpoint)
        
        print(f"\n=== Processing Complete ===")
        print(f"Success: {success_count}")
        print(f"Failed: {fail_count}")
        print(f"Total: {total_files}")
    
    async def get_status(self):
        """Get current processing status"""
        conn = await asyncpg.connect(self.NEON_CONN)
        
        stats = await conn.fetchrow('''
            SELECT 
                COUNT(*) as total_files,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending
            FROM file_processing_log
        ''')
        
        recent_failures = await conn.fetch('''
            SELECT file_path, error_message, processed_at
            FROM file_processing_log
            WHERE status = 'failed'
            ORDER BY processed_at DESC
            LIMIT 10
        ''')
        
        await conn.close()
        
        print("=== Processing Status ===")
        print(f"Total files tracked: {stats['total_files']}")
        print(f"Completed: {stats['completed']}")
        print(f"Failed: {stats['failed']}")
        print(f"Processing: {stats['processing']}")
        print(f"Pending: {stats['pending']}")
        
        if recent_failures:
            print("\nRecent failures:")
            for failure in recent_failures:
                print(f"  - {Path(failure['file_path']).name}: {failure['error_message'][:50]}...")


async def main():
    processor = IncrementalFloPyProcessor()
    
    # Check if we want status or processing
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        await processor.get_status()
    else:
        # Process files (limit to 50 for testing)
        await processor.run(max_files=50)


if __name__ == "__main__":
    asyncio.run(main())