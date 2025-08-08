#!/usr/bin/env python3
"""
DSPy Workflow Analysis Optimizer
Uses DSPy to find better prompts for code analysis, then generates v01 embeddings with GPT-5-mini
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from openai import AsyncOpenAI
import dspy

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
import config


class WorkflowAnalysisOptimizer:
    """DSPy-powered workflow analysis optimizer"""
    
    def __init__(self):
        # Initialize connections
        self.neon_conn = config.NEON_CONNECTION_STRING
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        
        # Configure DSPy with GPT-5-mini (with required temperature=1)
        import litellm
        litellm.drop_params = True  # Drop unsupported params
        
        dspy.configure(lm=dspy.LM('gpt-5-mini', api_key=config.OPENAI_API_KEY))
        
        # Initialize optimizer
        self.optimizer = None
        
    def fetch_training_data(self, limit: int = 10) -> List[Dict]:
        """Fetch workflows with existing v00 analysis for training"""
        with psycopg2.connect(self.neon_conn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id, tutorial_file, source_code, analysis_v00
                    FROM flopy_workflows
                    WHERE analysis_v00 IS NOT NULL
                        AND source_code IS NOT NULL
                        AND source_repository = 'flopy'
                    ORDER BY tutorial_file
                    LIMIT %s
                """, (limit,))
                return cur.fetchall()
    
    def create_dspy_examples(self, workflows: List[Dict]) -> List[dspy.Example]:
        """Convert workflows to DSPy training examples"""
        examples = []
        
        for workflow in workflows:
            example = dspy.Example(
                source_code=workflow['source_code'],
                tutorial_file=workflow['tutorial_file'],
                # Expected output from v00 analysis
                title=workflow['analysis_v00']['title'],
                summary=workflow['analysis_v00']['summary'],
                key_concepts=workflow['analysis_v00']['key_concepts'],
                potential_questions=workflow['analysis_v00']['potential_questions'],
                keywords=workflow['analysis_v00']['keywords']
            ).with_inputs('source_code', 'tutorial_file')
            
            examples.append(example)
        
        return examples

class WorkflowAnalysisSignature(dspy.Signature):
    """DSPy signature for workflow analysis generation"""
    source_code = dspy.InputField(desc="Python source code of the FloPy workflow")
    tutorial_file = dspy.InputField(desc="Filename of the tutorial for context")
    
    title = dspy.OutputField(desc="Clear, descriptive title of what this workflow demonstrates")
    summary = dspy.OutputField(desc="Concise 1-2 paragraph explanation of the workflow's purpose and techniques")
    key_concepts = dspy.OutputField(desc="List of 5-10 fundamental groundwater/modeling concepts demonstrated")
    potential_questions = dspy.OutputField(desc="List of exactly 10 diverse search queries users would type to find this workflow")
    keywords = dspy.OutputField(desc="List of 10-15 specific technical search terms")

class OptimizedWorkflowAnalyzer(dspy.Module):
    """DSPy module for generating optimized workflow analysis"""
    
    def __init__(self):
        super().__init__()
        self.analyzer = dspy.ChainOfThought(WorkflowAnalysisSignature)
    
    def forward(self, source_code, tutorial_file):
        result = self.analyzer(source_code=source_code, tutorial_file=tutorial_file)
        return dspy.Prediction(
            title=result.title,
            summary=result.summary, 
            key_concepts=result.key_concepts,
            potential_questions=result.potential_questions,
            keywords=result.keywords
        )

