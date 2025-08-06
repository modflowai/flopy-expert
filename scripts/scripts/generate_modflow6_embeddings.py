#!/usr/bin/env python3
"""
Generate OpenAI Embeddings for MODFLOW 6 Examples
Creates real semantic embeddings from the rich embedding text.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import psycopg2
from openai import OpenAI
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MODFLOW6EmbeddingProcessor:
    """Generate OpenAI embeddings for MODFLOW 6 examples."""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_EMBEDDING_MODEL
        logger.info(f"Initialized with OpenAI model: {self.model}")
    
    def get_records_needing_embeddings(self):
        """Get all MODFLOW 6 records that need embeddings."""
        with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                # Get records where embedding is likely dummy (all zeros)
                cur.execute("""
                    SELECT tutorial_file, embedding_text 
                    FROM flopy_workflows 
                    WHERE source_repository = 'modflow6-examples'
                    AND embedding_text IS NOT NULL 
                    AND length(embedding_text) > 100
                    ORDER BY tutorial_file
                """)
                return cur.fetchall()
    
    def create_embedding(self, text: str) -> list:
        """Create OpenAI embedding for text."""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            return None
    
    def update_embedding(self, tutorial_file: str, embedding: list):
        """Update embedding in database."""
        with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE flopy_workflows 
                    SET embedding = %s, processed_at = %s
                    WHERE tutorial_file = %s AND source_repository = 'modflow6-examples'
                """, (embedding, datetime.now(), tutorial_file))
                conn.commit()
    
    def process_all_embeddings(self):
        """Process all MODFLOW 6 examples to create embeddings."""
        logger.info("🚀 Starting MODFLOW 6 embedding generation...")
        
        # Get records that need embeddings
        records = self.get_records_needing_embeddings()
        logger.info(f"Found {len(records)} records to process")
        
        if not records:
            logger.info("✅ No records need embedding generation")
            return
        
        successful = 0
        failed = 0
        
        for i, (tutorial_file, embedding_text) in enumerate(records, 1):
            logger.info(f"Processing [{i}/{len(records)}]: {tutorial_file}")
            
            if not embedding_text or len(embedding_text.strip()) < 50:
                logger.warning(f"  ⚠️  Skipping - insufficient embedding text ({len(embedding_text) if embedding_text else 0} chars)")
                failed += 1
                continue
            
            # Create embedding
            start_time = time.time()
            embedding = self.create_embedding(embedding_text)
            
            if embedding:
                # Update database
                self.update_embedding(tutorial_file, embedding)
                
                processing_time = time.time() - start_time
                successful += 1
                logger.info(f"  ✅ Success ({processing_time:.1f}s): {len(embedding)} dimensions")
            else:
                failed += 1
                logger.error(f"  ❌ Failed to create embedding")
            
            # Rate limiting - OpenAI allows 3000 RPM for embeddings
            time.sleep(0.1)  # Small delay to be respectful
        
        logger.info(f"🏁 Embedding generation complete!")
        logger.info(f"   Successful: {successful}")
        logger.info(f"   Failed: {failed}")
        
        # Verify results
        self.verify_embeddings()
    
    def verify_embeddings(self):
        """Verify that embeddings were created successfully."""
        logger.info("🔍 Verifying embedding quality...")
        
        with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                # Check embedding dimensions and sample values
                cur.execute("""
                    SELECT tutorial_file, cardinality(embedding) as dimensions
                    FROM flopy_workflows 
                    WHERE source_repository = 'modflow6-examples'
                    AND embedding IS NOT NULL
                    LIMIT 5
                """)
                
                results = cur.fetchall()
                logger.info("Sample embedding dimensions:")
                for tutorial_file, dimensions in results:
                    logger.info(f"  {tutorial_file}: {dimensions} dimensions")
                
                # Count total records with proper embeddings
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM flopy_workflows 
                    WHERE source_repository = 'modflow6-examples'
                    AND embedding IS NOT NULL
                    AND cardinality(embedding) = 1536
                """)
                
                proper_embeddings = cur.fetchone()[0]
                logger.info(f"✅ {proper_embeddings} records have proper 1536-dimensional embeddings")
    
    def test_semantic_search(self):
        """Test semantic search with actual embeddings."""
        logger.info("🔍 Testing semantic search...")
        
        test_queries = [
            "henry problem saltwater intrusion",
            "sparse matrix solver",
            "well pumping simulation"
        ]
        
        for query in test_queries:
            logger.info(f"Testing query: '{query}'")
            
            # Create query embedding
            query_embedding = self.create_embedding(query)
            if not query_embedding:
                logger.error(f"Failed to create query embedding for: {query}")
                continue
            
            # Search database
            with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT tutorial_file, workflow_purpose, 
                               embedding <-> %s::vector as distance
                        FROM flopy_workflows 
                        WHERE source_repository = 'modflow6-examples'
                        AND embedding IS NOT NULL
                        AND cardinality(embedding) = 1536
                        ORDER BY distance
                        LIMIT 3
                    """, [query_embedding])
                    
                    results = cur.fetchall()
                    for i, (file, purpose, distance) in enumerate(results, 1):
                        similarity = 1 - distance
                        logger.info(f"  {i}. {file} - {similarity:.3f} similarity")
                        logger.info(f"     {purpose[:100]}...")
            
            logger.info("")


def main():
    """Main function to generate embeddings."""
    processor = MODFLOW6EmbeddingProcessor()
    
    # Process all embeddings
    processor.process_all_embeddings()
    
    # Test semantic search
    processor.test_semantic_search()


if __name__ == "__main__":
    main()