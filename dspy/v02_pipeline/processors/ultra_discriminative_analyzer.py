"""
Ultra-Discriminative Analysis Generator
Generates highly specific technical questions and analysis using Gemini
"""

import sys
import json
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
import google.genai as genai

logger = logging.getLogger(__name__)

class UltraDiscriminativeAnalyzer:
    """Generates ultra-discriminative analysis for workflows"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize the analyzer with Gemini
        
        Args:
            api_key: Google Gemini API key
            model_name: Gemini model to use
        """
        self.gemini_client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.max_retries = 3
        self.retry_delay = 2
    
    async def _generate_async(self, prompt: str) -> Any:
        """Async wrapper for Gemini generation"""
        response = await asyncio.to_thread(
            self.gemini_client.models.generate_content,
            model=self.model_name,
            contents=prompt
        )
        return response
    
    def generate_analysis(self, 
                         workflow: Dict[str, Any], 
                         prompt_template: str,
                         required_fields: List[str]) -> Optional[Dict[str, Any]]:
        """
        Generate ultra-discriminative analysis for a workflow
        
        Args:
            workflow: Workflow data dictionary
            prompt_template: Template for the prompt
            required_fields: List of required fields in the response
            
        Returns:
            Analysis dictionary or None if failed
        """
        # Format the prompt with workflow data
        prompt = prompt_template.format(**workflow)
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Generating analysis (attempt {attempt + 1})")
                
                # Generate response using Gemini
                response = asyncio.run(self._generate_async(prompt))
                
                # Parse JSON from response
                analysis = self._extract_json(response.text)
                
                # Validate required fields
                if analysis and self._validate_analysis(analysis, required_fields):
                    logger.debug(f"Successfully generated analysis with {len(analysis.get('discriminative_questions', []))} questions")
                    return analysis
                else:
                    logger.warning(f"Analysis missing required fields, retrying...")
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error: {e}")
            except Exception as e:
                logger.error(f"Generation error: {e}")
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay ** attempt)
        
        logger.error(f"Failed to generate analysis after {self.max_retries} attempts")
        return None
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from Gemini response text"""
        # Find JSON in response
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start >= 0 and end > start:
            json_str = text[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try to fix common JSON errors
                json_str = self._fix_json_errors(json_str)
                return json.loads(json_str)
        
        return None
    
    def _fix_json_errors(self, json_str: str) -> str:
        """Attempt to fix common JSON formatting errors"""
        # Replace single quotes with double quotes
        json_str = json_str.replace("'", '"')
        
        # Fix trailing commas
        import re
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        return json_str
    
    def _validate_analysis(self, analysis: Dict, required_fields: List[str]) -> bool:
        """Validate that analysis contains all required fields"""
        for field in required_fields:
            if field not in analysis:
                logger.warning(f"Missing required field: {field}")
                return False
            
            # Check that lists have content
            if isinstance(analysis[field], list) and len(analysis[field]) == 0:
                logger.warning(f"Empty list for required field: {field}")
                return False
        
        return True
    
    def batch_generate(self, 
                      workflows: List[Dict[str, Any]], 
                      prompt_template: str,
                      required_fields: List[str],
                      checkpoint_manager=None) -> Dict[str, Dict[str, Any]]:
        """
        Generate analysis for multiple workflows with checkpoint support
        
        Args:
            workflows: List of workflow dictionaries
            prompt_template: Template for the prompt
            required_fields: List of required fields
            checkpoint_manager: Optional checkpoint manager
            
        Returns:
            Dictionary mapping workflow IDs to analysis
        """
        results = {}
        
        for i, workflow in enumerate(workflows, 1):
            workflow_id = workflow.get('id') or workflow.get('file')
            
            # Check if already processed
            if checkpoint_manager and not checkpoint_manager.should_process(workflow_id):
                checkpoint_manager.mark_skipped(workflow_id)
                logger.info(f"[{i}/{len(workflows)}] Skipping {workflow_id} (already processed)")
                continue
            
            logger.info(f"[{i}/{len(workflows)}] Processing {workflow_id}")
            
            # Generate analysis
            analysis = self.generate_analysis(workflow, prompt_template, required_fields)
            
            if analysis:
                results[workflow_id] = analysis
                if checkpoint_manager:
                    checkpoint_manager.mark_completed(workflow_id, {
                        "questions_count": len(analysis.get('discriminative_questions', [])),
                        "timestamp": time.time()
                    })
                logger.info(f"  ✅ Generated {len(analysis.get('discriminative_questions', []))} questions")
            else:
                if checkpoint_manager:
                    checkpoint_manager.mark_failed(workflow_id, "Failed to generate analysis")
                logger.error(f"  ❌ Failed to generate analysis")
            
            # Rate limiting
            time.sleep(1)
        
        return results
    
    def format_analysis_summary(self, analysis: Dict[str, Any]) -> str:
        """Format analysis into a readable summary"""
        lines = []
        
        if 'workflow_purpose' in analysis:
            lines.append(f"Purpose: {analysis['workflow_purpose']}")
        
        if 'discriminative_questions' in analysis:
            lines.append(f"Questions: {len(analysis['discriminative_questions'])}")
            if analysis['discriminative_questions']:
                sample = str(analysis['discriminative_questions'][0])[:100]
                lines.append(f"Sample: {sample}...")
        
        if 'key_differentiators' in analysis:
            lines.append(f"Differentiators: {len(analysis['key_differentiators'])}")
        
        return " | ".join(lines)