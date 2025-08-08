# FloPy Workflows DSPy Embedding Optimization Roadmap

## Overview
Transform poor concatenated embedding strings in `flopy_workflows` into rich, semantic documents optimized for retrieval using DSPy, with versioned columns for A/B testing and continuous improvement.

## Current State Assessment
- **Table**: `flopy_workflows` in Neon project `autumn-math-76166931` (modflow_ai)
- **Current embedding**: Simple concatenation of title, description, packages
- **Problem**: Poor semantic quality, missing domain context
- **Goal**: Create repository_files quality embeddings with DSPy optimization

## Database Versioning Strategy

### Naming Convention
```sql
-- Version 00: Baseline enhanced analysis (Gemini-generated)
analysis_v00 JSONB         -- Enhanced analysis structure
emb_string_00 TEXT          -- Formatted embedding string from analysis
dspy_emb_00 vector(1536)    -- OpenAI embedding from emb_string_00

-- Version 01: First DSPy optimization
emb_string_01 TEXT          -- DSPy-optimized embedding string
dspy_emb_01 vector(1536)    -- OpenAI embedding from DSPy output

-- Version 02: Refined DSPy with user feedback
emb_string_02 TEXT          
dspy_emb_02 vector(1536)    
```

---

## Phase 1: Database Preparation (30 min)
**Goal**: Add versioned columns for A/B testing without disrupting existing system

### Step 1.1: Add Analysis Column
```python
# Using Neon MCP tool
mcp__Neon__run_sql(
    projectId="autumn-math-76166931",
    sql="""
    ALTER TABLE flopy_workflows 
    ADD COLUMN IF NOT EXISTS analysis_v00 JSONB,
    ADD COLUMN IF NOT EXISTS analysis_generated_at TIMESTAMP;
    """
)
```

### Step 1.2: Add Embedding String Columns
```python
mcp__Neon__run_sql(
    projectId="autumn-math-76166931",
    sql="""
    ALTER TABLE flopy_workflows 
    ADD COLUMN IF NOT EXISTS emb_string_00 TEXT,
    ADD COLUMN IF NOT EXISTS emb_string_01 TEXT,
    ADD COLUMN IF NOT EXISTS emb_string_02 TEXT;
    """
)
```

### Step 1.3: Add Vector Columns
```python
mcp__Neon__run_sql(
    projectId="autumn-math-76166931",
    sql="""
    ALTER TABLE flopy_workflows 
    ADD COLUMN IF NOT EXISTS dspy_emb_00 vector(1536),
    ADD COLUMN IF NOT EXISTS dspy_emb_01 vector(1536),
    ADD COLUMN IF NOT EXISTS dspy_emb_02 vector(1536);
    """
)
```

### Step 1.4: Create Comparison View
```python
mcp__Neon__run_sql(
    projectId="autumn-math-76166931",
    sql="""
    CREATE OR REPLACE VIEW workflow_embedding_comparison AS
    SELECT 
        id,
        tutorial_file,
        title,
        -- Original embedding
        LENGTH(embedding_text) as original_length,
        -- Version 00
        LENGTH(emb_string_00) as v00_length,
        -- Version 01
        LENGTH(emb_string_01) as v01_length,
        -- Similarity scores (when both exist)
        CASE 
            WHEN dspy_emb_00 IS NOT NULL AND embedding IS NOT NULL 
            THEN 1 - (dspy_emb_00 <-> embedding) 
        END as v00_vs_original_similarity
    FROM flopy_workflows;
    """
)
```

---

## Phase 2: Enhanced Analysis Structure (2 hours)
**Goal**: Create rich analysis JSON similar to repository_files

### Step 2.1: Create Analysis Generator Script
```python
# File: scripts/generate_workflow_analysis_v00.py

class WorkflowAnalysisGenerator:
    def __init__(self):
        self.gemini_client = google.generativeai.configure()
        self.neon_conn = config.NEON_CONNECTION_STRING
    
    def create_analysis_prompt(self, workflow):
        return f"""
        Analyze this FloPy workflow and generate a comprehensive analysis.
        
        Title: {workflow['title']}
        Code: {workflow['source_code']}
        Packages: {workflow['packages_used']}
        
        Generate JSON with these fields:
        - modeling_objective: What groundwater problem this solves
        - hydrogeological_concepts: Physical concepts list
        - numerical_methods: Solver types, discretization
        - package_interactions: How packages work together
        - flopy_patterns: Code patterns used
        - key_parameters: Critical parameters with typical values
        - learning_objectives: What users will learn
        - prerequisite_concepts: Required knowledge
        - difficulty_progression: beginner/intermediate/advanced
        - typical_modifications: Common adaptations
        - real_world_applications: Actual use cases
        - common_errors: Pitfalls to avoid
        - debugging_hints: Troubleshooting tips
        - user_queries: Natural language questions this answers
        - alternative_approaches: Other solutions
        - related_workflows: Similar examples
        """
```

