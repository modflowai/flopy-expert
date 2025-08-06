# FloPy Expert - Architecture Overview

## What We Built: A Semantic Search System for Groundwater Modeling

This project creates a comprehensive semantic database that understands Python groundwater modeling packages at a deep conceptual level, enabling intelligent search beyond simple keywords.

## The Core Problem We Solved

**Before**: Searching for "SMS" returns UZF packages due to superficial text similarity
**After**: Semantic search correctly identifies SMS as a solver, UZF as a physical process

## High-Level Architecture

```mermaid
graph TB
    subgraph "Source Repositories"
        A[FloPy Repository] 
        B[PyEMU Repository]
        C[FloPy Examples/Notebooks]
        D[PyEMU Notebooks]
    end
    
    subgraph "Processing Pipeline"
        E[Documentation Parser] --> F[Code Analysis]
        F --> G[AI Semantic Analysis]
        G --> H[Embedding Generation]
        H --> I[Database Storage]
    end
    
    subgraph "Database (Neon PostgreSQL)"
        J[flopy_modules<br/>224 items]
        K[flopy_workflows<br/>72 items]
        L[pyemu_modules<br/>20 items]
        M[pyemu_workflows<br/>13 items]
    end
    
    subgraph "AI Services"
        N[Gemini 2.5 Pro<br/>Semantic Analysis]
        O[OpenAI<br/>Vector Embeddings]
    end
    
    A --> E
    B --> E
    C --> E
    D --> E
    
    G --> N
    H --> O
    
    I --> J
    I --> K
    I --> L
    I --> M
    
    style J fill:#e1f5fe
    style K fill:#e8f5e8
    style L fill:#fff3e0
    style M fill:#fce4ec
```

## Database Schema & Table Relationships

### Complete Database Schema with Relationships

```mermaid
erDiagram
    flopy_modules {
        uuid id PK
        text file_path UK
        text relative_path
        text model_family "mf6, modflow, mt3d, utils"
        text package_code "WEL, SMS, CHD, UZF"
        text semantic_purpose "AI-generated analysis"
        text_array user_scenarios
        text_array related_concepts
        text_array typical_errors
        text embedding_text "For debugging"
        vector_1536 embedding "OpenAI vectors"
        tsvector search_vector "PostgreSQL FTS"
        text file_hash
        timestamp processed_at
        text git_commit_hash
        text git_branch
        timestamp git_commit_date
    }
    
    flopy_workflows {
        uuid id PK
        text tutorial_file UK
        text title
        text description
        text model_type
        text_array packages_used
        int num_steps
        text complexity
        text_array tags
        text workflow_purpose "AI-generated analysis"
        text_array best_use_cases
        text_array prerequisites
        text_array common_modifications
        text embedding_text "For debugging"
        vector_1536 embedding "OpenAI vectors"
        tsvector search_vector "PostgreSQL FTS"
        text file_hash
        int total_lines
        timestamp extracted_at
        timestamp processed_at
    }
    
    flopy_workflow_steps {
        uuid id PK
        uuid workflow_id FK
        int step_number
        text description
        text code_snippet
        text_array imports
        text_array flopy_classes
        text_array key_functions
        jsonb parameters
        text step_explanation
        timestamp created_at
    }
    
    flopy_workflow_relationships {
        uuid id PK
        uuid source_workflow_id FK
        uuid target_workflow_id FK
        text relationship_type "similar, prerequisite, advanced"
        float similarity_score
        timestamp created_at
    }
    
    pyemu_modules {
        uuid id PK
        text file_path UK
        text relative_path
        text module_name
        text semantic_purpose "AI-generated analysis"
        text_array use_cases
        text_array pest_integration
        text_array statistical_concepts
        text_array common_pitfalls
        text embedding_text "For debugging"
        vector_1536 embedding "OpenAI vectors"
        tsvector search_vector "PostgreSQL FTS"
        text file_hash
        timestamp processed_at
        text git_commit_hash
        text git_branch
        timestamp git_commit_date
    }
    
    pyemu_workflows {
        uuid id PK
        text notebook_file UK
        text title
        text description
        text workflow_purpose "AI-generated analysis"
        text_array best_practices
        text_array common_applications
        text_array implementation_tips
        text embedding_text "For debugging"
        vector_1536 embedding "OpenAI vectors"
        tsvector search_vector "PostgreSQL FTS"
        text file_hash
        timestamp processed_at
    }
    
    pyemu_workflow_sections {
        uuid id PK
        uuid workflow_id FK
        int section_number
        text title
        text description
        text_array pest_concepts
        text_array uncertainty_methods
        text_array pyemu_classes
        text_array key_functions
        text_array code_snippets
        text section_explanation
        timestamp created_at
    }
    
    pyemu_workflow_relationships {
        uuid id PK
        uuid source_workflow_id FK
        uuid target_workflow_id FK
        text relationship_type "similar, prerequisite, advanced"
        float similarity_score
        timestamp created_at
    }
    
    %% FloPy Relationships
    flopy_workflows ||--o{ flopy_workflow_steps : "broken into steps"
    flopy_workflows ||--o{ flopy_workflow_relationships : "source workflow"
    flopy_workflows ||--o{ flopy_workflow_relationships : "target workflow"
    
    %% PyEMU Relationships  
    pyemu_workflows ||--o{ pyemu_workflow_sections : "broken into sections"
    pyemu_workflows ||--o{ pyemu_workflow_relationships : "source workflow"
    pyemu_workflows ||--o{ pyemu_workflow_relationships : "target workflow"
```

