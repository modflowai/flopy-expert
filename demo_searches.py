#!/usr/bin/env python3
"""
Demo script showing effective searches for the CLI
"""

import asyncio
from search_cli import SemanticSearchCLI


async def run_demo():
    cli = SemanticSearchCLI()
    
    print("🔍 SEMANTIC SEARCH DEMO")
    print("=" * 50)
    
    demos = [
        ("FloPy", "well boundaries", "Shows WEL package and related workflows"),
        ("FloPy", "drain package", "Shows DRN package documentation"),
        ("FloPy", "solver convergence", "Shows solver-related modules"),
        ("PyEMU", "monte carlo", "Shows Monte Carlo uncertainty analysis"),
        ("PyEMU", "parameter estimation", "Shows PEST calibration workflows"),
        ("PyEMU", "uncertainty quantification", "Shows uncertainty analysis methods"),
    ]
    
    for domain, query, description in demos:
        print(f"\n{'='*80}")
        print(f"DEMO: {domain.upper()} - '{query}'")
        print(f"Expected: {description}")
        print('='*80)
        
        if domain == "FloPy":
            result = await cli.comprehensive_flopy_search(query)
        else:
            result = await cli.comprehensive_pyemu_search(query)
        
        print(result)
        
        # Wait for user input to continue
        input("\nPress Enter to continue to next demo...")


if __name__ == "__main__":
    asyncio.run(run_demo())