### Step 2.2: Process Workflows in Batches
```python
# Process 5 workflows at a time to manage costs
batch_size = 5
workflows = fetch_workflows_from_neon()

for batch in chunks(workflows, batch_size):
    for workflow in batch:
        analysis = generate_analysis_with_gemini(workflow)
        store_analysis_v00(workflow['id'], analysis)
    time.sleep(2)  # Rate limiting
```

### Step 2.3: Create Embedding String Formatter
```python
def format_embedding_string_v00(workflow, analysis):
    """Create structured embedding string from analysis"""
    return f"""
    Workflow: {workflow['title']}
    Model Type: {workflow['model_type']} | Complexity: {workflow['complexity']}
    
    === OBJECTIVE ===
    {analysis['modeling_objective']}
    
    === HYDROGEOLOGICAL CONCEPTS ===
    {', '.join(analysis['hydrogeological_concepts'])}
    
    === NUMERICAL METHODS ===
    {', '.join(analysis['numerical_methods'])}
    
    === PACKAGE INTERACTIONS ===
    {format_dict(analysis['package_interactions'])}
    
    === KEY PARAMETERS ===
    {format_dict(analysis['key_parameters'])}
    
    === USER QUERIES ===
    {chr(10).join(analysis['user_queries'])}
    
    === REAL-WORLD APPLICATIONS ===
    {'; '.join(analysis['real_world_applications'])}
    """
```

### Step 2.4: Generate Version 00 Embeddings
```python
# Generate OpenAI embeddings for v00
for workflow in workflows:
    emb_string = format_embedding_string_v00(workflow, analysis)
    embedding = openai.embeddings.create(
        input=emb_string,
        model="text-embedding-3-small"
    )
    
    # Store in database
    update_workflow_v00(
        workflow_id=workflow['id'],
        emb_string_00=emb_string,
        dspy_emb_00=embedding.data[0].embedding
    )
```

---

## Phase 3: Test Baseline Performance (1 hour)
**Goal**: Establish metrics for v00 before DSPy optimization

### Step 3.1: Create Test Query Set
```python
test_queries = [
    # Beginner queries
    "how to create a simple steady state model",
    "basic well package setup",
    
    # Intermediate queries
    "transient model with time-varying pumping",
    "river boundary condition implementation",
    
    # Advanced queries
    "coupled surface water groundwater model",
    "density-dependent flow with seawater intrusion",
    
    # Problem-specific queries
    "dewatering simulation for construction",
    "contaminant transport in fractured media"
]
```

### Step 3.2: Measure Retrieval Quality
```python
def evaluate_v00_retrieval():
    results = {}
    for query in test_queries:
        # Get top 3 results using v00 embeddings
        query_emb = create_embedding(query)
        results[query] = search_workflows_v00(query_emb, top_k=3)
    
    # Manual review of relevance
    return calculate_metrics(results)
```

### Step 3.3: Create Baseline Report
```markdown
# Version 00 Baseline Performance
- Average retrieval accuracy: X%
- Beginner query performance: X%
- Advanced query performance: X%
- Common failures: [list patterns]
```

---

## Phase 4: DSPy Setup & Training Data (2 hours)
**Goal**: Prepare DSPy optimization pipeline

### Step 4.1: Install DSPy and Configure
```python
pip install dspy-ai
import dspy

# Configure with OpenAI
dspy.configure(lm=dspy.LM('openai/gpt-4o-mini'))
```

### Step 4.2: Create DSPy Signatures
```python
class WorkflowEmbeddingGenerator(dspy.Signature):
    """Generate optimal embedding for FloPy workflow retrieval"""
    workflow_code = dspy.InputField(desc="FloPy workflow source code")
    workflow_metadata = dspy.InputField(desc="Title, packages, description")
    analysis = dspy.InputField(desc="Comprehensive analysis JSON")
    embedding_string = dspy.OutputField(
        desc="Optimized text for semantic search embedding"
    )

class QueryGenerator(dspy.Signature):
    """Generate test queries for this workflow"""
    workflow_code = dspy.InputField()
    analysis = dspy.InputField()
    test_queries = dspy.OutputField(
        desc="List of 5 realistic user queries, one per line"
    )
```

### Step 4.3: Create Training Dataset
```python
# Use workflows with good existing descriptions as training data
training_workflows = select_high_quality_workflows(limit=20)

trainset = []
for workflow in training_workflows:
    trainset.append(dspy.Example(
        workflow_code=workflow['source_code'],
        workflow_metadata=workflow['metadata'],
        analysis=workflow['analysis_v00'],
        workflow_id=workflow['id']
    ).with_inputs('workflow_code', 'workflow_metadata', 'analysis'))
```

