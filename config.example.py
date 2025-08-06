#!/usr/bin/env python3
"""
Configuration file for FloPy Semantic Database Processing

Copy this to config.py and fill in your actual credentials
"""

# Neon PostgreSQL connection
NEON_CONNECTION_STRING = "postgresql://username:password@ep-example.us-east-2.aws.neon.tech/neondb?sslmode=require"

# API Keys
GEMINI_API_KEY = "your_gemini_api_key_here"
OPENAI_API_KEY = "your_openai_api_key_here"

# Model Selection
GEMINI_MODEL = "gemini-2.5-flash"  # Options: gemini-2.5-flash, gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions, cost-effective

# Processing settings
BATCH_SIZE = 10  # Number of files to process per batch
RATE_LIMIT_DELAY = 0.5  # Seconds between API calls
BATCH_DELAY = 2.0  # Seconds between batches

# Repository path
REPO_PATH = "/home/danilopezmella/flopy_expert"

# Enable/disable features for testing
ENABLE_GEMINI_ANALYSIS = True
ENABLE_OPENAI_EMBEDDINGS = True
ENABLE_DATABASE_SAVE = True
ENABLE_CHECKPOINTS = True