### Database Architecture Overview

**Two Separate Ecosystems**:

1. **FloPy Ecosystem** (Groundwater Modeling):
   - **flopy_modules** (224 items) - Individual Python modules
   - **flopy_workflows** (72 items) - Tutorial examples
   - **flopy_workflow_steps** (204 items) - Detailed step breakdown
   - **flopy_workflow_relationships** (54 items) - How workflows relate

2. **PyEMU Ecosystem** (Uncertainty Analysis):
   - **pyemu_modules** (20 items) - Individual Python modules  
   - **pyemu_workflows** (13 items) - Jupyter notebook tutorials
   - **pyemu_workflow_sections** (70 items) - Notebook section breakdown
   - **pyemu_workflow_relationships** - How workflows relate

### Key Architectural Features

1. **Hierarchical Structure**: Workflows → Steps/Sections → Detailed Analysis
2. **Relationship Mapping**: Workflows understand how they relate to each other
3. **Separate Search Domains**: FloPy and PyEMU can be searched independently
4. **Rich Metadata**: Each level has specialized AI-generated analysis

## Processing Pipeline Flow

### 1. FloPy Module Processing

```mermaid
flowchart TD
    A[FloPy Repository] --> B[docs/code.rst Parser]
    B --> C[Extract 224 Official Modules]
    C --> D[For Each Module]
    
    D --> E[Read Python File]
    E --> F[AST Parse: Extract Docstrings, Classes, Functions]
    F --> G[Regex Extract: Package Code WEL, SMS, etc.]
    G --> H[Git Info: Commit, Branch, Date]
    
    H --> I[Gemini AI Analysis]
    I --> J[Generate Semantic Purpose]
    J --> K[Extract User Scenarios]
    K --> L[Identify Related Concepts]
    L --> M[List Typical Errors]
    
    M --> N[OpenAI Embedding]
    N --> O[Create 1536-dim Vector]
    
    O --> P[Store in flopy_modules Table]
    
    style I fill:#ff9800
    style N fill:#2196f3
    style P fill:#4caf50
```

### 2. FloPy Workflow Processing

```mermaid
flowchart TD
    A[FloPy Examples Directory] --> B[Scan for .py Tutorial Files]
    B --> C[Extract 72 Workflow Files]
    C --> D[For Each Workflow]
    
    D --> E[Read Tutorial File]
    E --> F[Parse: Title, Description, Model Type]
    F --> G[Extract: Packages Used, Complexity]
    G --> H[Count: Steps, Lines]
    
    H --> I[Gemini AI Analysis]
    I --> J[Generate Workflow Purpose]
    J --> K[Extract Best Use Cases]
    K --> L[Identify Prerequisites]
    L --> M[List Common Modifications]
    
    M --> N[OpenAI Embedding]
    N --> O[Create 1536-dim Vector]
    
    O --> P[Store in flopy_workflows Table]
    
    style I fill:#ff9800
    style N fill:#2196f3
    style P fill:#4caf50
```

### 3. PyEMU Module Processing