### Step 4.4: Define Quality Metric
```python
def embedding_quality_metric(example, pred):
    """Measure if embedding retrieves correct workflow"""
    try:
        # Generate embedding from DSPy output
        pred_embedding = create_embedding(pred.embedding_string)
        
        # Generate test queries
        queries = pred.test_queries.split('\n')[:3]
        
        # Check if workflow appears in top-3 for its own queries
        retrieval_scores = []
        for query in queries:
            query_emb = create_embedding(query)
            top_results = search_all_workflows(query_emb, top_k=3)
            
            # Score: 1.0 if in top result, 0.5 if in top-3, 0 otherwise
            if example.workflow_id == top_results[0]['id']:
                retrieval_scores.append(1.0)
            elif example.workflow_id in [r['id'] for r in top_results]:
                retrieval_scores.append(0.5)
            else:
                retrieval_scores.append(0.0)
        
        return sum(retrieval_scores) / len(retrieval_scores)
    except:
        return 0.0
```

---

## Phase 5: DSPy Optimization (3 hours)
**Goal**: Create optimized v01 embeddings

### Step 5.1: Build DSPy Module
```python
class WorkflowEmbeddingOptimizer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.embedding_gen = dspy.ChainOfThought(WorkflowEmbeddingGenerator)
        self.query_gen = dspy.ChainOfThought(QueryGenerator)
    
    def forward(self, workflow_code, workflow_metadata, analysis):
        # Generate optimized embedding string
        embedding_result = self.embedding_gen(
            workflow_code=workflow_code,
            workflow_metadata=workflow_metadata,
            analysis=analysis
        )
        
        # Generate test queries for validation
        query_result = self.query_gen(
            workflow_code=workflow_code,
            analysis=analysis
        )
        
        return dspy.Prediction(
            embedding_string=embedding_result.embedding_string,
            test_queries=query_result.test_queries
        )
```

### Step 5.2: Run Optimization
```python
# Start with small subset for testing
optimizer = dspy.MIPROv2(
    metric=embedding_quality_metric,
    auto="medium",
    num_threads=4
)

optimized_module = optimizer.compile(
    WorkflowEmbeddingOptimizer(),
    trainset=trainset[:10],  # Start small
    max_bootstrapped_demos=3,
    max_labeled_demos=2
)

# Save optimized module
optimized_module.save("workflow_optimizer_v01.json")
```

### Step 5.3: Generate v01 Embeddings
```python
# Process all workflows with optimized DSPy module
for workflow in workflows:
    result = optimized_module(
        workflow_code=workflow['source_code'],
        workflow_metadata=workflow['metadata'],
        analysis=workflow['analysis_v00']
    )
    
    # Create embedding from optimized string
    embedding_v01 = create_embedding(result.embedding_string)
    
    # Store in database
    update_workflow_v01(
        workflow_id=workflow['id'],
        emb_string_01=result.embedding_string,
        dspy_emb_01=embedding_v01,
        test_queries_01=result.test_queries
    )
```

### Step 5.4: Compare v00 vs v01 Performance
```python
def compare_versions():
    results = {
        'v00': evaluate_retrieval('dspy_emb_00'),
        'v01': evaluate_retrieval('dspy_emb_01')
    }
    
    print(f"Version 00 accuracy: {results['v00']['accuracy']}")
    print(f"Version 01 accuracy: {results['v01']['accuracy']}")
    print(f"Improvement: {results['v01']['accuracy'] - results['v00']['accuracy']}")
```

---

## Phase 6: User Feedback Integration (1 week)
**Goal**: Collect real usage data for v02 optimization

### Step 6.1: Create A/B Testing Endpoint
```python
@app.route('/search')
def search_workflows():
    query = request.args.get('query')
    version = request.args.get('version', 'v01')  # Default to best
    
    if version == 'original':
        results = search_original_embeddings(query)
    elif version == 'v00':
        results = search_v00_embeddings(query)
    elif version == 'v01':
        results = search_v01_embeddings(query)
    
    # Log query and results for analysis
    log_search_interaction(query, version, results)
    
    return jsonify(results)
```

### Step 6.2: Collect Click-Through Data
```python
CREATE TABLE search_feedback (
    id UUID PRIMARY KEY,
    query TEXT,
    embedding_version TEXT,
    returned_workflows UUID[],
    clicked_workflow UUID,
    relevance_score INTEGER,  -- User rating 1-5
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Step 6.3: Analyze Feedback for v02
```python
def analyze_search_feedback():
    # Find queries where v01 failed but v00 succeeded
    problem_queries = find_regression_queries()
    
    # Find new query patterns not in training
    novel_queries = find_novel_query_patterns()
    
    # Create enhanced training set for v02
    return create_v02_training_data(problem_queries, novel_queries)
