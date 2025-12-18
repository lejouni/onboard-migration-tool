"""
MCP Server for Local Workflow Analysis
Provides cost-free workflow analysis and template recommendations
"""

import json
import sys
from typing import Dict, Any
from workflow_analyzer import LocalWorkflowAnalyzer, WorkflowAnalysis

class WorkflowAnalysisMCPServer:
    """MCP Server for workflow analysis without external API costs"""
    
    def __init__(self):
        self.analyzer = LocalWorkflowAnalyzer()
        
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests for workflow analysis"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            
            if method == "analyze_workflow":
                return await self._analyze_workflow(params)
            elif method == "find_template_matches":
                return await self._find_template_matches(params)
            elif method == "get_capabilities":
                return await self._get_capabilities()
            else:
                return self._error_response(f"Unknown method: {method}")
                
        except Exception as e:
            return self._error_response(str(e))
    
    async def _analyze_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a workflow file and return insights"""
        workflow_content = params.get("content", "")
        file_name = params.get("file_name", "workflow.yml")
        
        if not workflow_content:
            return self._error_response("No workflow content provided")
        
        analysis = await self.analyzer.analyze_workflow(workflow_content, file_name)
        
        return {
            "success": True,
            "analysis": {
                "file_name": analysis.file_name,
                "technologies": [
                    {
                        "name": tech.name,
                        "type": tech.type.value,
                        "confidence": tech.confidence,
                        "evidence": tech.evidence
                    } for tech in analysis.technologies
                ],
                "patterns": [
                    {
                        "type": pattern.pattern_type,
                        "description": pattern.description,
                        "confidence": pattern.confidence,
                        "locations": pattern.locations
                    } for pattern in analysis.patterns
                ],
                "scores": {
                    "complexity": analysis.complexity_score,
                    "security": analysis.security_score,
                    "modernization": analysis.modernization_score
                },
                "recommendations": analysis.recommendations
            }
        }
    
    async def _find_template_matches(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find template matches for a workflow analysis"""
        analysis_data = params.get("analysis")
        templates = params.get("templates", [])
        
        if not analysis_data:
            return self._error_response("No analysis data provided")
        
        # Convert analysis_data back to WorkflowAnalysis object (simplified)
        # In a real implementation, you'd properly deserialize this
        workflow_analysis = self._deserialize_analysis(analysis_data)
        
        matches = await self.analyzer.find_template_matches(workflow_analysis, templates)
        
        return {
            "success": True,
            "matches": [
                {
                    "template_id": match.template_id,
                    "template_name": match.template_name,
                    "similarity_score": match.similarity_score,
                    "matching_features": match.matching_features,
                    "missing_features": match.missing_features,
                    "improvement_potential": match.improvement_potential
                } for match in matches
            ]
        }
    
    async def _get_capabilities(self) -> Dict[str, Any]:
        """Return server capabilities"""
        return {
            "success": True,
            "capabilities": {
                "name": "Local Workflow Analyzer",
                "version": "1.0.0",
                "description": "Cost-free local workflow analysis and template matching",
                "methods": [
                    {
                        "name": "analyze_workflow",
                        "description": "Analyze workflow content for technologies, patterns, and recommendations",
                        "parameters": {
                            "content": "Workflow file content (string)",
                            "file_name": "Optional file name (string)"
                        }
                    },
                    {
                        "name": "find_template_matches",
                        "description": "Find matching templates for analyzed workflow",
                        "parameters": {
                            "analysis": "Workflow analysis object",
                            "templates": "Array of available templates"
                        }
                    }
                ],
                "features": [
                    "Technology detection (Java, Node.js, Python, etc.)",
                    "CI/CD pattern recognition",
                    "Security assessment",
                    "Modernization scoring",
                    "Template similarity matching",
                    "Improvement recommendations"
                ],
                "cost": "Free - No external API calls"
            }
        }
    
    def _deserialize_analysis(self, analysis_data: Dict) -> WorkflowAnalysis:
        """Convert analysis data dict back to WorkflowAnalysis object"""
        # This is a simplified implementation
        # In practice, you'd want proper deserialization
        from workflow_analyzer import WorkflowAnalysis, DetectedTechnology, WorkflowPattern, TechnologyType
        
        technologies = []
        for tech_data in analysis_data.get("technologies", []):
            technologies.append(DetectedTechnology(
                name=tech_data["name"],
                type=TechnologyType(tech_data["type"]),
                confidence=tech_data["confidence"],
                evidence=tech_data["evidence"]
            ))
        
        patterns = []
        for pattern_data in analysis_data.get("patterns", []):
            patterns.append(WorkflowPattern(
                pattern_type=pattern_data["type"],
                description=pattern_data["description"],
                confidence=pattern_data["confidence"],
                locations=pattern_data["locations"]
            ))
        
        scores = analysis_data.get("scores", {})
        
        return WorkflowAnalysis(
            file_name=analysis_data.get("file_name", ""),
            technologies=technologies,
            patterns=patterns,
            complexity_score=scores.get("complexity", 0.0),
            security_score=scores.get("security", 0.0),
            modernization_score=scores.get("modernization", 0.0),
            recommendations=analysis_data.get("recommendations", [])
        )
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Return error response"""
        return {
            "success": False,
            "error": message
        }

# MCP Server Entry Point
async def run_mcp_server():
    """Run the MCP server"""
    server = WorkflowAnalysisMCPServer()
    
    print("🔄 Local Workflow Analysis MCP Server starting...", file=sys.stderr)
    print("💰 Cost: $0 - No external API calls required", file=sys.stderr)
    
    while True:
        try:
            # Read request from stdin
            line = sys.stdin.readline()
            if not line:
                break
                
            request = json.loads(line.strip())
            response = await server.handle_request(request)
            
            # Write response to stdout
            print(json.dumps(response))
            sys.stdout.flush()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Server error: {str(e)}"
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_mcp_server())