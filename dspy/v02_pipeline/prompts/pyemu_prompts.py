"""
PyEMU Ultra-Discriminative Prompt Templates
Prompts specifically designed for uncertainty analysis and PEST workflows
"""

PYEMU_ULTRA_DISCRIMINATIVE_PROMPT = """You are an expert in uncertainty quantification and PEST++ inverse modeling analyzing PyEMU workflows.

WORKFLOW: {notebook_file}
TITLE: {title}
TYPE: {workflow_type}
PEST CONCEPTS: {pest_concepts}
UNCERTAINTY METHODS: {uncertainty_methods}
PYEMU MODULES: {pyemu_modules}

CRITICAL REQUIREMENT: Generate ULTRA-DISCRIMINATIVE technical questions that are IMPOSSIBLE to answer correctly 
without understanding THIS SPECIFIC workflow's implementation details.

Your questions must differentiate between:
1. PEST++ TOOLS: PESTPP-IES vs PESTPP-GLM vs PESTPP-SEN vs PESTPP-SWP vs PESTPP-DA
2. UNCERTAINTY APPROACHES: Monte Carlo vs FOSM vs GLUE vs Null Space Monte Carlo
3. CALIBRATION METHODS: Regularization types (Tikhonov vs SVD-Assist vs Subspace)
4. SENSITIVITY ANALYSES: Morris vs Sobol vs PEST++ DSS vs Method of Morris
5. IMPLEMENTATION STAGES: Prior vs Posterior, Linear vs Nonlinear, First-order vs Second-order

FORCE DIFFERENTIATION by including:
- Specific PyEMU class names and methods (Pst, Schur, EnsembleSmoother, etc.)
- Exact statistical calculations and matrix operations
- PEST control file parameters and settings
- Computational complexity and scaling
- Specific error handling in uncertainty propagation

Generate a JSON with:
{{
    "workflow_purpose": "Ultra-specific purpose focusing on exact statistical method",
    "discriminative_questions": [10 ultra-specific technical questions],
    "key_differentiators": ["What makes this unique from similar workflows"],
    "pest_tool_specifics": ["Exact PEST++ tool configurations used"],
    "statistical_implementation": ["Precise mathematical operations performed"],
    "unique_pyemu_features": ["PyEMU-specific classes and methods used"]
}}

EXAMPLES OF ULTRA-DISCRIMINATIVE QUESTIONS BASED ON KEY DIFFERENTIATORS:

For PESTPP-IES workflows:
- "Which pyemu.ParameterEnsemble method updates realizations using the Kalman gain in this workflow?"
- "How does this workflow's ensemble localization strategy differ from standard EnKF?"
- "What ensemble size vs parameter dimension ratio does this PESTPP-IES implementation use?"

For PESTPP-GLM workflows:
- "How does pyemu.Jco handle the Jacobian matrix scaling before SVD decomposition here?"
- "What regularization weight adjustment does PESTPP-GLM apply after each lambda iteration?"
- "Which pyemu.Schur method calculates the posterior parameter covariance in this workflow?"

For Monte Carlo workflows:
- "How does ParameterEnsemble.from_gaussian_draw() enforce parameter bounds in this prior MC?"
- "What correlation structure does pyemu.Cov.from_parameter_data() impose on the ensemble?"
- "How many realizations are needed for this workflow's Sobol sensitivity convergence?"

For FOSM workflows:
- "What singular value truncation does pyemu.ErrVar apply to the Jacobian before uncertainty propagation?"
- "How does this workflow's Schur complement handle forecast sensitivity calculation?"
- "Which linear assumption violations does this FOSM implementation check for?"

For Schur complement examples:
- "How does pyemu.Schur.get_forecast_summary() handle parameter-to-forecast covariance?"
- "What specific prior information weight does this workflow apply to observations?"
- "How are forecast variances adjusted for nonlinearity in this implementation?"

Make questions so specific that ONLY someone who understands THIS EXACT workflow could answer."""

# Required fields for validation
PYEMU_REQUIRED_FIELDS = [
    "workflow_purpose",
    "discriminative_questions",
    "key_differentiators"
]

def format_workflow_for_prompt(workflow: dict) -> dict:
    """Format PyEMU workflow data for use in prompt template"""
    formatted = {
        'notebook_file': workflow.get('notebook_file', 'unknown'),
        'title': workflow.get('title', 'Unknown Title'),
        'workflow_type': workflow.get('workflow_type', 'uncertainty_analysis')
    }
    
    # Handle arrays
    pest_concepts = workflow.get('pest_concepts', [])
    formatted['pest_concepts'] = ', '.join(pest_concepts) if pest_concepts else 'general PEST concepts'
    
    uncertainty_methods = workflow.get('uncertainty_methods', [])
    formatted['uncertainty_methods'] = ', '.join(uncertainty_methods) if uncertainty_methods else 'various methods'
    
    pyemu_modules = workflow.get('pyemu_modules', [])
    formatted['pyemu_modules'] = ', '.join(pyemu_modules) if pyemu_modules else 'various modules'
    
    return formatted