```

---

## Phase 7: Continuous Improvement Pipeline (Ongoing)
**Goal**: Automated improvement cycle

### Step 7.1: Weekly Retraining Script
```python
# cron job: weekly_retrain.py
def weekly_retrain():
    # Get last week's search data
    feedback = get_weekly_feedback()
    
    # Retrain DSPy module with new data
    new_trainset = create_trainset_from_feedback(feedback)
    
    # Create v_next (v02, v03, etc.)
    next_version = get_next_version_number()
    optimized_module = retrain_dspy(new_trainset)
    
    # Generate embeddings for new version
    generate_version_embeddings(next_version, optimized_module)
    
    # A/B test new version vs current best
    run_ab_test(next_version)
```

### Step 7.2: Performance Dashboard
```sql
CREATE VIEW embedding_performance_dashboard AS
SELECT 
    version,
    COUNT(DISTINCT query) as unique_queries,
    AVG(relevance_score) as avg_relevance,
    COUNT(*) as total_searches,
    SUM(CASE WHEN clicked_workflow IS NOT NULL THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as ctr
FROM search_feedback
GROUP BY version
ORDER BY avg_relevance DESC;
```

### Step 7.3: Automated Rollout Decision
```python
def auto_promote_best_version():
    # Get performance metrics for all versions
    metrics = get_version_metrics(min_searches=100)
    
    # Find best performing version
    best_version = max(metrics, key=lambda x: x['weighted_score'])
    
    # Update default search to use best version
    if best_version['improvement'] > 0.05:  # 5% improvement threshold
        set_default_search_version(best_version['version'])
        notify_team(f"Promoted {best_version['version']} as default")
```

---

## Phase 8: Advanced Optimizations (Future)
**Goal**: Domain-specific improvements

### Step 8.1: Package-Specific Embeddings
```python
# Create specialized embeddings for package types
package_specific_fields = {
    'WEL': ['pumping_rate', 'well_efficiency', 'screen_intervals'],
    'RIV': ['conductance', 'stage', 'riverbed_thickness'],
    'GWT': ['species', 'dispersion', 'sorption', 'decay']
}
```

### Step 8.2: Complexity-Aware Embeddings
```python
# Different embedding strategies by complexity
beginner_emphasis = ['step_by_step', 'basic_concepts', 'common_errors']
advanced_emphasis = ['optimization', 'performance', 'numerical_stability']
```

### Step 8.3: Multi-Modal Embeddings
```python
# Combine code, text, and visualization embeddings
visual_features = extract_plot_characteristics(workflow)
combined_embedding = concatenate([
    text_embedding * 0.7,
    code_ast_embedding * 0.2,
    visual_embedding * 0.1
])
```

---

## Success Metrics

### Short-term (Phases 1-3)
- ✅ Database schema updated with versioned columns
- ✅ All workflows have analysis_v00 and emb_string_00
- ✅ Baseline performance measured

### Medium-term (Phases 4-5)
- ✅ DSPy module trained and optimized
- ✅ v01 shows >20% improvement over v00
- ✅ Search accuracy >80% for test queries

### Long-term (Phases 6-8)
- ✅ Automated retraining pipeline active
- ✅ User satisfaction scores >4.5/5
- ✅ Domain-specific optimizations deployed
- ✅ System self-improves weekly

---

## Risk Mitigation

### Rollback Strategy
```sql
-- Keep original embeddings intact
-- Can instantly rollback to any version
UPDATE search_config 
SET active_embedding_column = 'embedding'  -- Original
WHERE service = 'workflow_search';
```

### Cost Control
- Process in batches of 5-10 workflows
- Use GPT-4o-mini for DSPy optimization
- Cache embeddings aggressively
- Monitor API costs daily

### Quality Assurance
- Never delete original embeddings
- Require minimum 100 searches before promotion
- Manual review of dramatic changes
- Automated regression testing

---

## Implementation Timeline

**Week 1**: Phases 1-3 (Database prep, analysis generation, baseline)
**Week 2**: Phases 4-5 (DSPy setup and optimization)
**Week 3**: Phase 6 (Deploy v01, collect feedback)
**Week 4**: Phase 7 (First automated retrain cycle)
**Ongoing**: Phase 8 (Advanced optimizations as needed)

---

## Next Immediate Steps

1. **Today**: Run Phase 1 database updates via Neon MCP
2. **Tomorrow**: Start Phase 2 analysis generation with 5 workflows
3. **Day 3**: Complete Phase 2 for all workflows
4. **Day 4**: Run Phase 3 baseline testing
5. **Day 5**: Begin DSPy optimization

This roadmap provides a safe, incremental path from poor embeddings to a self-improving semantic search system, with careful versioning and rollback capabilities at every step.