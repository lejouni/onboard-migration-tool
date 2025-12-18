"""
Local Workflow Analyzer for MCP Integration
Provides cost-free workflow analysis and template recommendations
"""

import re
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

class TechnologyType(Enum):
    LANGUAGE = "language"
    BUILD_TOOL = "build_tool"
    DEPLOYMENT_TARGET = "deployment_target"
    TESTING_FRAMEWORK = "testing_framework"
    SECURITY_TOOL = "security_tool"
    CONTAINER_TECH = "container_tech"
    PACKAGE_MANAGER = "package_manager"
    BINARY_ARTIFACT = "binary_artifact"

class BlackDuckToolType(Enum):
    POLARIS = "polaris"           # SAST
    BLACKDUCK = "blackduck"       # SCA  
    COVERITY = "coverity"         # SAST for C/C++
    SRM = "srm"                   # Software Risk Manager
    BDBA = "bdba"                 # Binary Analysis
    SEEKER = "seeker"             # IAST

@dataclass
class DetectedTechnology:
    name: str
    type: TechnologyType
    confidence: float  # 0.0 to 1.0
    evidence: List[str]  # Lines/patterns that detected this tech

@dataclass
class WorkflowPattern:
    pattern_type: str
    description: str
    confidence: float
    locations: List[str]  # Where in the workflow this pattern was found

@dataclass
class BlackDuckToolDetection:
    tool_type: BlackDuckToolType
    is_configured: bool
    configuration_quality: float  # 0.0 to 1.0
    evidence: List[str]
    issues: List[str]  # Configuration problems found

@dataclass
class PackageManager:
    name: str           # npm, maven, pip, etc.
    files_detected: List[str]  # package.json, pom.xml, etc.
    languages: List[str]       # Associated languages

@dataclass
class SecurityGap:
    missing_tool: BlackDuckToolType
    technology_trigger: str    # What technology requires this tool
    priority: str             # "high", "medium", "low"
    reasoning: str            # Why this tool is recommended

@dataclass
class BlackDuckAnalysis:
    detected_tools: List[BlackDuckToolDetection]
    package_managers: List[PackageManager]
    binary_artifacts: List[str]
    security_gaps: List[SecurityGap]
    recommendations: List[str]

@dataclass
class WorkflowAnalysis:
    file_name: str
    technologies: List[DetectedTechnology]
    patterns: List[WorkflowPattern]
    complexity_score: float  # 0.0 to 1.0 (simple to complex)
    security_score: float   # 0.0 to 1.0 (poor to excellent)
    modernization_score: float  # 0.0 to 1.0 (legacy to modern)
    recommendations: List[str]
    blackduck_analysis: BlackDuckAnalysis  # Black Duck security tools analysis

@dataclass
class TemplateMatch:
    template_id: str
    template_name: str
    similarity_score: float  # 0.0 to 1.0
    matching_features: List[str]
    missing_features: List[str]
    improvement_potential: str

