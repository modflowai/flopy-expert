#!/usr/bin/env python3
"""
Quality Assessment for FloPy and PyEmu Embeddings

Identifies modules and workflows with poor quality embeddings that need reprocessing.
"""
import sys
sys.path.append('/home/danilopezmella/flopy_expert')
import config
import psycopg2
from datetime import datetime
from typing import List, Tuple, Dict


class EmbeddingQualityChecker:
    """Check embedding quality across all tables"""
    
    def __init__(self, conn_string: str):
        self.conn_string = conn_string
        
        # Quality thresholds
        self.FLOPY_MODULE_MIN_EMBED = 500      # FloPy modules should have >500 chars
        self.PYEMU_MODULE_MIN_EMBED = 500      # PyEmu modules should have >500 chars
        self.FLOPY_WORKFLOW_MIN_EMBED = 1000   # FloPy workflows should have >1000 chars
        self.PYEMU_WORKFLOW_MIN_EMBED = 1000   # PyEmu workflows should have >1000 chars
        
    def check_flopy_modules(self) -> List[Dict]:
        """Check FloPy module embedding quality"""
        with psycopg2.connect(self.conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        relative_path,
                        package_code,
                        LENGTH(embedding_text) as embed_len,
                        semantic_purpose,
                        processed_at
                    FROM flopy_modules
                    WHERE LENGTH(embedding_text) < %s
                    ORDER BY LENGTH(embedding_text)
                """, (self.FLOPY_MODULE_MIN_EMBED,))
                
                results = []
                for row in cur.fetchall():
                    id, path, package, embed_len, purpose, processed_at = row
                    results.append({
                        'id': id,
                        'path': path,
                        'package': package,
                        'embed_len': embed_len,
                        'has_purpose': bool(purpose and len(purpose) > 100),
                        'processed_at': processed_at
                    })
                
                return results
    
    def check_pyemu_modules(self) -> List[Dict]:
        """Check PyEmu module embedding quality"""
        with psycopg2.connect(self.conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        relative_path,
                        module_name,
                        LENGTH(embedding_text) as embed_len,
                        semantic_purpose,
                        processed_at
                    FROM pyemu_modules
                    WHERE LENGTH(embedding_text) < %s
                    ORDER BY LENGTH(embedding_text)
                """, (self.PYEMU_MODULE_MIN_EMBED,))
                
                results = []
                for row in cur.fetchall():
                    id, path, module, embed_len, purpose, processed_at = row
                    results.append({
                        'id': id,
                        'path': path,
                        'module': module,
                        'embed_len': embed_len,
                        'has_purpose': bool(purpose and len(purpose) > 100),
                        'processed_at': processed_at
                    })
                
                return results
    
    def check_flopy_workflows(self) -> List[Dict]:
        """Check FloPy workflow embedding quality"""
        with psycopg2.connect(self.conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        tutorial_file,
                        title,
                        LENGTH(embedding_text) as embed_len,
                        workflow_purpose,
                        best_use_cases,
                        processed_at
                    FROM flopy_workflows
                    WHERE LENGTH(embedding_text) < %s
                    ORDER BY LENGTH(embedding_text)
                """, (self.FLOPY_WORKFLOW_MIN_EMBED,))
                
                results = []
                for row in cur.fetchall():
                    id, file, title, embed_len, purpose, use_cases, processed_at = row
                    results.append({
                        'id': id,
                        'file': file,
                        'title': title,
                        'embed_len': embed_len,
                        'has_purpose': bool(purpose and len(purpose) > 100),
                        'has_use_cases': bool(use_cases and len(use_cases) > 0),
                        'processed_at': processed_at
                    })
                
                return results
    
    def check_pyemu_workflows(self) -> List[Dict]:
        """Check PyEmu workflow embedding quality"""
        with psycopg2.connect(self.conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        notebook_file,
                        title,
                        LENGTH(embedding_text) as embed_len,
                        workflow_purpose,
                        best_practices,
                        processed_at
                    FROM pyemu_workflows
                    WHERE LENGTH(embedding_text) < %s
                    ORDER BY LENGTH(embedding_text)
                """, (self.PYEMU_WORKFLOW_MIN_EMBED,))
                
                results = []
                for row in cur.fetchall():
                    id, file, title, embed_len, purpose, practices, processed_at = row
                    results.append({
                        'id': id,
                        'file': file,
                        'title': title,
                        'embed_len': embed_len,
                        'has_purpose': bool(purpose and len(purpose) > 100),
                        'has_practices': bool(practices and len(practices) > 0),
                        'processed_at': processed_at
                    })
                
                return results
    
    def get_statistics(self) -> Dict:
        """Get overall statistics for all tables"""
        with psycopg2.connect(self.conn_string) as conn:
            with conn.cursor() as cur:
                stats = {}
                
                # FloPy modules
                cur.execute("""
                    SELECT 
                        COUNT(*),
                        AVG(LENGTH(embedding_text)),
                        MIN(LENGTH(embedding_text)),
                        MAX(LENGTH(embedding_text))
                    FROM flopy_modules
                """)
                count, avg, min_len, max_len = cur.fetchone()
                stats['flopy_modules'] = {
                    'total': count,
                    'avg_embed_len': int(avg) if avg else 0,
                    'min_embed_len': min_len or 0,
                    'max_embed_len': max_len or 0
                }
                
                # PyEmu modules
                cur.execute("""
                    SELECT 
                        COUNT(*),
                        AVG(LENGTH(embedding_text)),
                        MIN(LENGTH(embedding_text)),
                        MAX(LENGTH(embedding_text))
                    FROM pyemu_modules
                """)
                count, avg, min_len, max_len = cur.fetchone()
                stats['pyemu_modules'] = {
                    'total': count,
                    'avg_embed_len': int(avg) if avg else 0,
                    'min_embed_len': min_len or 0,
                    'max_embed_len': max_len or 0
                }
                
                # FloPy workflows
                cur.execute("""
                    SELECT 
                        COUNT(*),
                        AVG(LENGTH(embedding_text)),
                        MIN(LENGTH(embedding_text)),
                        MAX(LENGTH(embedding_text))
                    FROM flopy_workflows
                """)
                count, avg, min_len, max_len = cur.fetchone()
                stats['flopy_workflows'] = {
                    'total': count,
                    'avg_embed_len': int(avg) if avg else 0,
                    'min_embed_len': min_len or 0,
                    'max_embed_len': max_len or 0
                }
                
                # PyEmu workflows
                cur.execute("""
                    SELECT 
                        COUNT(*),
                        AVG(LENGTH(embedding_text)),
                        MIN(LENGTH(embedding_text)),
                        MAX(LENGTH(embedding_text))
                    FROM pyemu_workflows
                """)
                count, avg, min_len, max_len = cur.fetchone()
                stats['pyemu_workflows'] = {
                    'total': count,
                    'avg_embed_len': int(avg) if avg else 0,
                    'min_embed_len': min_len or 0,
                    'max_embed_len': max_len or 0
                }
                
                return stats
    
    def print_report(self):
        """Print comprehensive quality report"""
        print("=" * 80)
        print("EMBEDDING QUALITY ASSESSMENT REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Overall statistics
        stats = self.get_statistics()
        print("OVERALL STATISTICS:")
        print("-" * 40)
        for table, table_stats in stats.items():
            print(f"\n{table.upper()}:")
            print(f"  Total records: {table_stats['total']}")
            print(f"  Average embedding: {table_stats['avg_embed_len']} chars")
            print(f"  Range: {table_stats['min_embed_len']} - {table_stats['max_embed_len']} chars")
        
        # Poor quality items
        print("\n\nPOOR QUALITY EMBEDDINGS NEEDING REPROCESSING:")
        print("=" * 80)
        
        # FloPy modules
        flopy_modules = self.check_flopy_modules()
        print(f"\nFLOPY MODULES (threshold: {self.FLOPY_MODULE_MIN_EMBED} chars):")
        print("-" * 40)
        if flopy_modules:
            for item in flopy_modules[:10]:  # Show top 10
                print(f"  {item['path']} ({item['package']})")
                print(f"    Embedding: {item['embed_len']} chars")
                print(f"    Has purpose: {item['has_purpose']}")
                print(f"    Processed: {item['processed_at']}")
            if len(flopy_modules) > 10:
                print(f"  ... and {len(flopy_modules) - 10} more")
            print(f"\n  TOTAL TO REPROCESS: {len(flopy_modules)}")
        else:
            print("  ✅ All FloPy modules have good embeddings!")
        
        # PyEmu modules
        pyemu_modules = self.check_pyemu_modules()
        print(f"\n\nPYEMU MODULES (threshold: {self.PYEMU_MODULE_MIN_EMBED} chars):")
        print("-" * 40)
        if pyemu_modules:
            for item in pyemu_modules[:10]:
                print(f"  {item['path']} ({item['module']})")
                print(f"    Embedding: {item['embed_len']} chars")
                print(f"    Has purpose: {item['has_purpose']}")
                print(f"    Processed: {item['processed_at']}")
            if len(pyemu_modules) > 10:
                print(f"  ... and {len(pyemu_modules) - 10} more")
            print(f"\n  TOTAL TO REPROCESS: {len(pyemu_modules)}")
        else:
            print("  ✅ All PyEmu modules have good embeddings!")
        
        # FloPy workflows
        flopy_workflows = self.check_flopy_workflows()
        print(f"\n\nFLOPY WORKFLOWS (threshold: {self.FLOPY_WORKFLOW_MIN_EMBED} chars):")
        print("-" * 40)
        if flopy_workflows:
            for item in flopy_workflows[:10]:
                print(f"  {item['file']}")
                print(f"    Title: {item['title']}")
                print(f"    Embedding: {item['embed_len']} chars")
                print(f"    Has purpose: {item['has_purpose']}, Has use cases: {item['has_use_cases']}")
                print(f"    Processed: {item['processed_at']}")
            if len(flopy_workflows) > 10:
                print(f"  ... and {len(flopy_workflows) - 10} more")
            print(f"\n  TOTAL TO REPROCESS: {len(flopy_workflows)}")
        else:
            print("  ✅ All FloPy workflows have good embeddings!")
        
        # PyEmu workflows
        pyemu_workflows = self.check_pyemu_workflows()
        print(f"\n\nPYEMU WORKFLOWS (threshold: {self.PYEMU_WORKFLOW_MIN_EMBED} chars):")
        print("-" * 40)
        if pyemu_workflows:
            for item in pyemu_workflows[:10]:
                print(f"  {item['file']}")
                print(f"    Title: {item['title']}")
                print(f"    Embedding: {item['embed_len']} chars")
                print(f"    Has purpose: {item['has_purpose']}, Has practices: {item['has_practices']}")
                print(f"    Processed: {item['processed_at']}")
            if len(pyemu_workflows) > 10:
                print(f"  ... and {len(pyemu_workflows) - 10} more")
            print(f"\n  TOTAL TO REPROCESS: {len(pyemu_workflows)}")
        else:
            print("  ✅ All PyEmu workflows have good embeddings!")
        
        # Summary
        total_poor = len(flopy_modules) + len(pyemu_modules) + len(flopy_workflows) + len(pyemu_workflows)
        print("\n" + "=" * 80)
        print(f"TOTAL ITEMS NEEDING REPROCESSING: {total_poor}")
        print("=" * 80)
    
    def export_reprocess_lists(self):
        """Export lists of items to reprocess"""
        # FloPy modules
        flopy_modules = self.check_flopy_modules()
        if flopy_modules:
            with open('/home/danilopezmella/flopy_expert/tests/reprocess_flopy_modules.txt', 'w') as f:
                for item in flopy_modules:
                    f.write(f"{item['id']},{item['path']}\n")
            print(f"✓ Exported {len(flopy_modules)} FloPy modules to reprocess_flopy_modules.txt")
        
        # PyEmu modules
        pyemu_modules = self.check_pyemu_modules()
        if pyemu_modules:
            with open('/home/danilopezmella/flopy_expert/tests/reprocess_pyemu_modules.txt', 'w') as f:
                for item in pyemu_modules:
                    f.write(f"{item['id']},{item['path']}\n")
            print(f"✓ Exported {len(pyemu_modules)} PyEmu modules to reprocess_pyemu_modules.txt")
        
        # FloPy workflows
        flopy_workflows = self.check_flopy_workflows()
        if flopy_workflows:
            with open('/home/danilopezmella/flopy_expert/tests/reprocess_flopy_workflows.txt', 'w') as f:
                for item in flopy_workflows:
                    f.write(f"{item['id']},{item['file']}\n")
            print(f"✓ Exported {len(flopy_workflows)} FloPy workflows to reprocess_flopy_workflows.txt")
        
        # PyEmu workflows
        pyemu_workflows = self.check_pyemu_workflows()
        if pyemu_workflows:
            with open('/home/danilopezmella/flopy_expert/tests/reprocess_pyemu_workflows.txt', 'w') as f:
                for item in pyemu_workflows:
                    f.write(f"{item['id']},{item['file']}\n")
            print(f"✓ Exported {len(pyemu_workflows)} PyEmu workflows to reprocess_pyemu_workflows.txt")


def main():
    """Run quality assessment"""
    checker = EmbeddingQualityChecker(config.NEON_CONNECTION_STRING)
    
    # Print detailed report
    checker.print_report()
    
    # Export lists for reprocessing
    print("\nExporting reprocess lists...")
    checker.export_reprocess_lists()


if __name__ == "__main__":
    main()