"""
Assessment Type Determination Logic
Determines which security assessments (SAST, SCA, both) to recommend based on project characteristics
"""

from typing import List
from dataclasses import dataclass
from enum import Enum


class AssessmentType(Enum):
    """Types of security assessments"""
    SAST = "SAST"  # Static Application Security Testing
    SCA = "SCA"    # Software Composition Analysis
    SAST_SCA = "SAST,SCA"  # Both SAST and SCA


@dataclass
class PackageManagerDetection:
    """Package manager detection result"""
    detected: bool
    package_manager: str  # "maven", "gradle", "npm", "pip", etc.
    files_found: List[str]  # List of package manager files found
    languages: List[str]  # Associated programming languages


@dataclass
class AssessmentRecommendation:
    """Assessment type recommendation with reasoning"""
    assessment_type: AssessmentType
    reasoning: str
    package_managers: List[PackageManagerDetection]
    primary_language: str


# Package manager file patterns
PACKAGE_MANAGER_PATTERNS = {
    'maven': {
        'files': ['pom.xml'],
        'languages': ['java'],
        'description': 'Maven project'
    },
    'gradle': {
        'files': ['build.gradle', 'build.gradle.kts', 'settings.gradle', 'settings.gradle.kts'],
        'languages': ['java', 'kotlin'],
        'description': 'Gradle project'
    },
    'npm': {
        'files': ['package.json', 'package-lock.json'],
        'languages': ['javascript', 'typescript'],
        'description': 'NPM/Node.js project'
    },
    'yarn': {
        'files': ['yarn.lock'],
        'languages': ['javascript', 'typescript'],
        'description': 'Yarn project'
    },
    'pip': {
        'files': ['requirements.txt', 'requirements-dev.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
        'languages': ['python'],
        'description': 'Python/pip project'
    },
    'nuget': {
        'files': ['packages.config', '.csproj', '.sln', 'nuget.config'],
        'languages': ['csharp', 'dotnet'],
        'description': '.NET/NuGet project'
    },
    'composer': {
        'files': ['composer.json', 'composer.lock'],
        'languages': ['php'],
        'description': 'PHP/Composer project'
    },
    'cargo': {
        'files': ['Cargo.toml', 'Cargo.lock'],
        'languages': ['rust'],
        'description': 'Rust/Cargo project'
    },
    'go_modules': {
        'files': ['go.mod', 'go.sum'],
        'languages': ['go'],
        'description': 'Go modules project'
    },
    'bundler': {
        'files': ['Gemfile', 'Gemfile.lock'],
        'languages': ['ruby'],
        'description': 'Ruby/Bundler project'
    }
}


def detect_package_managers(file_list: List[str]) -> List[PackageManagerDetection]:
    """
    Detect package managers from a list of files in the repository
    
    Args:
        file_list: List of file paths in the repository
    
    Returns:
        List of detected package managers
    """
    detections = []
    
    # Normalize file paths to just filenames for matching
    file_names = [f.split('/')[-1] for f in file_list]
    
    for pm_name, pm_config in PACKAGE_MANAGER_PATTERNS.items():
        files_found = []
        
        for pm_file in pm_config['files']:
            # Check if any file matches the pattern
            if pm_file in file_names:
                # Find the full path
                for full_path in file_list:
                    if full_path.endswith(pm_file):
                        files_found.append(full_path)
        
        if files_found:
            detections.append(PackageManagerDetection(
                detected=True,
                package_manager=pm_name,
                files_found=files_found,
                languages=pm_config['languages']
            ))
    
    return detections


def determine_assessment_types(
    file_list: List[str],
    detected_languages: List[str] = None
) -> AssessmentRecommendation:
    """
    Determine which assessment types to recommend based on project characteristics
    
    Logic:
    - If package manager detected (pom.xml, package.json, requirements.txt, etc.) → SAST,SCA
    - If no package manager but language detected → SAST only
    - Default → SAST only
    
    Args:
        file_list: List of file paths in the repository
        detected_languages: Optional list of detected programming languages
    
    Returns:
        AssessmentRecommendation with assessment type and reasoning
    """
    # Detect package managers
    package_managers = detect_package_managers(file_list)
    
    # Determine primary language
    primary_language = _determine_primary_language(package_managers, detected_languages)
    
    # If package manager(s) detected, recommend SAST + SCA
    if package_managers:
        pm_names = ', '.join([pm.package_manager for pm in package_managers])
        pm_files = ', '.join([pm.files_found[0].split('/')[-1] for pm in package_managers])
        
        return AssessmentRecommendation(
            assessment_type=AssessmentType.SAST_SCA,
            reasoning=f"Package manager(s) detected ({pm_names}): {pm_files}. "
                     f"Recommend both SAST (for source code analysis) and SCA (for dependency vulnerability scanning).",
            package_managers=package_managers,
            primary_language=primary_language
        )
    
    # No package manager detected, but language is known → SAST only
    if primary_language:
        return AssessmentRecommendation(
            assessment_type=AssessmentType.SAST,
            reasoning=f"No package manager detected, but {primary_language} code identified. "
                     f"Recommend SAST only for source code analysis.",
            package_managers=[],
            primary_language=primary_language
        )
    
    # Fallback: SAST only
    return AssessmentRecommendation(
        assessment_type=AssessmentType.SAST,
        reasoning="No package manager or specific language detected. "
                 "Recommend SAST for general source code security analysis.",
        package_managers=[],
        primary_language="unknown"
    )


def _determine_primary_language(
    package_managers: List[PackageManagerDetection],
    detected_languages: List[str] = None
) -> str:
    """
    Determine the primary programming language
    
    Priority:
    1. Language from package manager
    2. First detected language
    3. "unknown"
    """
    # Try to get language from package manager
    if package_managers:
        # Use the first package manager's primary language
        return package_managers[0].languages[0] if package_managers[0].languages else "unknown"
    
    # Use detected languages
    if detected_languages and len(detected_languages) > 0:
        return detected_languages[0].lower()
    
    return "unknown"


def should_include_sca(assessment_type: AssessmentType) -> bool:
    """Check if SCA should be included in the assessment"""
    return assessment_type in [AssessmentType.SCA, AssessmentType.SAST_SCA]


def should_include_sast(assessment_type: AssessmentType) -> bool:
    """Check if SAST should be included in the assessment"""
    return assessment_type in [AssessmentType.SAST, AssessmentType.SAST_SCA]


def get_polaris_assessment_types(assessment_type: AssessmentType) -> str:
    """
    Get the Polaris assessment types configuration value
    
    Args:
        assessment_type: The determined assessment type
    
    Returns:
        String value for POLARIS_ASSESSMENT_TYPES environment variable
    """
    if assessment_type == AssessmentType.SAST:
        return "SAST"
    elif assessment_type == AssessmentType.SCA:
        return "SCA"
    elif assessment_type == AssessmentType.SAST_SCA:
        return "SAST,SCA"
    return "SAST"  # Default


# Example usage for testing
if __name__ == "__main__":
    # Test cases
    test_cases = [
        {
            'name': 'Java Maven project',
            'files': ['src/main/java/App.java', 'pom.xml', 'README.md'],
            'expected': AssessmentType.SAST_SCA
        },
        {
            'name': 'JavaScript NPM project',
            'files': ['src/index.js', 'package.json', 'package-lock.json'],
            'expected': AssessmentType.SAST_SCA
        },
        {
            'name': 'Python pip project',
            'files': ['main.py', 'requirements.txt', 'README.md'],
            'expected': AssessmentType.SAST_SCA
        },
        {
            'name': 'Plain Python (no requirements.txt)',
            'files': ['script.py', 'utils.py', 'README.md'],
            'languages': ['python'],
            'expected': AssessmentType.SAST
        },
        {
            'name': 'Java Gradle project',
            'files': ['src/main/java/App.java', 'build.gradle', 'settings.gradle'],
            'expected': AssessmentType.SAST_SCA
        }
    ]
    
    print("Testing assessment type determination:")
    print("=" * 60)
    
    for test in test_cases:
        recommendation = determine_assessment_types(
            test['files'],
            test.get('languages', [])
        )
        
        result = "✓" if recommendation.assessment_type == test['expected'] else "✗"
        
        print(f"\n{result} {test['name']}")
        print(f"  Files: {test['files']}")
        print(f"  Expected: {test['expected'].value}")
        print(f"  Got: {recommendation.assessment_type.value}")
        print(f"  Reasoning: {recommendation.reasoning}")
        print(f"  Primary Language: {recommendation.primary_language}")
        if recommendation.package_managers:
            pm_list = ', '.join([pm.package_manager for pm in recommendation.package_managers])
            print(f"  Package Managers: {pm_list}")