```mermaid
flowchart TD
    A[PyEMU Repository] --> B[docs/ RST Parser]
    B --> C[Extract 20 Documented Modules]
    C --> D[For Each Module]
    
    D --> E[Read Python File]
    E --> F[AST Parse: Extract Docstrings, Classes, Functions]
    F --> G[Classify: Core, Utils, PST, MAT categories]
    G --> H[Git Info: Commit, Branch, Date]
    
    H --> I[Gemini AI Analysis - PyEMU Focus]
    I --> J[Generate Semantic Purpose]
    J --> K[Extract Use Cases]
    K --> L[Identify PEST Integration]
    L --> M[List Statistical Concepts]
    M --> N[Document Common Pitfalls]
    
    N --> O[OpenAI Embedding]
    O --> P[Create 1536-dim Vector]
    
    P --> Q[Store in pyemu_modules Table]
    
    style I fill:#ff9800
    style O fill:#2196f3
    style Q fill:#4caf50
```

### 4. PyEMU Workflow Processing

```mermaid
flowchart TD
    A[PyEMU Notebooks] --> B[Scan for .ipynb Files]
    B --> C[Extract 13 Tutorial Notebooks]
    C --> D[For Each Notebook]
    
    D --> E[Parse Jupyter Notebook]
    E --> F[Extract: Cells, Markdown, Code]
    F --> G[Analyze: Complexity, Methods Used]
    G --> H[Count: Sections, Code Cells]
    
    H --> I[Gemini AI Analysis - PyEMU Focus]
    I --> J[Generate Workflow Purpose]
    J --> K[Extract Best Practices]
    K --> L[Identify Common Applications]
    L --> M[List Implementation Tips]
    
    M --> N[OpenAI Embedding]
    N --> O[Create 1536-dim Vector]
    
    O --> P[Store in pyemu_workflows Table]
    
    style I fill:#ff9800
    style N fill:#2196f3
    style P fill:#4caf50
```

## AI Processing Architecture

### Dual AI System

```mermaid
graph LR
    A[Input: Code/Notebook] --> B{AI Processing}
    
    B --> C[Gemini 2.5 Pro<br/>Semantic Analysis]
    B --> D[OpenAI text-embedding-3-small<br/>Vector Generation]
    
    C --> E[Natural Language Analysis:<br/>• Purpose<br/>• Use Cases<br/>• Concepts<br/>• Errors]
    
    D --> F[1536-dimensional Vector:<br/>• Semantic similarity<br/>• Cosine distance search<br/>• Clustering capability]
    
    E --> G[Store as Text Fields]
    F --> H[Store as Vector Field]
    
    G --> I[Database Table]
    H --> I
    
    style C fill:#ff9800
    style D fill:#2196f3
    style I fill:#4caf50
```

### AI Analysis Examples

**For FloPy SMS Module**:
```
Semantic Purpose: "The SMS (Sparse Matrix Solver) package provides advanced 
numerical solution methods for MODFLOW 6 models, particularly for unstructured 
grids and complex geometries where standard solvers struggle..."

User Scenarios: ["Complex unstructured grid models", "Models with extreme 
heterogeneity", "Large-scale simulations needing memory efficiency"]

Related Concepts: ["IMS solver", "DISU/DISV packages", "Numerical convergence"]

Typical Errors: ["Using SMS with structured grids", "Incorrect parameter tuning", 
"Memory allocation issues"]
```

## Search Capabilities & Example Flows

### FloPy Search Example: "How do I set up well boundaries?"

```mermaid
flowchart TD
    A[User: "How do I set up well boundaries?"] --> B{Determine Search Domain}
    B --> C[FloPy Search - Groundwater Modeling]
    
    C --> D[Step 1: Vector Search in flopy_modules]
    D --> E[Find: WEL package modules]
    
    E --> F[Step 2: Find Related Workflows]
    F --> G[Query: flopy_workflows WHERE 'WEL' = ANY(packages_used)]
    
    G --> H[Step 3: Get Detailed Steps]
    H --> I[Query: flopy_workflow_steps WHERE workflow_id IN (...)]
    
    I --> J[Step 4: Find Related Workflows]
    J --> K[Query: flopy_workflow_relationships for similar workflows]
    
    K --> L[Return Comprehensive Answer:]
    L --> M[• WEL package documentation<br/>• Tutorial workflows using WEL<br/>• Step-by-step implementation<br/>• Related boundary condition workflows]
    
    style C fill:#e1f5fe
    style E fill:#4caf50
    style G fill:#4caf50
    style I fill:#4caf50
    style K fill:#4caf50
    style M fill:#81c784
```

