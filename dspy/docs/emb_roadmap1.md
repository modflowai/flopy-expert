DSPy FLOPY Embedding Optimization Roadmap (Correct Neon Usage)
Step 1: Database Setup with psycopg2 and pgvector
pythonimport psycopg2
from psycopg2.extras import RealDictCursor
import openai
import dspy
import numpy as np

# Connect to Neon using standard PostgreSQL connection
conn = psycopg2.connect(
    host="your-neon-host.aws.neon.tech",
    database="your-db", 
    user="your-user",
    password="your-password",
    sslmode="require"
)

# Enable pgvector extension
with conn.cursor() as cur:
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Add columns for optimized embeddings
    cur.execute("ALTER TABLE your_table ADD COLUMN IF NOT EXISTS dsp_emb_1 TEXT")
    cur.execute("ALTER TABLE your_table ADD COLUMN IF NOT EXISTS dsp_emb_1_vector vector(1536)")  # OpenAI dimensions
    
    conn.commit()

# Fetch all code examples
with conn.cursor(cursor_factory=RealDictCursor) as cur:
    cur.execute("SELECT id, source_code FROM your_table WHERE source_code IS NOT NULL")
    code_examples = cur.fetchall()

print(f"Found {len(code_examples)} code examples")
Step 2: DSPy System Setup
python# Configure DSPy
dspy.configure(lm=dspy.LM('openai/gpt-4o-mini'))

class EmbeddingStringGenerator(dspy.Signature):
    """Generate optimal embedding description from FLOPY code"""
    code = dspy.InputField(desc="FLOPY/MODFLOW Python code")
    embedding_string = dspy.OutputField(desc="Rich semantic description for optimal retrieval")

class TestQueryGenerator(dspy.Signature): 
    """Generate realistic test queries that should retrieve this code"""
    code = dspy.InputField(desc="FLOPY/MODFLOW Python code")
    test_queries = dspy.OutputField(desc="List of realistic user questions, one per line")

class EmbeddingOptimizer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.embedding_gen = dspy.ChainOfThought(EmbeddingStringGenerator)
        self.query_gen = dspy.ChainOfThought(TestQueryGenerator)
    
    def forward(self, code):
        embedding_result = self.embedding_gen(code=code)
        query_result = self.query_gen(code=code)
        
        return dspy.Prediction(
            embedding_string=embedding_result.embedding_string,
            test_queries=query_result.test_queries
        )
Step 3: DSPy Training Data & Metric
python# Convert DB records to DSPy examples
trainset = []
for record in code_examples:
    trainset.append(dspy.Example(
        code=record['source_code'],
        id=record['id']
    ).with_inputs('code'))

# Auto-evaluation metric using cosine similarity
def embedding_quality_metric(example, pred):
    """Test if generated embedding + queries work well together"""
    try:
        # Create embedding from DSPy's generated string
        embedding = openai.embeddings.create(
            input=pred.embedding_string,
            model="text-embedding-3-small"
        ).data[0].embedding
        
        # Parse generated queries
        queries = [q.strip() for q in pred.test_queries.split('\n') if q.strip()]
        
        similarities = []
        for query in queries[:5]:  # Limit for cost control
            query_emb = openai.embeddings.create(
                input=query,
                model="text-embedding-3-small"
            ).data[0].embedding
            
            # Calculate cosine similarity
            sim = np.dot(embedding, query_emb) / (np.linalg.norm(embedding) * np.linalg.norm(query_emb))
            similarities.append(sim)
        
        return np.mean(similarities) if similarities else 0.0
        
    except Exception as e:
        print(f"Error in metric: {e}")
        return 0.0
Step 4: DSPy Optimization
python# Create and optimize the system
embedding_optimizer = EmbeddingOptimizer()

# Start with subset for cost control
train_subset = trainset[:10]

optimizer = dspy.MIPROv2(
    metric=embedding_quality_metric,
    auto="medium",
    num_threads=4
)

print("Starting DSPy optimization...")
optimized_system = optimizer.compile(
    embedding_optimizer,
    trainset=train_subset,
    max_bootstrapped_demos=3,
    max_labeled_demos=2
)

print("Optimization complete!")
Step 5: Generate and Store Optimized Embeddings
python# Generate optimized embedding strings
optimized_embeddings = {}

for record in code_examples:
    try:
        result = optimized_system(code=record['source_code'])
        
        # Generate embedding vector from optimized string
        embedding_vector = openai.embeddings.create(
            input=result.embedding_string,
            model="text-embedding-3-small"
        ).data[0].embedding
        
        optimized_embeddings[record['id']] = {
            'text': result.embedding_string,
            'vector': embedding_vector
        }
        
        print(f"Generated embedding for ID {record['id']}")
        
    except Exception as e:
        print(f"Error processing ID {record['id']}: {e}")

# Update database with both text and vectors
with conn.cursor() as cur:
    for record_id, embedding_data in optimized_embeddings.items():
        cur.execute(
            "UPDATE your_table SET dsp_emb_1 = %s, dsp_emb_1_vector = %s WHERE id = %s",
            (embedding_data['text'], embedding_data['vector'], record_id)
        )
    
    conn.commit()

print("Database updated with optimized embeddings!")
Step 6: Create pgvector Index for Fast Search
python# Create vector index for performance
with conn.cursor() as cur:
    # Create HNSW index (best for high-dimensional vectors)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS dsp_emb_1_hnsw_idx 
        ON your_table 
        USING hnsw (dsp_emb_1_vector vector_cosine_ops)
    """)
    
    conn.commit()

print("Vector index created!")
Step 7: Test Native Neon Vector Search
pythondef neon_semantic_search(query, top_k=3):
    """Use Neon's native pgvector search"""
    # Generate query embedding
    query_embedding = openai.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    ).data[0].embedding
    
    # Use Neon's pgvector cosine similarity search
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, source_code, dsp_emb_1,
                   1 - (dsp_emb_1_vector <=> %s::vector) as similarity
            FROM your_table 
            WHERE dsp_emb_1_vector IS NOT NULL
            ORDER BY dsp_emb_1_vector <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, top_k))
        
        return cur.fetchall()

# Test with sample queries
test_queries = [
    "temperature effects on groundwater flow",
    "viscosity modeling example",
    "heat transport coupling",
    "boundary conditions setup"
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    results = neon_semantic_search(query)
    for result in results:
        print(f"  ID {result['id']}: {result['similarity']:.3f}")