def analysis_quality_metric(example, pred, trace=None):
    """Evaluate the quality of generated analysis with focus on search relevance"""
    score = 0.0
    
    try:
        # Parse outputs consistently
        questions = parse_list_output(pred.potential_questions)
        concepts = parse_list_output(pred.key_concepts) 
        keywords = parse_list_output(pred.keywords)
        
        # 1. TITLE QUALITY (15 points) - Descriptive and specific
        if pred.title and 20 < len(pred.title) < 100:
            score += 10
            # Bonus for specificity (mentions FloPy/MODFLOW/specific technique)
            title_lower = pred.title.lower()
            if any(term in title_lower for term in ['flopy', 'modflow', 'grid', 'boundary', 'package']):
                score += 5
        
        # 2. SUMMARY QUALITY (20 points) - Concise but informative
        if pred.summary and 300 < len(pred.summary) < 1000:
            score += 15
            # Penalty for overly verbose summaries
            if len(pred.summary) > 800:
                score -= 5
        
        # 3. QUESTION NATURALNESS (25 points) - Sound like real user queries
        if 8 <= len(questions) <= 12:
            score += 10
            
            # Check for natural language patterns
            natural_score = 0
            question_text = ' '.join(questions).lower()
            
            # Reward natural question patterns
            natural_patterns = [
                'how do i', 'how to', 'how can i', 'what is', 'why does', 
                'example of', 'tutorial for', 'error when', 'problem with'
            ]
            for pattern in natural_patterns:
                if pattern in question_text:
                    natural_score += 2
            
            # Reward diverse question types
            question_types = 0
            if any(word in question_text for word in ['how', 'tutorial', 'example']):
                question_types += 3
            if any(word in question_text for word in ['what', 'explain', 'difference']):
                question_types += 3  
            if any(word in question_text for word in ['error', 'problem', 'fail', 'not working']):
                question_types += 4  # Troubleshooting is valuable
            if any(word in question_text for word in ['vs', 'compare', 'better', 'alternative']):
                question_types += 3
                
            score += min(natural_score, 10)  # Cap at 10 points
            score += min(question_types, 5)   # Cap at 5 points
        
        # 4. TECHNICAL ACCURACY (20 points) - Correct package/method names
        code_text = example.source_code.lower()
        accuracy_score = 0
        
        # Check if mentioned concepts/keywords actually appear in code
        all_terms = concepts + keywords
        matching_terms = 0
        total_terms = len(all_terms)
        
        if total_terms > 0:
            for term in all_terms:
                term_lower = term.lower().strip()
                # Check for FloPy-specific terms
                if any(flopy_term in term_lower for flopy_term in ['flopy', 'modflow', 'dis', 'npf', 'wel', 'chd', 'rch']):
                    matching_terms += 2  # Extra credit for FloPy terms
                elif any(code_term in code_text for code_term in [term_lower, term_lower.replace(' ', '_'), term_lower.replace(' ', '')]):
                    matching_terms += 1
            
            # Accuracy ratio
            accuracy_ratio = min(matching_terms / total_terms, 1.0)
            accuracy_score = accuracy_ratio * 15
        
        # Bonus for specific package mentions
        if any(pkg in question_text + ' '.join(concepts).lower() for pkg in ['dis', 'npf', 'wel', 'chd', 'ghb', 'rch']):
            accuracy_score += 5
            
        score += accuracy_score
        
        # 5. CONCEPT SPECIFICITY (10 points) - Not too generic
        if 5 <= len(concepts) <= 10:
            specificity_score = 0
            
            # Penalize overly generic concepts
            generic_concepts = ['python', 'programming', 'code', 'software', 'data', 'file', 'array']
            generic_count = sum(1 for concept in concepts if concept.lower() in generic_concepts)
            
            # Reward specific hydrogeological/FloPy concepts  
            specific_concepts = [
                'boundary condition', 'hydraulic conductivity', 'groundwater flow',
                'steady-state', 'transient', 'discretization', 'finite difference',
                'head', 'drawdown', 'aquifer', 'confined', 'unconfined'
            ]
            specific_count = sum(1 for concept in concepts 
                               if any(spec in concept.lower() for spec in specific_concepts))
            
            specificity_score = max(0, 10 - generic_count * 2 + specific_count * 2)
            score += min(specificity_score, 10)
        
        # 6. KEYWORD UNIQUENESS (10 points) - Different from concepts  
        if 8 <= len(keywords) <= 15:
            # Check overlap between keywords and concepts
            concept_words = set(' '.join(concepts).lower().split())
            keyword_words = set(' '.join(keywords).lower().split())
            
            overlap = len(concept_words.intersection(keyword_words))
            total_words = len(concept_words.union(keyword_words))
            
            # Reward low overlap (keywords should be different from concepts)
            if total_words > 0:
                uniqueness = 1 - (overlap / total_words)
                score += uniqueness * 10
        
        return min(score / 100.0, 1.0)  # Normalize and cap at 1.0
        
    except Exception as e:
        print(f"Error in metric evaluation: {e}")
        return 0.0