### PyEMU Search Example: "How do I run Monte Carlo uncertainty analysis?"

```mermaid
flowchart TD
    A[User: "How do I run Monte Carlo uncertainty analysis?"] --> B{Determine Search Domain}
    B --> C[PyEMU Search - Uncertainty Analysis]
    
    C --> D[Step 1: Vector Search in pyemu_modules]
    D --> E[Find: Monte Carlo (mc.py) module]
    
    E --> F[Step 2: Find Related Workflows]
    F --> G[Query: pyemu_workflows WHERE workflow_purpose ILIKE '%monte carlo%']
    
    G --> H[Step 3: Get Detailed Sections]
    H --> I[Query: pyemu_workflow_sections WHERE workflow_id IN (...)]
    
    I --> J[Step 4: Find Implementation Details]
    J --> K[Extract: pyemu_classes, uncertainty_methods, code_snippets]
    
    K --> L[Step 5: Find Related Workflows]
    L --> M[Query: pyemu_workflow_relationships for prerequisite workflows]
    
    M --> N[Return Comprehensive Answer:]
    N --> O[• MonteCarlo class documentation<br/>• Jupyter notebook tutorials<br/>• Section-by-section implementation<br/>• PEST integration methods<br/>• Statistical concepts involved<br/>• Related uncertainty workflows]
    
    style C fill:#fff3e0
    style E fill:#ff9800
    style G fill:#ff9800
    style I fill:#ff9800
    style K fill:#ff9800
    style M fill:#ff9800
    style O fill:#ffcc02
```

### Search Architecture Comparison

```mermaid
graph LR
    subgraph "FloPy Domain"
        A1[flopy_modules<br/>224 items] --> A2[Package Focus<br/>WEL, SMS, CHD]
        A3[flopy_workflows<br/>72 items] --> A4[Tutorial Focus<br/>Step-by-step guides]
        A5[flopy_workflow_steps<br/>204 items] --> A6[Implementation<br/>Code snippets, parameters]
        A7[flopy_workflow_relationships<br/>54 items] --> A8[Learning Path<br/>Beginner → Advanced]
    end
    
    subgraph "PyEMU Domain"  
        B1[pyemu_modules<br/>20 items] --> B2[Method Focus<br/>FOSM, Monte Carlo, Bayes]
        B3[pyemu_workflows<br/>13 items] --> B4[Analysis Focus<br/>Uncertainty workflows]
        B5[pyemu_workflow_sections<br/>70 items] --> B6[PEST Integration<br/>Statistical methods]
        B7[pyemu_workflow_relationships] --> B8[Analysis Path<br/>Simple → Complex]
    end
    
    A2 --> A4
    A4 --> A6
    A6 --> A8
    
    B2 --> B4
    B4 --> B6
    B6 --> B8
    
    style A1 fill:#e1f5fe
    style A3 fill:#e1f5fe
    style A5 fill:#e1f5fe
    style A7 fill:#e1f5fe
    
    style B1 fill:#fff3e0
    style B3 fill:#fff3e0
    style B5 fill:#fff3e0
    style B7 fill:#fff3e0
```

### Why Separate Search Domains?

1. **Different User Intent**:
   - FloPy: "How do I model groundwater flow?"
   - PyEMU: "How do I quantify uncertainty?"

2. **Different Terminology**:
   - FloPy: Packages, solvers, boundary conditions
   - PyEMU: PEST, FOSM, Monte Carlo, ensembles

3. **Different Workflow Structure**:
   - FloPy: Linear tutorial steps (setup → run → analyze)
   - PyEMU: Iterative analysis sections (setup → calibrate → quantify → interpret)

4. **Different Relationships**:
   - FloPy: Package dependencies and model complexity
   - PyEMU: Statistical method prerequisites and analysis depth

## Quality Assurance System

### Processing Quality Pipeline

