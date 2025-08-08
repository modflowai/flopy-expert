"""
FloPy Ultra-Discriminative Prompt Templates
Prompts specifically designed for FloPy/MODFLOW workflows
"""

FLOPY_ULTRA_DISCRIMINATIVE_PROMPT = """You are an expert MODFLOW modeler analyzing FloPy tutorial workflows.

WORKFLOW: {tutorial_file}
TITLE: {title}
PACKAGES: {packages_used}
MODEL TYPE: {model_type}

CRITICAL REQUIREMENT: Generate ULTRA-DISCRIMINATIVE technical questions that are IMPOSSIBLE to answer correctly 
without understanding THIS SPECIFIC workflow's implementation details.

Your questions must differentiate between:
1. MODFLOW VERSIONS: MODFLOW-2005 vs MODFLOW-6 vs MODFLOW-NWT vs MODFLOW-USG
2. PACKAGE IMPLEMENTATIONS: Same package code but different implementations (e.g., WEL in MF2005 vs MF6)
3. SOLVER CONFIGURATIONS: PCG vs GMG vs SMS/IMS with specific settings
4. GRID TYPES: Regular DIS vs vertex DISV vs unstructured DISU
5. FLOPY METHODS: High-level convenience methods vs low-level array manipulation

FORCE DIFFERENTIATION by including:
- Specific FloPy class names and method signatures
- Exact array dimensions and shapes used
- Package-specific parameter names and units
- Version-specific keyword arguments
- Grid discretization details unique to this example

Generate a JSON with:
{{
    "workflow_purpose": "Ultra-specific purpose mentioning exact packages and methods",
    "discriminative_questions": [10 ultra-specific technical questions],
    "key_differentiators": ["What makes this unique from similar workflows"],
    "modflow_version_specifics": ["Version-specific implementation details"],
    "package_implementations": ["How packages are specifically configured"],
    "flopy_methods_used": ["Specific FloPy methods and their parameters"]
}}

EXAMPLES OF ULTRA-DISCRIMINATIVE QUESTIONS:
- "In this MF6 workflow, how does ModflowGwfdis handle cell2d array construction for DISV?"
- "What specific IMS outer_maximum value does this tutorial use for PCG convergence?"
- "How does this workflow's flopy.mf6.ModflowGwfnpf rewetting differ from UPW?"
- "What is the exact shape of the stress_period_data recarray for the WEL package here?"
- "Which flopy.utils.binaryfile method reads the CBC file in this specific example?"

Make questions so specific that ONLY someone who has studied THIS EXACT workflow could answer."""

MODFLOW6_EXAMPLES_PROMPT = """You are an expert analyzing official MODFLOW 6 example problems.

EXAMPLE: {tutorial_file}
TITLE: {title}
PURPOSE: {workflow_purpose}

These are OFFICIAL MODFLOW 6 examples, not tutorials. They demonstrate specific features and capabilities.

CRITICAL: Generate questions that distinguish THIS example from other MODFLOW 6 examples.

Focus on:
1. UNIQUE FEATURES demonstrated (not found in other examples)
2. SPECIFIC PROBLEM SETUP (boundary conditions, domain, parameters)
3. ADVANCED PACKAGES used (not common ones)
4. NUMERICAL METHODS specific to this problem
5. VALIDATION/COMPARISON aspects if present

Generate a JSON with:
{{
    "workflow_purpose": "What specific MODFLOW 6 feature this example demonstrates",
    "discriminative_questions": [10 ultra-specific questions about THIS example],
    "key_differentiators": ["Unique aspects not found in other examples"],
    "advanced_features": ["Advanced MODFLOW 6 features used"],
    "problem_specifics": ["Specific problem setup details"],
    "validation_aspects": ["How results are validated or compared"]
}}"""

# Required fields for validation
FLOPY_REQUIRED_FIELDS = [
    "workflow_purpose",
    "discriminative_questions",
    "key_differentiators"
]

def get_prompt_for_repository(repo: str) -> str:
    """Get the appropriate prompt template for a repository"""
    if repo == "modflow6-examples":
        return MODFLOW6_EXAMPLES_PROMPT
    else:  # flopy
        return FLOPY_ULTRA_DISCRIMINATIVE_PROMPT

def format_workflow_for_prompt(workflow: dict, repo: str) -> dict:
    """Format workflow data for use in prompt template"""
    # Ensure all required fields exist
    formatted = {
        'tutorial_file': workflow.get('tutorial_file', workflow.get('file', 'unknown')),
        'title': workflow.get('title', 'Unknown Title'),
        'model_type': workflow.get('model_type', 'Unknown'),
        'workflow_purpose': workflow.get('workflow_purpose', 'General workflow')
    }
    
    # Handle packages_used
    packages = workflow.get('packages_used', [])
    if packages:
        formatted['packages_used'] = ', '.join(packages[:10])  # Limit to 10
    else:
        formatted['packages_used'] = 'Various packages'
    
    return formatted