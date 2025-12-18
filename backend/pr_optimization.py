"""
PR Optimization Logic for Polaris Workflows
Adds polaris_test_sast_type parameter with GitHub expression to optimize SAST scanning for PRs
Only applies SAST_RAPID when PR is opened, synchronized (new commits), or reopened
"""

from typing import Dict
from assessment_logic import AssessmentType, should_include_sast


def generate_polaris_config_with_event_optimization(
    assessment_type: AssessmentType,
    has_pr_trigger: bool = False,
    existing_env: Dict[str, str] = None
) -> Dict[str, str]:
    """
    Generate Polaris environment configuration with PR event optimization
    
    For SAST assessments on workflows with PR triggers, adds:
    POLARIS_TEST_SAST_TYPE: ${{ (github.event_name == 'pull_request' && contains(fromJSON('["opened","synchronize","reopened"]'), github.event.action)) && 'SAST_RAPID' || '' }}
    
    This optimizes Polaris by:
    - Using SAST_RAPID mode for PR scans when PR is opened/updated (faster feedback)
    - Using full SAST for push events (comprehensive analysis)
    - Skipping SAST_RAPID when PR is closed/merged (no need to scan)
    
    Args:
        assessment_type: Type of assessment (SAST, SCA, or SAST,SCA)
        has_pr_trigger: Whether the workflow has a pull_request trigger
        existing_env: Existing environment variables to merge with
    
    Returns:
        Dictionary of environment variables for Polaris
    """
    env_vars = existing_env.copy() if existing_env else {}
    
    # Always add POLARIS_ASSESSMENT_TYPES
    if assessment_type == AssessmentType.SAST:
        env_vars['POLARIS_ASSESSMENT_TYPES'] = 'SAST'
    elif assessment_type == AssessmentType.SCA:
        env_vars['POLARIS_ASSESSMENT_TYPES'] = 'SCA'
    elif assessment_type == AssessmentType.SAST_SCA:
        env_vars['POLARIS_ASSESSMENT_TYPES'] = 'SAST,SCA'
    
    # Add PR optimization ONLY if:
    # 1. Assessment includes SAST
    # 2. Workflow has PR trigger
    if should_include_sast(assessment_type) and has_pr_trigger:
        env_vars['POLARIS_TEST_SAST_TYPE'] = "${{ (github.event_name == 'pull_request' && contains(fromJSON('[\"opened\",\"synchronize\",\"reopened\"]'), github.event.action)) && 'SAST_RAPID' || '' }}"
    
    return env_vars


def should_add_pr_optimization(
    assessment_type: AssessmentType,
    has_pr_trigger: bool
) -> bool:
    """
    Determine if PR optimization should be added
    
    Args:
        assessment_type: Type of assessment
        has_pr_trigger: Whether workflow has PR trigger
    
    Returns:
        True if PR optimization should be added
    """
    return should_include_sast(assessment_type) and has_pr_trigger


def get_pr_optimization_explanation() -> str:
    """Get explanation text for PR optimization feature"""
    return (
        "This workflow uses PR optimization: "
        "SAST_RAPID mode for pull requests (faster feedback) "
        "and full SAST for push events (comprehensive analysis)."
    )


def format_env_for_yaml(env_vars: Dict[str, str], indent: int = 4) -> str:
    """
    Format environment variables dictionary as YAML string
    
    Args:
        env_vars: Dictionary of environment variables
        indent: Number of spaces for indentation
    
    Returns:
        YAML-formatted string
    """
    indent_str = ' ' * indent
    lines = []
    
    for key, value in env_vars.items():
        # Check if value contains GitHub expression syntax
        if '${{' in value:
            # Don't quote GitHub expressions
            lines.append(f"{indent_str}{key}: {value}")
        else:
            # Quote regular values
            lines.append(f"{indent_str}{key}: '{value}'")
    
    return '\n'.join(lines)


# Example usage and testing
if __name__ == "__main__":
    print("Testing PR optimization logic:")
    print("=" * 70)
    
    # Test cases
    test_cases = [
        {
            'name': 'SAST with PR trigger',
            'assessment': AssessmentType.SAST,
            'has_pr': True,
            'should_optimize': True
        },
        {
            'name': 'SAST without PR trigger',
            'assessment': AssessmentType.SAST,
            'has_pr': False,
            'should_optimize': False
        },
        {
            'name': 'SAST,SCA with PR trigger',
            'assessment': AssessmentType.SAST_SCA,
            'has_pr': True,
            'should_optimize': True
        },
        {
            'name': 'SCA only with PR trigger',
            'assessment': AssessmentType.SCA,
            'has_pr': True,
            'should_optimize': False
        },
        {
            'name': 'SAST,SCA without PR trigger',
            'assessment': AssessmentType.SAST_SCA,
            'has_pr': False,
            'should_optimize': False
        }
    ]
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"  Assessment: {test['assessment'].value}")
        print(f"  Has PR trigger: {test['has_pr']}")
        
        env_vars = generate_polaris_config_with_event_optimization(
            test['assessment'],
            test['has_pr']
        )
        
        has_optimization = 'POLARIS_TEST_SAST_TYPE' in env_vars
        result = "✓" if has_optimization == test['should_optimize'] else "✗"
        
        print(f"  {result} Should optimize: {test['should_optimize']}, Got: {has_optimization}")
        print("  Environment variables:")
        for key, value in env_vars.items():
            print(f"    {key}: {value}")
    
    # Test YAML formatting
    print("\n" + "=" * 70)
    print("Example YAML formatting:")
    print("=" * 70)
    
    env_vars = generate_polaris_config_with_event_optimization(
        AssessmentType.SAST_SCA,
        has_pr_trigger=True
    )
    
    print("\nenv:")
    print(format_env_for_yaml(env_vars))