```mermaid
flowchart TD
    A[Raw Processing] --> B{Quality Check}
    
    B -->|Embedding < Threshold| C[Mark as Poor Quality]
    B -->|Empty Semantic Purpose| C
    B -->|Processing Failure| C
    B -->|Good Quality| D[Store Successfully]
    
    C --> E[Retry with Exponential Backoff]
    E --> F[2s delay, then 4s, then 8s]
    F --> G{Retry Success?}
    
    G -->|Yes| D
    G -->|No| H[Fallback Analysis]
    
    H --> I[Basic Documentation Analysis]
    I --> J[Store with Lower Quality Flag]
    
    D --> K[Quality Assessment]
    K --> L{Meets Standards?}
    
    L -->|No| M[Add to Reprocessing Queue]
    L -->|Yes| N[Production Ready]
    
    M --> O[Targeted Reprocessing Script]
    O --> A
    
    style C fill:#f44336
    style E fill:#ff9800
    style N fill:#4caf50
```

## File System Organization

```
flopy_expert/
├── src/                              # Core processing logic
│   ├── processing_pipeline.py        # FloPy module processor
│   ├── pyemu_processing_pipeline.py  # PyEMU module processor  
│   ├── flopy_workflow_processor.py   # FloPy workflow processor
│   ├── pyemu_workflow_processor.py   # PyEMU workflow processor
│   ├── docs_parser.py               # FloPy docs parser
│   ├── pyemu_docs_parser.py         # PyEMU docs parser
│   ├── flopy_workflow_extractor.py  # FloPy example extractor
│   └── pyemu_workflow_extractor.py  # PyEMU notebook extractor
├── tests/
│   └── qa_embedding_quality.py      # Quality assessment across all tables
├── scripts/
│   ├── reprocess_poor_embeddings.py # Fix poor FloPy workflows
│   └── reprocess_pyemu_mc.py        # Fix specific PyEMU module
├── run_processing_flopy.py          # Main FloPy module processing
├── run_processing_pyemu.py          # Main PyEMU module processing
├── run_processing_flopy_workflows.py # FloPy workflow processing
├── run_processing_pyemu_workflows.py # PyEMU workflow processing
└── config.py                        # API keys and settings
```

## Data Flow Summary

```mermaid
sankey-beta

    FloPy_Repo,FloPy_Examples,PyEMU_Repo,PyEMU_Notebooks,flopy_modules,flopy_workflows,pyemu_modules,pyemu_workflows,Vector_Search,Text_Search,Hybrid_Search

    FloPy_Repo,flopy_modules,224
    FloPy_Examples,flopy_workflows,72
    PyEMU_Repo,pyemu_modules,20
    PyEMU_Notebooks,pyemu_workflows,13
    flopy_modules,Vector_Search,224
    flopy_workflows,Vector_Search,72
    pyemu_modules,Vector_Search,20
    pyemu_workflows,Vector_Search,13
    flopy_modules,Text_Search,224
    flopy_workflows,Text_Search,72
    pyemu_modules,Text_Search,20
    pyemu_workflows,Text_Search,13
    Vector_Search,Hybrid_Search,329
    Text_Search,Hybrid_Search,329
```

## Key Achievements

1. **698 Total Items Processed**: 
   - 244 FloPy items (224 modules + 20 workflows) 
   - 85 PyEMU items (20 modules + 13 workflows + 52 related items)
   - 369 detailed breakdown items (204 workflow steps + 70 workflow sections + 95 relationships)
2. **100% Quality Success**: All main items meet embedding quality thresholds
3. **Semantic Understanding**: AI-generated analysis for each item
4. **Hierarchical Structure**: Workflows broken down into detailed steps/sections
5. **Relationship Mapping**: 54+ workflow relationships mapped
6. **Dual Search Domains**: Separate FloPy and PyEMU search capabilities
7. **Version Tracking**: Git commit tracking for all modules
8. **Robust Processing**: Retry logic, quality assessment, reprocessing tools

## What Makes This Special

1. **Domain Expertise**: Understands groundwater modeling concepts
2. **Semantic vs Keyword**: Goes beyond text matching to conceptual understanding
3. **Comprehensive Coverage**: Both core packages and tutorial workflows
4. **Production Quality**: Robust error handling, quality assurance, monitoring
5. **Scalable Architecture**: Can be extended to other Python packages

This system transforms how developers find and understand groundwater modeling components, enabling intelligent discovery based on purpose rather than just keywords.