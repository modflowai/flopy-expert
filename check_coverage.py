#!/usr/bin/env python3
"""Check which FloPy modules were processed vs which exist"""

import psycopg2
import config
from pathlib import Path

# Directory file counts from filesystem
filesystem_counts = {
    'mf6': 140,
    'modflow': 51,
    'utils': 38,
    'mt3d': 14,
    'mfusg': 10,  # NOT PROCESSED!
    'modpath': 9,
    'export': 8,
    'discretization': 6,
    'plot': 5,
    'pest': 4,
    'seawat': 4,
    'modflowlgr': 2,  # NOT PROCESSED!
}

# Get processed counts from database
with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT model_family, COUNT(*) 
            FROM flopy_modules 
            GROUP BY model_family
        """)
        db_counts = dict(cur.fetchall())

print("FLOPY MODULE COVERAGE ANALYSIS")
print("=" * 50)
print(f"{'Directory':<15} {'Files':<10} {'Processed':<12} {'Coverage':<10}")
print("-" * 50)

total_files = 0
total_processed = 0

for family, file_count in sorted(filesystem_counts.items(), key=lambda x: x[1], reverse=True):
    processed = db_counts.get(family, 0)
    coverage = (processed / file_count * 100) if file_count > 0 else 0
    
    status = ""
    if processed == 0:
        status = " ❌ MISSING"
    elif coverage < 50:
        status = " ⚠️  PARTIAL"
    elif coverage >= 90:
        status = " ✅"
    
    print(f"{family:<15} {file_count:<10} {processed:<12} {coverage:>6.1f}%{status}")
    
    total_files += file_count
    total_processed += processed

print("-" * 50)
print(f"{'TOTAL':<15} {total_files:<10} {total_processed:<12} {total_processed/total_files*100:>6.1f}%")

print("\n\nMISSING DIRECTORIES:")
print("- mfusg (10 files) - MODFLOW-USG including SMS solver")
print("- modflowlgr (2 files) - MODFLOW-LGR (Local Grid Refinement)")

print("\n\nPARTIAL COVERAGE:")
for family, file_count in filesystem_counts.items():
    processed = db_counts.get(family, 0)
    if 0 < processed < file_count * 0.9:
        print(f"- {family}: {processed}/{file_count} files ({processed/file_count*100:.1f}%)")