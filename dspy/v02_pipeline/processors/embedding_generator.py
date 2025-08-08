"""
Embedding Generator for V02 Pipeline
Creates OpenAI embeddings from ultra-discriminative analysis
"""

import logging
import time
from typing import Dict, Any, List, Optional
import openai
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Generates embeddings from ultra-discriminative analysis"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """
        Initialize embedding generator
        
        Args:
            api_key: OpenAI API key
            model: Embedding model name
        """
        openai.api_key = api_key
        self.model = model
        self.dimensions = 1536  # For text-embedding-3-small
        self.max_retries = 3
        self.retry_delay = 2
    
    def create_embedding_text(self, 
                             workflow: Dict[str, Any], 
                             analysis: Dict[str, Any],
                             include_metadata: bool = True) -> str:
        """
        Create comprehensive text for embedding from analysis
        
        Args:
            workflow: Original workflow data
            analysis: Ultra-discriminative analysis
            include_metadata: Whether to include original metadata
            
        Returns:
            Text string for embedding
        """
        parts = []
        
        # Add basic identification
        if 'file' in workflow:
            parts.append(f"File: {workflow['file']}")
        elif 'tutorial_file' in workflow:
            parts.append(f"Tutorial: {workflow['tutorial_file']}")
        elif 'notebook_file' in workflow:
            parts.append(f"Notebook: {workflow['notebook_file']}")
        
        if 'title' in workflow:
            parts.append(f"Title: {workflow['title']}")
        
        if 'workflow_type' in workflow:
            parts.append(f"Type: {workflow['workflow_type']}")
        elif 'model_type' in workflow:
            parts.append(f"Model Type: {workflow['model_type']}")
        
        # Add ultra-discriminative purpose
        if 'workflow_purpose' in analysis:
            parts.append(f"Purpose: {analysis['workflow_purpose']}")
        
        # Add discriminative questions (most important)
        if 'discriminative_questions' in analysis:
            parts.append("")
            parts.append("ULTRA-DISCRIMINATIVE QUESTIONS:")
            for i, question in enumerate(analysis['discriminative_questions'][:10], 1):
                parts.append(f"{i}. {question}")
        
        # Add key differentiators
        if 'key_differentiators' in analysis:
            parts.append("")
            parts.append("KEY DIFFERENTIATORS:")
            for diff in analysis['key_differentiators']:
                parts.append(f"- {diff}")
        
        # Add domain-specific features
        self._add_domain_specific_features(parts, analysis, workflow)
        
        # Add original metadata if requested
        if include_metadata:
            self._add_original_metadata(parts, workflow)
        
        return "\n".join(parts)
    
    def _add_domain_specific_features(self, parts: List[str], analysis: Dict, workflow: Dict):
        """Add domain-specific features based on workflow type"""
        
        # For PyEMU workflows
        if 'pest_tool_specifics' in analysis:
            parts.append("")
            parts.append("PEST++ TOOL SPECIFICS:")
            for spec in analysis['pest_tool_specifics']:
                parts.append(f"- {spec}")
        
        if 'statistical_implementation' in analysis:
            parts.append("")
            parts.append("STATISTICAL IMPLEMENTATION:")
            for impl in analysis['statistical_implementation']:
                parts.append(f"- {impl}")
        
        if 'unique_pyemu_features' in analysis:
            parts.append("")
            parts.append("PYEMU FEATURES:")
            for feature in analysis['unique_pyemu_features']:
                parts.append(f"- {feature}")
        
        # For FloPy workflows
        if 'modflow_version_specifics' in analysis:
            parts.append("")
            parts.append("MODFLOW VERSION SPECIFICS:")
            for spec in analysis['modflow_version_specifics']:
                parts.append(f"- {spec}")
        
        if 'package_implementations' in analysis:
            parts.append("")
            parts.append("PACKAGE IMPLEMENTATIONS:")
            for impl in analysis['package_implementations']:
                parts.append(f"- {impl}")
    
    def _add_original_metadata(self, parts: List[str], workflow: Dict):
        """Add original metadata from workflow"""
        
        # PyEMU specific
        if 'pest_concepts' in workflow and workflow['pest_concepts']:
            parts.append("")
            parts.append(f"PEST Concepts: {', '.join(workflow['pest_concepts'])}")
        
        if 'uncertainty_methods' in workflow and workflow['uncertainty_methods']:
            parts.append(f"Uncertainty Methods: {', '.join(workflow['uncertainty_methods'])}")
        
        # FloPy specific
        if 'packages_used' in workflow and workflow['packages_used']:
            packages = workflow['packages_used'][:10]  # Limit to first 10
            parts.append("")
            parts.append(f"Packages: {', '.join(packages)}")
        
        if 'model_type' in workflow:
            parts.append(f"Model Type: {workflow['model_type']}")
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector from text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                response = openai.embeddings.create(
                    model=self.model,
                    input=text
                )
                embedding = response.data[0].embedding
                logger.debug(f"Generated embedding with {len(embedding)} dimensions")
                return embedding
                
            except Exception as e:
                logger.warning(f"Embedding generation attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay ** attempt)
        
        logger.error(f"Failed to generate embedding after {self.max_retries} attempts")
        return None
    
    def batch_generate(self,
                      workflows_with_analysis: List[Dict[str, Any]],
                      checkpoint_manager=None) -> Dict[str, Dict[str, Any]]:
        """
        Generate embeddings for multiple workflows
        
        Args:
            workflows_with_analysis: List of dicts with 'workflow' and 'analysis' keys
            checkpoint_manager: Optional checkpoint manager
            
        Returns:
            Dictionary mapping workflow IDs to embedding data
        """
        results = {}
        
        for i, item in enumerate(workflows_with_analysis, 1):
            workflow = item['workflow']
            analysis = item['analysis']
            workflow_id = workflow.get('id') or workflow.get('file')
            
            # Check if already processed
            if checkpoint_manager and not checkpoint_manager.should_process(workflow_id):
                checkpoint_manager.mark_skipped(workflow_id)
                logger.info(f"[{i}/{len(workflows_with_analysis)}] Skipping {workflow_id}")
                continue
            
            logger.info(f"[{i}/{len(workflows_with_analysis)}] Generating embedding for {workflow_id}")
            
            # Create embedding text
            embedding_text = self.create_embedding_text(workflow, analysis)
            logger.debug(f"  Text length: {len(embedding_text)} chars")
            
            # Generate embedding
            embedding = self.generate_embedding(embedding_text)
            
            if embedding:
                results[workflow_id] = {
                    'embedding': embedding,
                    'embedding_text': embedding_text,
                    'text_length': len(embedding_text)
                }
                
                if checkpoint_manager:
                    checkpoint_manager.mark_completed(workflow_id, {
                        'text_length': len(embedding_text),
                        'timestamp': time.time()
                    })
                logger.info(f"  ✅ Generated embedding ({len(embedding_text)} chars)")
            else:
                if checkpoint_manager:
                    checkpoint_manager.mark_failed(workflow_id, "Failed to generate embedding")
                logger.error(f"  ❌ Failed to generate embedding")
            
            # Rate limiting
            time.sleep(0.5)
        
        return results
    
    @staticmethod
    def format_embedding_for_postgres(embedding: List[float]) -> str:
        """Format embedding for PostgreSQL vector column"""
        return '[' + ','.join(map(str, embedding)) + ']'
    
    @staticmethod
    def validate_embedding(embedding: List[float], expected_dims: int = 1536) -> bool:
        """Validate embedding dimensions and values"""
        if len(embedding) != expected_dims:
            logger.error(f"Invalid embedding dimensions: {len(embedding)} (expected {expected_dims})")
            return False
        
        # Check for NaN or inf values
        arr = np.array(embedding)
        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
            logger.error("Embedding contains NaN or inf values")
            return False
        
        return True