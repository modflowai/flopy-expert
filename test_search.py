#!/usr/bin/env python3
"""Quick test to verify search functionality"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import config
import psycopg2
from openai import AsyncOpenAI


async def test_search():
    # Test basic database queries
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            # Check for SMS modules
            cur.execute("SELECT relative_path, package_code FROM flopy_modules WHERE package_code ILIKE '%SMS%' OR relative_path ILIKE '%sms%'")
            sms_modules = cur.fetchall()
            print(f"SMS modules found: {len(sms_modules)}")
            for module in sms_modules:
                print(f"  - {module[0]} ({module[1]})")
            
            # Check FloPy modules that mention solver
            cur.execute("SELECT relative_path, package_code FROM flopy_modules WHERE semantic_purpose ILIKE '%solver%' LIMIT 5")
            solver_modules = cur.fetchall()
            print(f"\nModules mentioning 'solver': {len(solver_modules)}")
            for module in solver_modules:
                print(f"  - {module[0]} ({module[1]})")
            
            # Test PyEMU Monte Carlo
            cur.execute("SELECT relative_path FROM pyemu_modules WHERE relative_path ILIKE '%mc%'")
            mc_modules = cur.fetchall()
            print(f"\nPyEMU Monte Carlo modules: {len(mc_modules)}")
            for module in mc_modules:
                print(f"  - {module[0]}")


if __name__ == "__main__":
    asyncio.run(test_search())