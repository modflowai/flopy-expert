"""
V02 Ultra-Discriminative Pipeline Configuration
Central configuration for the production v02 embedding pipeline
"""

from pathlib import Path
from typing import Dict, Any

# Version Configuration
PIPELINE_VERSION = "v02"
BASELINE_VERSION = "v00"  # For comparison

# Model Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
ANALYSIS_MODEL = "gemini-2.0-flash-exp"  # Gemini model for analysis

# Database Columns
COLUMNS = {
    "analysis": f"analysis_{PIPELINE_VERSION}",
    "embedding": f"dspy_emb_{PIPELINE_VERSION.replace('v', '')}",  # dspy_emb_02
    "embedding_text": f"emb_string_{PIPELINE_VERSION.replace('v', '')}",  # emb_string_02
    "baseline_embedding": "embedding",  # Original baseline
}

# Processing Configuration
BATCH_SIZE = 10
RATE_LIMIT_DELAY = 1.0  # seconds between API calls
MAX_RETRIES = 3
CHECKPOINT_FREQUENCY = 5  # Save checkpoint every N items

# Checkpoint Configuration
CHECKPOINT_DIR = Path("v02_pipeline/checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True, parents=True)

# Logging Configuration
LOG_DIR = Path("v02_pipeline/logs")
LOG_DIR.mkdir(exist_ok=True, parents=True)
LOG_LEVEL = "INFO"

# Quality Thresholds
MIN_QUESTIONS_PER_WORKFLOW = 8
MAX_QUESTIONS_PER_WORKFLOW = 15
MIN_EMBEDDING_TEXT_LENGTH = 500

# Repository Configuration
REPOSITORIES = {
    "flopy": {
        "table": "flopy_workflows",
        "filter": "source_repository = 'flopy'",
        "expected_count": 72
    },
    "modflow6-examples": {
        "table": "flopy_workflows", 
        "filter": "source_repository = 'modflow6-examples'",
        "expected_count": 73
    },
    "pyemu": {
        "table": "pyemu_workflows",
        "filter": None,  # No filter needed
        "expected_count": 13
    }
}

# Pipeline Stages
STAGES = [
    "analysis_generation",
    "embedding_creation",
    "quality_validation"
]

def get_table_config(repository: str) -> Dict[str, Any]:
    """Get configuration for a specific repository"""
    if repository not in REPOSITORIES:
        raise ValueError(f"Unknown repository: {repository}. Valid: {list(REPOSITORIES.keys())}")
    return REPOSITORIES[repository]

def get_column_name(column_type: str) -> str:
    """Get the database column name for a given type"""
    if column_type not in COLUMNS:
        raise ValueError(f"Unknown column type: {column_type}. Valid: {list(COLUMNS.keys())}")
    return COLUMNS[column_type]