class LocalWorkflowAnalyzer:
    """Local, cost-free workflow analyzer using pattern matching"""
    
    def __init__(self):
        self.technology_patterns = self._init_technology_patterns()
        self.workflow_patterns = self._init_workflow_patterns()
        self.security_patterns = self._init_security_patterns()
        self.blackduck_patterns = self._init_blackduck_patterns()
        self.package_manager_patterns = self._init_package_manager_patterns()
        
    def _init_technology_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize technology detection patterns"""
        return {
            "languages": [
                {"name": "Java", "patterns": [r"java", r"maven", r"gradle", r"\.jar", r"openjdk"], "weight": 1.0},
                {"name": "Node.js", "patterns": [r"node", r"npm", r"yarn", r"package\.json"], "weight": 1.0},
                {"name": "Python", "patterns": [r"python", r"pip", r"requirements\.txt", r"setup\.py"], "weight": 1.0},
                {"name": ".NET", "patterns": [r"dotnet", r"\.csproj", r"\.sln", r"nuget"], "weight": 1.0},
                {"name": "Go", "patterns": [r"\bgo\b", r"go\.mod", r"go\.sum"], "weight": 1.0},
                {"name": "Rust", "patterns": [r"rust", r"cargo", r"Cargo\.toml"], "weight": 1.0},
                {"name": "Ruby", "patterns": [r"ruby", r"gem", r"Gemfile", r"bundle"], "weight": 1.0},
            ],
            "build_tools": [
                {"name": "Maven", "patterns": [r"mvn", r"pom\.xml", r"maven"], "weight": 1.0},
                {"name": "Gradle", "patterns": [r"gradle", r"gradlew", r"build\.gradle"], "weight": 1.0},
                {"name": "NPM", "patterns": [r"npm\s+(?:install|run|build)", r"package\.json"], "weight": 1.0},
                {"name": "Yarn", "patterns": [r"yarn", r"yarn\.lock"], "weight": 1.0},
                {"name": "Make", "patterns": [r"make", r"Makefile"], "weight": 0.8},
                {"name": "CMake", "patterns": [r"cmake", r"CMakeLists\.txt"], "weight": 0.9},
            ],
            "deployment_targets": [
                {"name": "Azure", "patterns": [r"azure", r"az\s+", r"AZURE_", r"\.azurewebsites\."], "weight": 1.0},
                {"name": "AWS", "patterns": [r"aws", r"s3://", r"AWS_", r"amazon"], "weight": 1.0},
                {"name": "Google Cloud", "patterns": [r"gcloud", r"GCP_", r"google.*cloud"], "weight": 1.0},
                {"name": "Docker Hub", "patterns": [r"docker\.io", r"hub\.docker\.com"], "weight": 0.9},
                {"name": "Kubernetes", "patterns": [r"kubectl", r"k8s", r"kubernetes"], "weight": 1.0},
                {"name": "Heroku", "patterns": [r"heroku", r"\.herokuapp\.com"], "weight": 0.9},
            ],
            "testing_frameworks": [
                {"name": "JUnit", "patterns": [r"junit", r"test.*java"], "weight": 1.0},
                {"name": "Jest", "patterns": [r"jest", r"\.test\.js", r"\.spec\.js"], "weight": 1.0},
                {"name": "PyTest", "patterns": [r"pytest", r"test_.*\.py"], "weight": 1.0},
                {"name": "Mocha", "patterns": [r"mocha", r"\.test\.js"], "weight": 0.9},
                {"name": "Cypress", "patterns": [r"cypress", r"e2e.*test"], "weight": 0.9},
                {"name": "Selenium", "patterns": [r"selenium", r"webdriver"], "weight": 0.8},
            ],
            "security_tools": [
                {"name": "SonarQube", "patterns": [r"sonar", r"sonarqube"], "weight": 1.0},
                {"name": "Snyk", "patterns": [r"snyk"], "weight": 1.0},
                {"name": "OWASP", "patterns": [r"owasp", r"dependency-check"], "weight": 1.0},
                {"name": "Coverity", "patterns": [r"coverity", r"cov-.*"], "weight": 1.0},
                {"name": "CodeQL", "patterns": [r"codeql", r"github/codeql"], "weight": 1.0},
            ],
            "container_tech": [
                {"name": "Docker", "patterns": [r"docker", r"Dockerfile", r"docker-compose"], "weight": 1.0},
                {"name": "Podman", "patterns": [r"podman"], "weight": 0.9},
                {"name": "Buildah", "patterns": [r"buildah"], "weight": 0.8},
            ]
        }
    
    def _init_workflow_patterns(self) -> Dict[str, Dict]:
        """Initialize CI/CD workflow patterns"""
        return {
            "ci_patterns": {
                "multi_stage_pipeline": {
                    "patterns": [r"build.*test.*deploy", r"stages?:", r"jobs:.*build.*test"],
                    "description": "Multi-stage CI/CD pipeline with separate build, test, and deploy stages"
                },
                "matrix_strategy": {
                    "patterns": [r"strategy:\s*matrix", r"matrix:"],
                    "description": "Matrix build strategy for testing multiple configurations"
                },
                "caching": {
                    "patterns": [r"cache:", r"actions/cache", r"restore-keys"],
                    "description": "Dependency caching for faster builds"
                },
                "parallel_jobs": {
                    "patterns": [r"needs:", r"parallel", r"concurrent"],
                    "description": "Parallel job execution for faster pipelines"
                },
                "conditional_execution": {
                    "patterns": [r"if:", r"condition:", r"\$\{\{.*\}\}"],
                    "description": "Conditional execution based on branch, tags, or other conditions"
                }
            },
            "cd_patterns": {
                "blue_green_deployment": {
                    "patterns": [r"blue.*green", r"zero.*downtime"],
                    "description": "Blue-green deployment strategy"
                },
                "canary_deployment": {
                    "patterns": [r"canary", r"gradual.*rollout"],
                    "description": "Canary deployment for gradual rollouts"
                },
                "rollback_strategy": {
                    "patterns": [r"rollback", r"revert", r"previous.*version"],
                    "description": "Automated rollback capabilities"
                },
                "environment_promotion": {
                    "patterns": [r"dev.*staging.*prod", r"environment.*promotion"],
                    "description": "Environment promotion pipeline"
                }
            },
            "quality_patterns": {
                "code_coverage": {
                    "patterns": [r"coverage", r"jacoco", r"nyc", r"pytest-cov"],
                    "description": "Code coverage measurement and reporting"
                },
                "static_analysis": {
                    "patterns": [r"lint", r"sonar", r"eslint", r"checkstyle"],
                    "description": "Static code analysis and linting"
                },
                "security_scanning": {
                    "patterns": [r"security.*scan", r"vulnerability", r"cve"],
                    "description": "Security vulnerability scanning"
                },
                "performance_testing": {
                    "patterns": [r"performance.*test", r"load.*test", r"jmeter"],
                    "description": "Performance and load testing"
                }
            }
        }
    
    def _init_security_patterns(self) -> List[Dict]:
        """Initialize security best practice patterns"""
        return [
            {
                "name": "secret_management",
                "patterns": [r"secrets\.", r"\$\{\{\s*secrets\.", r"vault", r"keystore"],
                "description": "Proper secret management using GitHub secrets or vault",
                "weight": 1.0
            },
            {
                "name": "dependency_scanning", 
                "patterns": [r"audit", r"dependency.*check", r"snyk", r"npm.*audit"],
                "description": "Dependency vulnerability scanning",
                "weight": 0.9
            },
            {
                "name": "image_scanning",
                "patterns": [r"docker.*scan", r"container.*security", r"trivy"],
                "description": "Container image security scanning", 
                "weight": 0.9
            },
            {
                "name": "code_signing",
                "patterns": [r"sign", r"gpg", r"certificate"],
                "description": "Code and artifact signing",
                "weight": 0.8
            }
        ]

    def _init_blackduck_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize Black Duck security tools detection patterns"""
        return {
            BlackDuckToolType.POLARIS.value: [
                {"patterns": [r"polaris", r"blackduck.*polaris", r"blackduck-inc/black-duck-security-scan"], "weight": 1.0},
                {"patterns": [r"POLARIS_", r"polaris\.yml", r"polaris\.yaml"], "weight": 0.9},
            ],
            BlackDuckToolType.BLACKDUCK.value: [
                {"patterns": [r"blackduck", r"black.*duck", r"blackduck-inc/black-duck-security-scan"], "weight": 1.0},
                {"patterns": [r"BLACK_DUCK_", r"BLACKDUCK_", r"BD_HUB_"], "weight": 0.9},
            ],
            BlackDuckToolType.COVERITY.value: [
                {"patterns": [r"coverity", r"blackduck.*coverity", r"cov-analyze"], "weight": 1.0},
                {"patterns": [r"COVERITY_", r"coverity\.yaml", r"coverity\.yml"], "weight": 0.9},
            ],
            BlackDuckToolType.SRM.value: [
                {"patterns": [r"srm", r"software.*risk.*manager", r"blackduck.*srm"], "weight": 1.0},
                {"patterns": [r"SRM_"], "weight": 0.8},
            ],
            BlackDuckToolType.BDBA.value: [
                {"patterns": [r"bdba", r"binary.*analysis", r"blackduck.*bdba"], "weight": 1.0},
                {"patterns": [r"BDBA_", r"binary.*scan"], "weight": 0.8},
            ],
            BlackDuckToolType.SEEKER.value: [
                {"patterns": [r"seeker", r"blackduck.*seeker", r"iast"], "weight": 1.0},
                {"patterns": [r"SEEKER_"], "weight": 0.8},
            ],
        }

    def _init_package_manager_patterns(self) -> List[Dict]:
        """Initialize package manager detection patterns"""
        return [
            {
                "name": "npm",
                "files": ["package.json", "package-lock.json", "yarn.lock"],
                "patterns": [r"npm\s+install", r"yarn\s+install", r"node_modules"],
                "languages": ["JavaScript", "TypeScript", "Node.js"],
                "blackduck_recommendation": BlackDuckToolType.BLACKDUCK.value
            },
            {
                "name": "maven", 
                "files": ["pom.xml"],
                "patterns": [r"mvn\s+", r"maven", r"<dependency>"],
                "languages": ["Java"],
                "blackduck_recommendation": BlackDuckToolType.BLACKDUCK.value
            },
            {
                "name": "gradle",
                "files": ["build.gradle", "build.gradle.kts", "gradle.properties"],
                "patterns": [r"gradle", r"gradlew", r"implementation\s"],
                "languages": ["Java", "Kotlin"],
                "blackduck_recommendation": BlackDuckToolType.BLACKDUCK.value
            },
            {
                "name": "pip",
                "files": ["requirements.txt", "requirements-dev.txt", "setup.py", "pyproject.toml"],
                "patterns": [r"pip\s+install", r"requirements\.txt"],
                "languages": ["Python"],
                "blackduck_recommendation": BlackDuckToolType.BLACKDUCK.value
            },
            {
                "name": "nuget",
                "files": ["packages.config", "*.csproj", "*.sln", "nuget.config"],
                "patterns": [r"nuget", r"PackageReference", r"packages\.config"],
                "languages": [".NET", "C#"],
                "blackduck_recommendation": BlackDuckToolType.BLACKDUCK.value
            },
            {
                "name": "composer",
                "files": ["composer.json", "composer.lock"],
                "patterns": [r"composer\s+install", r"vendor/"],
                "languages": ["PHP"],
                "blackduck_recommendation": BlackDuckToolType.BLACKDUCK.value
            },
            {
                "name": "cargo",
                "files": ["Cargo.toml", "Cargo.lock"],
                "patterns": [r"cargo\s+build", r"crates\.io"],
                "languages": ["Rust"],
                "blackduck_recommendation": BlackDuckToolType.BLACKDUCK.value
            },
            {
                "name": "go_modules",
                "files": ["go.mod", "go.sum"],
                "patterns": [r"go\s+mod", r"go\s+get"],
                "languages": ["Go"],
                "blackduck_recommendation": BlackDuckToolType.BLACKDUCK.value
            }
        ]

    async def analyze_workflow(self, workflow_content: str, file_name: str = "workflow.yml") -> WorkflowAnalysis:
        """Analyze a workflow file and return detailed analysis"""
        
        # Convert to lowercase for pattern matching
        content_lower = workflow_content.lower()
        lines = workflow_content.split('\n')
        
        # Detect technologies
        technologies = self._detect_technologies(content_lower, lines)
        
        # Detect CI/CD patterns
        patterns = self._detect_patterns(content_lower, lines)
        
        # Calculate scores
        complexity_score = self._calculate_complexity_score(workflow_content, technologies, patterns)
        security_score = self._calculate_security_score(content_lower, lines)
        modernization_score = self._calculate_modernization_score(technologies, patterns)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(technologies, patterns, security_score)
        
        # Perform Blackduck-specific analysis
        blackduck_analysis = self._analyze_blackduck_tools(content_lower, lines, technologies)
        
        return WorkflowAnalysis(
            file_name=file_name,
            technologies=technologies,
            patterns=patterns,
            complexity_score=complexity_score,
            security_score=security_score,
            modernization_score=modernization_score,
            recommendations=recommendations,
            blackduck_analysis=blackduck_analysis
        )

    def _detect_technologies(self, content: str, lines: List[str]) -> List[DetectedTechnology]:
        """Detect technologies used in the workflow"""
        detected = []
        
        for category, techs in self.technology_patterns.items():
            for tech in techs:
                confidence = 0.0
                evidence = []
                
                for pattern in tech["patterns"]:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        confidence += tech["weight"] * min(len(matches) / 3, 1.0)  # Cap at 1.0
                        
                        # Find evidence lines
                        for i, line in enumerate(lines):
                            if re.search(pattern, line, re.IGNORECASE):
                                evidence.append(f"Line {i+1}: {line.strip()}")
                
                if confidence > 0.2:  # Threshold for inclusion
                    tech_type = TechnologyType.LANGUAGE
                    if category == "build_tools":
                        tech_type = TechnologyType.BUILD_TOOL
                    elif category == "deployment_targets":
                        tech_type = TechnologyType.DEPLOYMENT_TARGET
                    elif category == "testing_frameworks":
                        tech_type = TechnologyType.TESTING_FRAMEWORK
                    elif category == "security_tools":
                        tech_type = TechnologyType.SECURITY_TOOL
                    elif category == "container_tech":
                        tech_type = TechnologyType.CONTAINER_TECH
                    
                    detected.append(DetectedTechnology(
                        name=tech["name"],
                        type=tech_type,
                        confidence=min(confidence, 1.0),
                        evidence=evidence[:3]  # Limit evidence to 3 examples
                    ))
        
        return detected

    def _detect_patterns(self, content: str, lines: List[str]) -> List[WorkflowPattern]:
        """Detect CI/CD patterns in the workflow"""
        patterns = []
        
        for category, pattern_group in self.workflow_patterns.items():
            for pattern_name, pattern_info in pattern_group.items():
                confidence = 0.0
                locations = []
                
                for pattern in pattern_info["patterns"]:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        confidence += 0.3 * min(len(matches), 3)  # Max 0.9 per pattern
                        
                        # Find locations
                        for i, line in enumerate(lines):
                            if re.search(pattern, line, re.IGNORECASE):
                                locations.append(f"Line {i+1}")
                
                if confidence > 0.2:
                    patterns.append(WorkflowPattern(
                        pattern_type=f"{category}.{pattern_name}",
                        description=pattern_info["description"],
                        confidence=min(confidence, 1.0),
                        locations=locations[:3]
                    ))
        
        return patterns

    def _calculate_complexity_score(self, content: str, technologies: List[DetectedTechnology], patterns: List[WorkflowPattern]) -> float:
        """Calculate workflow complexity score (0.0 = simple, 1.0 = very complex)"""
        score = 0.0
        
        # Base complexity from file length
        lines = len(content.split('\n'))
        score += min(lines / 100, 0.3)  # Max 0.3 for length
        
        # Technology diversity adds complexity
        score += len(technologies) * 0.05  # Max ~0.5 for many technologies
        
        # Pattern complexity
        score += len(patterns) * 0.03  # Max ~0.3 for many patterns
        
        # Specific complexity indicators
        if re.search(r"matrix:", content, re.IGNORECASE):
            score += 0.2
        if re.search(r"strategy:", content, re.IGNORECASE):
            score += 0.1
        if re.search(r"needs:", content, re.IGNORECASE):
            score += 0.15
        
        return min(score, 1.0)

    def _calculate_security_score(self, content: str, lines: List[str]) -> float:
        """Calculate security score (0.0 = poor, 1.0 = excellent)"""
        score = 0.0
        
        for security_pattern in self.security_patterns:
            for pattern in security_pattern["patterns"]:
                if re.search(pattern, content, re.IGNORECASE):
                    score += security_pattern["weight"] * 0.25  # Max 1.0 for all patterns
        
        # Deduct points for bad practices
        if re.search(r"password.*=", content, re.IGNORECASE):
            score -= 0.3  # Hardcoded passwords
        if re.search(r"token.*=.*[a-zA-Z0-9]{20,}", content, re.IGNORECASE):
            score -= 0.3  # Hardcoded tokens
        
        return max(min(score, 1.0), 0.0)

    def _calculate_modernization_score(self, technologies: List[DetectedTechnology], patterns: List[WorkflowPattern]) -> float:
        """Calculate modernization score (0.0 = legacy, 1.0 = modern)"""
        score = 0.5  # Start at middle
        
        # Modern patterns boost score
        modern_patterns = ["matrix_strategy", "caching", "parallel_jobs", "conditional_execution"]
        for pattern in patterns:
            if any(mp in pattern.pattern_type for mp in modern_patterns):
                score += 0.1
        
        # Container tech is modern
        for tech in technologies:
            if tech.type == TechnologyType.CONTAINER_TECH:
                score += 0.2
        
        # Security tools are modern
        for tech in technologies:
            if tech.type == TechnologyType.SECURITY_TOOL:
                score += 0.1
        
        return min(score, 1.0)

    def _generate_recommendations(self, technologies: List[DetectedTechnology], patterns: List[WorkflowPattern], security_score: float) -> List[str]:
        """Generate recommendations for workflow improvement"""
        recommendations = []
        
        # Security recommendations
        if security_score < 0.5:
            recommendations.append("🔒 Consider adding security scanning tools like Snyk or CodeQL")
            recommendations.append("🔐 Use GitHub secrets instead of hardcoded credentials")
        
        # Performance recommendations
        has_caching = any("caching" in p.pattern_type for p in patterns)
        if not has_caching:
            recommendations.append("⚡ Add dependency caching to speed up builds")
        
        # Quality recommendations
        has_testing = any(t.type == TechnologyType.TESTING_FRAMEWORK for t in technologies)
        if not has_testing:
            recommendations.append("🧪 Add automated testing to your pipeline")
        
        # Modernization recommendations
        has_containers = any(t.type == TechnologyType.CONTAINER_TECH for t in technologies)
        if not has_containers:
            recommendations.append("🐳 Consider containerizing your application with Docker")
        
        return recommendations

    async def find_template_matches(self, workflow_analysis: WorkflowAnalysis, available_templates: List[Dict]) -> List[TemplateMatch]:
        """Find matching templates for the analyzed workflow"""
        matches = []
        
        for template in available_templates:
            similarity_score = self._calculate_template_similarity(workflow_analysis, template)
            
            if similarity_score > 0.3:  # Minimum threshold
                matching_features, missing_features = self._compare_features(workflow_analysis, template)
                
                matches.append(TemplateMatch(
                    template_id=template.get("id", ""),
                    template_name=template.get("name", "Unknown Template"),
                    similarity_score=similarity_score,
                    matching_features=matching_features,
                    missing_features=missing_features,
                    improvement_potential=self._assess_improvement_potential(workflow_analysis, template)
                ))
        
        # Sort by similarity score
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        return matches[:5]  # Return top 5 matches

    def _calculate_template_similarity(self, analysis: WorkflowAnalysis, template: Dict) -> float:
        """Calculate similarity between workflow analysis and template"""
        score = 0.0
        
        # Compare technologies (simplified - would need template structure)
        template_content = template.get("content", "").lower()
        
        for tech in analysis.technologies:
            if tech.name.lower() in template_content:
                score += tech.confidence * 0.3
        
        # Compare patterns (simplified)
        for pattern in analysis.patterns:
            # This would need more sophisticated template analysis
            # For now, just check if pattern keywords exist in template
            pattern_keywords = pattern.pattern_type.split(".")[-1]
            if pattern_keywords in template_content:
                score += pattern.confidence * 0.2
        
        return min(score, 1.0)

    def _compare_features(self, analysis: WorkflowAnalysis, template: Dict) -> tuple:
        """Compare features between workflow and template"""
        # Simplified feature comparison
        workflow_features = [tech.name for tech in analysis.technologies]
        workflow_features.extend([pattern.pattern_type for pattern in analysis.patterns])
        
        # This would need template feature extraction
        template_features = ["Docker", "Testing", "Security"]  # Placeholder
        
        matching = list(set(workflow_features) & set(template_features))
        missing = list(set(template_features) - set(workflow_features))
        
        return matching[:3], missing[:3]  # Limit to 3 each

    def _assess_improvement_potential(self, analysis: WorkflowAnalysis, template: Dict) -> str:
        """Assess how much the template could improve the workflow"""
        if analysis.security_score < 0.5:
            return "High - Significant security improvements possible"
        elif analysis.modernization_score < 0.7:
            return "Medium - Modernization opportunities available"
        else:
            return "Low - Workflow is already well-optimized"

    def _analyze_blackduck_tools(self, content_lower: str, lines: List[str], technologies: List[str]) -> BlackDuckAnalysis:
        """Analyze Black Duck tools usage and identify gaps based on detected technologies"""
        
        # Detect currently configured Black Duck tools
        detected_tools = []
        for tool_name, pattern_groups in self.blackduck_patterns.items():
            tool_type = BlackDuckToolType(tool_name)
            for pattern_group in pattern_groups:
                patterns = pattern_group.get('patterns', [])
                weight = pattern_group.get('weight', 0.7)
                for pattern in patterns:
                    if pattern.lower() in content_lower:
                        detected_tools.append(BlackDuckToolDetection(
                            tool_type=tool_type,
                            is_configured=True,
                            configuration_quality=weight,
                            evidence=[pattern],
                            issues=[]
                        ))
                        break  # Only add one detection per tool type
                if detected_tools and detected_tools[-1].tool_type == tool_type:
                    break  # Move to next tool type if found
        
        # Detect package managers
        detected_package_managers = []
        for pm_config in self.package_manager_patterns:
            pm_name = pm_config['name']
            for pattern in pm_config['patterns']:
                if pattern.lower() in content_lower:
                    detected_package_managers.append(PackageManager(
                        name=pm_name,
                        files_detected=[pattern],
                        languages=pm_config.get('languages', [])
                    ))
                    break
        
        # Detect binary artifacts (for BDBA recommendations)
        binary_patterns = ['.jar', '.war', '.ear', '.dll', '.exe', '.so', '.dylib', 'docker build', 'container']
        has_binaries = any(pattern in content_lower for pattern in binary_patterns)
        
        # Detect programming languages
        language_indicators = {
            'c_cpp': ['gcc', 'g++', 'cmake', 'make', '.c', '.cpp', '.h', '.hpp'],
            'java': ['maven', 'gradle', 'java', '.jar', 'pom.xml'],
            'javascript': ['npm', 'node', 'package.json', '.js', '.ts'],
            'python': ['pip', 'python', 'requirements.txt', '.py'],
            'csharp': ['dotnet', 'nuget', '.csproj', '.cs'],
            'php': ['composer', '.php'],
            'rust': ['cargo', '.rs'],
            'go': ['go mod', '.go']
        }
        
        detected_languages = []
        for lang, patterns in language_indicators.items():
            if any(pattern in content_lower for pattern in patterns):
                detected_languages.append(lang)
        
        # Generate security gaps based on analysis
        gaps = []
        detected_tool_types = [dt.tool_type for dt in detected_tools]
        
        # Check for SCA gaps (package managers without Black Duck)
        if detected_package_managers and BlackDuckToolType.BLACKDUCK not in detected_tool_types:
            pm_names = [pm.name for pm in detected_package_managers]
            gaps.append(SecurityGap(
                missing_tool=BlackDuckToolType.BLACKDUCK,
                technology_trigger=f"Package managers: {', '.join(pm_names)}",
                priority="high",
                reasoning="Add Black Duck SCA for open source vulnerability and license compliance scanning"
            ))
        
        # Check for SAST gaps based on languages
        if detected_languages:
            if 'c_cpp' in detected_languages and BlackDuckToolType.COVERITY not in detected_tool_types:
                gaps.append(SecurityGap(
                    missing_tool=BlackDuckToolType.COVERITY,
                    technology_trigger="C/C++ code detected",
                    priority="high",
                    reasoning="Add Coverity for comprehensive C/C++ static analysis"
                ))
            
            # For other languages, recommend Polaris
            other_languages = [lang for lang in detected_languages if lang != 'c_cpp']
            if other_languages and BlackDuckToolType.POLARIS not in detected_tool_types:
                gaps.append(SecurityGap(
                    missing_tool=BlackDuckToolType.POLARIS,
                    technology_trigger=f"Programming languages: {', '.join(other_languages)}",
                    priority="high",
                    reasoning="Add Polaris for static application security testing"
                ))
        
        # Check for BDBA gaps (binaries without binary analysis)
        if has_binaries and BlackDuckToolType.BDBA not in detected_tool_types:
            gaps.append(SecurityGap(
                missing_tool=BlackDuckToolType.BDBA,
                technology_trigger="Binary artifacts or containers detected",
                priority="medium",
                reasoning="Add Black Duck Binary Analysis for third-party component scanning in binaries"
            ))
        
        # Check for IAST gaps (web applications without runtime testing)
        web_indicators = ['http', 'server', 'api', 'web', 'service']
        if any(indicator in content_lower for indicator in web_indicators) and BlackDuckToolType.SEEKER not in detected_tool_types:
            gaps.append(SecurityGap(
                missing_tool=BlackDuckToolType.SEEKER,
                technology_trigger="Web application patterns detected",
                priority="low",
                reasoning="Consider Seeker for interactive application security testing (IAST)"
            ))
        
        return BlackDuckAnalysis(
            detected_tools=detected_tools,
            package_managers=detected_package_managers,
            binary_artifacts=['docker build'] if has_binaries else [],
            security_gaps=gaps,
            recommendations=self._generate_blackduck_recommendations(gaps, detected_tools)
        )
    
    def _generate_blackduck_recommendations(self, gaps: List[SecurityGap], detected_tools: List[BlackDuckToolDetection]) -> List[str]:
        """Generate actionable recommendations based on gap analysis"""
        recommendations = []
        
        # Priority-based recommendations
        high_priority_gaps = [gap for gap in gaps if gap.priority == "high"]
        if high_priority_gaps:
            recommendations.append(f"Critical: Address {len(high_priority_gaps)} high-priority security gaps")
            for gap in high_priority_gaps[:2]:  # Show top 2
                recommendations.append(f"• {gap.reasoning}")
        
        # Tool integration suggestions
        if len(detected_tools) > 0:
            tool_names = [tool.tool_type.value for tool in detected_tools]
            recommendations.append(f"Enhance existing tools: {', '.join(tool_names)}")
        
        # Coverage improvement
        if len(detected_tools) < 3:
            recommendations.append("Consider implementing a comprehensive security testing strategy")
        
        return recommendations[:5]  # Limit to 5 recommendations