def parse_list_output(output):
    """Parse list output that might be string or actual list"""
    if isinstance(output, list):
        return output
    elif isinstance(output, str):
        try:
            # Try JSON first
            return json.loads(output)
        except:
            # Fall back to comma/newline split
            items = []
            for item in output.replace('\n', ',').split(','):
                item = item.strip().strip('"\'')
                if item and len(item) > 1:
                    items.append(item)
            return items
    return []

async def main():
    """Main DSPy optimization workflow"""
    print("=" * 80)
    print("DSPy Workflow Analysis Optimizer")
    print("Using GPT-5-mini for analysis optimization")
    print("=" * 80)
    
    optimizer = WorkflowAnalysisOptimizer()
    
    # Step 1: Fetch training data
    print("\n1. Fetching training data...")
    workflows = optimizer.fetch_training_data(limit=10)
    print(f"   Loaded {len(workflows)} workflows with v00 analysis")
    
    # Step 2: Create DSPy examples
    print("\n2. Creating DSPy training examples...")
    examples = optimizer.create_dspy_examples(workflows)
    print(f"   Created {len(examples)} training examples")
    
    # Step 3: Initialize and optimize
    print("\n3. Training DSPy optimizer...")
    print("   This may take 5-10 minutes as DSPy tests different prompt variations...")
    
    workflow_analyzer = OptimizedWorkflowAnalyzer()
    
    # Use DSPy's MIPROv2 optimizer
    try:
        from dspy.teleprompt import MIPROv2
    except ImportError:
        from dspy.teleprompt import MIPRO as MIPROv2
        
    teleprompter = MIPROv2(
        metric=analysis_quality_metric,
        auto="medium",  # Automatic optimization level
        num_threads=1   # Conservative threading for API limits
    )
    
    # Split data for training
    trainset = examples[:8]  # Use 8 for training
    testset = examples[8:]   # Use 2 for testing
    
    print(f"   Training with {len(trainset)} examples...")
    print(f"   Testing with {len(testset)} examples...")
    
    # Optimize the module
    optimized_analyzer = teleprompter.compile(
        workflow_analyzer,
        trainset=trainset,
        valset=testset,
        max_bootstrapped_demos=3,
        max_labeled_demos=2
    )
    
    print("✓ DSPy optimization complete!")
    
    # Step 4: Test the optimized analyzer
    print("\n4. Testing optimized analyzer...")
    
    # Test on a workflow not used in training
    test_workflow = workflows[-1]  # Last workflow
    
    result = optimized_analyzer(
        source_code=test_workflow['source_code'],
        tutorial_file=test_workflow['tutorial_file']
    )
    
    print(f"\n   Test Results:")
    print(f"   File: {test_workflow['tutorial_file']}")
    print(f"   Title: {result.title}")
    print(f"   Summary length: {len(result.summary)} chars")
    print(f"   Questions: {type(result.potential_questions)} - {result.potential_questions[:100]}...")
    
    # Step 5: Generate v01 analysis for all workflows
    print("\n5. Generating v01 analysis for all workflows...")
    
    workflows_to_process = optimizer.fetch_training_data(limit=50)  # Get more workflows
    
    successful = 0
    failed = 0
    
    for i, workflow in enumerate(workflows_to_process, 1):
        try:
            print(f"   [{i}/{len(workflows_to_process)}] Processing: {Path(workflow['tutorial_file']).name}")
            
            # Generate optimized analysis
            result = optimized_analyzer(
                source_code=workflow['source_code'],
                tutorial_file=workflow['tutorial_file']
            )
            
            # Convert result to structured analysis
            analysis_v01 = {
                "title": result.title,
                "summary": result.summary,
                "key_concepts": result.key_concepts if isinstance(result.key_concepts, list) else 
                               [c.strip() for c in result.key_concepts.split(',') if c.strip()],
                "potential_questions": result.potential_questions if isinstance(result.potential_questions, list) else
                                     [q.strip() for q in result.potential_questions.split(',') if q.strip()],
                "keywords": result.keywords if isinstance(result.keywords, list) else
                           [k.strip() for k in result.keywords.split(',') if k.strip()]
            }
            
            # Create embedding string
            embedding_string = format_embedding_string_v01(workflow, analysis_v01)
            
            # Create embedding vector
            embedding_response = await optimizer.openai_client.embeddings.create(
                input=embedding_string,
                model=config.OPENAI_EMBEDDING_MODEL
            )
            embedding_vector = embedding_response.data[0].embedding
            
            # Store in database
            with psycopg2.connect(optimizer.neon_conn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE flopy_workflows
                        SET 
                            emb_string_01 = %s,
                            dspy_emb_01 = %s
                        WHERE id = %s
                    """, (
                        embedding_string,
                        embedding_vector,
                        workflow['id']
                    ))
                    conn.commit()
            
            successful += 1
            
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("DSPy Optimization Complete!")
    print(f"  Successful v01 generations: {successful}")
    print(f"  Failed: {failed}")
    print("=" * 80)
    
    # Show comparison stats
    show_comparison_stats(optimizer.neon_conn)

def format_embedding_string_v01(workflow: Dict, analysis: Dict) -> str:
    """Create embedding string for v01"""
    filename = Path(workflow['tutorial_file']).name
    filepath = workflow['tutorial_file']
    
    embedding_string = f"""
        Filename: {filename}
        Filepath: {filepath}
        Repository: flopy
        
        Title: {analysis['title']}
        
        Summary: {analysis['summary']}
        
        Key Concepts: {', '.join(analysis['key_concepts']) if isinstance(analysis['key_concepts'], list) else analysis['key_concepts']}
        
        Potential Questions: {' | '.join(analysis['potential_questions']) if isinstance(analysis['potential_questions'], list) else analysis['potential_questions']}
        
        Keywords: {', '.join(analysis['keywords']) if isinstance(analysis['keywords'], list) else analysis['keywords']}
        """
    
    # Clean up extra whitespace
    lines = [line.strip() for line in embedding_string.strip().split('\n')]
    return '\n'.join(lines)

def show_comparison_stats(neon_conn: str):
    """Show statistics comparing v00 vs v01"""
    with psycopg2.connect(neon_conn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(analysis_v00) as with_v00,
                    COUNT(emb_string_01) as with_v01,
                    AVG(LENGTH(emb_string_00)) as avg_v00_length,
                    AVG(LENGTH(emb_string_01)) as avg_v01_length
                FROM flopy_workflows
                WHERE source_repository = 'flopy'
            """)
            
            stats = cur.fetchone()
            if stats:
                print(f"\nComparison Statistics:")
                print(f"  Total FloPy workflows: {stats['total']}")
                print(f"  With v00 analysis: {stats['with_v00']}")
                print(f"  With v01 analysis: {stats['with_v01']}")
                if stats['avg_v00_length'] and stats['avg_v01_length']:
                    print(f"  Average v00 length: {stats['avg_v00_length']:.0f} chars")
                    print(f"  Average v01 length: {stats['avg_v01_length']:.0f} chars")

if __name__ == "__main__":
    asyncio.run(main())