#!/usr/bin/env python3
"""
LangExtract schema definitions for comprehensive FloPy issue analysis
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


# Example-based schemas for LangExtract
PROBLEM_EXAMPLES = [
    {
        "text": "Mf6Splitter does not work when ATS is active with error 'ModflowUtlats' object has no attribute 'parent_package'",
        "extractions": [{
            "problem_description": "Mf6Splitter does not work when ATS is active",
            "error_message": "'ModflowUtlats' object has no attribute 'parent_package'",
            "error_type": "AttributeError",
            "problem_category": "compatibility"
        }]
    },
    {
        "text": "Only 168 of 235 stress periods are read. The data in model.wel.cln_stress_period_data.data are all zeros",
        "extractions": [{
            "problem_description": "well package is not read correctly",
            "error_message": "Only 168 of 235 stress periods are read",
            "error_type": "incomplete_read",
            "problem_category": "data_loss"
        }]
    }
]

MODULE_EXAMPLES = [
    {
        "text": "Using flopy.mf6.utils.Mf6Splitter to split a model with method split_model() fails when ATS is active",
        "extractions": [{
            "module_type": "primary",
            "module_name": "Mf6Splitter",
            "full_path": "flopy.mf6.utils.Mf6Splitter",
            "method": "split_model"
        }]
    },
    {
        "text": "tdis = flopy.mf6.ModflowTdis(sim, perioddata=[(365.0, 20, 1.2)])",
        "extractions": [{
            "module_type": "code_usage",
            "module_name": "ModflowTdis",
            "full_path": "flopy.mf6.ModflowTdis",
            "context": "time discretization setup"
        }]
    }
]

CODE_SNIPPET_EXAMPLES = [
    {
        "text": "```python\nsim = flopy.mf6.MFSimulation(sim_name=name, sim_ws=ws)\ntdis = flopy.mf6.ModflowTdis(sim, ats_perioddata=[(0, 0.0, 1.0, 30.0, 2.0, 5.0)])\n```",
        "extractions": [{
            "snippet_type": "reproducer",
            "code": "sim = flopy.mf6.MFSimulation(sim_name=name, sim_ws=ws)\ntdis = flopy.mf6.ModflowTdis(sim, ats_perioddata=[(0, 0.0, 1.0, 30.0, 2.0, 5.0)])",
            "key_features": ["ATS configuration", "time discretization"]
        }]
    }
]

RESOLUTION_EXAMPLES = [
    {
        "text": "ATS support has been implemented in develop",
        "extractions": [{
            "resolution_type": "code_fix",
            "description": "ATS support implemented",
            "target_version": "develop",
            "status": "completed"
        }]
    },
    {
        "text": "Data can be read correctly using a venv with flopy=3.3.6, pandas=1.5.3 and numpy=1.21.5",
        "extractions": [{
            "resolution_type": "version_constraint",
            "description": "Use specific versions",
            "requirements": {
                "flopy": "3.3.6",
                "pandas": "1.5.3",
                "numpy": "1.21.5"
            }
        }]
    }
]

ENVIRONMENT_EXAMPLES = [
    {
        "text": "OS: Windows 11, Flopy v3.9.2, MODFLOW v6.6.1",
        "extractions": [{
            "os": "Windows 11",
            "flopy_version": "3.9.2",
            "modflow_version": "6.6.1"
        }]
    }
]

COMMENT_INSIGHT_EXAMPLES = [
    {
        "text": "I'll take a look at this today and try to provide a fix.",
        "extractions": [{
            "comment_type": "developer_response",
            "intent": "acknowledge_and_commit",
            "author_role": "maintainer"
        }]
    },
    {
        "text": "Thanks @jlarsen-usgs! The fix works perfectly now.",
        "extractions": [{
            "comment_type": "user_confirmation",
            "feedback": "positive",
            "confirms_fix": True
        }]
    }
]


class ExtractionPrompts:
    """Prompts for different extraction tasks"""
    
    PROBLEM_EXTRACTION = """
    Extract problem information from this GitHub issue:
    - Main problem description
    - Error messages (exact text)
    - Error types (AttributeError, ValueError, etc.)
    - Symptoms described by user
    - Problem category (compatibility, regression, data_loss, feature_gap)
    """
    
    MODULE_EXTRACTION = """
    Extract all FloPy module references:
    - Primary modules (main subject of issue)
    - Secondary modules (mentioned in code/examples)
    - Import statements with full paths
    - File paths mentioned
    - Methods or attributes accessed
    """
    
    CODE_EXTRACTION = """
    Extract code snippets and categorize them:
    - Reproducer code (minimal example)
    - Workaround code (temporary fix)
    - Solution code (final fix)
    - Test code (validation)
    Include key features of each snippet
    """
    
    RESOLUTION_EXTRACTION = """
    Extract resolution information:
    - Resolution type (code_fix, workaround, version_constraint, configuration, wontfix)
    - Description of fix
    - Target version or branch
    - Required changes
    - Confirmation status
    """
    
    ENVIRONMENT_EXTRACTION = """
    Extract environment and version information:
    - FloPy version
    - MODFLOW version (mf6, mf2005, mfusg, etc.)
    - Python version
    - Operating system
    - Key dependencies and versions
    """
    
    RELATIONSHIP_EXTRACTION = """
    Extract relationships between modules:
    - Incompatible pairs (X doesn't work with Y)
    - Dependencies (X requires Y)
    - Affected by (error in X affects Y)
    - Fixed together (X and Y fixed in same commit)
    Include evidence for each relationship
    """


@dataclass
class ComprehensiveExtraction:
    """Complete extraction result for an issue"""
    issue_number: int
    
    # Problem analysis
    problem_description: str
    error_messages: List[str]
    error_types: List[str]
    symptoms: List[str]
    problem_category: str
    
    # Module identification
    primary_modules: List[Dict[str, str]]
    secondary_modules: List[Dict[str, str]]
    import_statements: List[str]
    file_paths: List[str]
    
    # Code context
    reproducer_code: Optional[str]
    workaround_code: Optional[str]
    solution_code: Optional[str]
    test_code: Optional[str]
    
    # Environment
    flopy_version: Optional[str]
    modflow_version: Optional[str]
    python_version: Optional[str]
    os: Optional[str]
    dependencies: Dict[str, str]
    
    # Resolution
    resolution_type: Optional[str]
    resolution_description: Optional[str]
    fixed_in_version: Optional[str]
    time_to_fix_days: Optional[int]
    
    # Relationships
    module_relationships: List[Dict[str, str]]
    
    # Comment insights
    developer_insights: List[str]
    user_confirmations: List[str]
    related_issues: List[str]
    pr_references: List[str]