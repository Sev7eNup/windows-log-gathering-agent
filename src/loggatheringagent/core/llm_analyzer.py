"""
LLM analyzer for processing Windows deployment logs and identifying issues.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import httpx

from ..config.settings import Settings, LLMConfig
from .log_collector import ClientLogCollection, LogCollectionResult

logger = logging.getLogger(__name__)


@dataclass
class LogAnalysisResult:
    """Result of LLM analysis for a single log source."""
    source: str
    analysis: str
    issues_found: List[str]
    recommendations: List[str]
    severity: str  # "info", "warning", "error", "critical"
    confidence: float  # 0.0 to 1.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ClientAnalysisResult:
    """Complete analysis result for a client machine."""
    client_name: str
    hostname: str
    overall_status: str  # "healthy", "issues", "critical"
    log_analyses: List[LogAnalysisResult]
    summary: str
    action_items: List[str]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class WindowsLogAnalyzer:
    """Analyzes Windows deployment logs using LLM."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.machines_config = settings.load_machines_config()
        self.llm_config = self.machines_config.llm_config
    
    async def analyze_client_logs(self, log_collection: ClientLogCollection) -> ClientAnalysisResult:
        """Analyze all logs from a client using LLM."""
        logger.info(f"Starting LLM analysis for client: {log_collection.client_name}")
        
        if not log_collection.success:
            return ClientAnalysisResult(
                client_name=log_collection.client_name,
                hostname=log_collection.hostname,
                overall_status="critical",
                log_analyses=[],
                summary=f"Log collection failed: {', '.join(log_collection.errors)}",
                action_items=["Fix log collection issues before analysis"]
            )
        
        # Analyze each log source
        log_analyses = []
        for log_result in log_collection.log_results:
            if log_result.success and log_result.content.strip():
                analysis = await self._analyze_single_log(log_result)
                log_analyses.append(analysis)
            else:
                # Create analysis for failed log collection
                log_analyses.append(LogAnalysisResult(
                    source=log_result.source,
                    analysis=f"Failed to collect log: {log_result.error}",
                    issues_found=["Log collection failed"],
                    recommendations=["Check file permissions and network connectivity"],
                    severity="error",
                    confidence=1.0
                ))
        
        # Generate overall summary
        summary = await self._generate_client_summary(log_collection, log_analyses)
        
        # Determine overall status
        overall_status = self._determine_overall_status(log_analyses)
        
        # Extract action items
        action_items = self._extract_action_items(log_analyses)
        
        return ClientAnalysisResult(
            client_name=log_collection.client_name,
            hostname=log_collection.hostname,
            overall_status=overall_status,
            log_analyses=log_analyses,
            summary=summary,
            action_items=action_items
        )
    
    async def _analyze_single_log(self, log_result: LogCollectionResult) -> LogAnalysisResult:
        """Analyze a single log using LLM."""
        try:
            # Prepare prompt based on log source type
            prompt = self._create_analysis_prompt(log_result)
            
            # Call LLM
            response = await self._call_llm(prompt)
            
            # Parse LLM response
            parsed_result = self._parse_llm_response(response, log_result.source)
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"Error analyzing log {log_result.source}: {e}")
            return LogAnalysisResult(
                source=log_result.source,
                analysis=f"Analysis failed: {str(e)}",
                issues_found=[f"Analysis error: {str(e)}"],
                recommendations=["Retry analysis or check LLM endpoint"],
                severity="error",
                confidence=0.0
            )
    
    def _create_analysis_prompt(self, log_result: LogCollectionResult) -> str:
        """Create specialized prompt based on log source type."""
        
        # Determine log type from source
        source_lower = log_result.source.lower()
        
        if "wuahandler" in source_lower:
            log_type = "SCCM Windows Update Agent Handler"
            specific_instructions = """
            Focus on:
            - Windows Update installation failures
            - Update agent errors and warnings
            - Communication issues with WSUS/Windows Update
            - Installation progress and completion status
            """
        elif "cas.log" in source_lower:
            log_type = "SCCM Content Access Service"
            specific_instructions = """
            Focus on:
            - Content download failures
            - Distribution point connectivity issues
            - Content validation errors
            - Cache management problems
            """
        elif "cbs.log" in source_lower:
            log_type = "Component-Based Servicing"
            specific_instructions = """
            Focus on:
            - Windows component installation failures
            - Package integrity issues
            - Dependency resolution problems
            - System file corruption
            """
        elif "windowsupdate" in source_lower or "get-windowsupdatelog" in source_lower:
            log_type = "Windows Update Log"
            specific_instructions = """
            Focus on:
            - Update download and installation errors
            - Agent communication issues
            - Reboot requirements and failures
            - Update rollback scenarios
            """
        elif "powershell" in source_lower and "winevent" in source_lower:
            log_type = "Windows Event Log"
            specific_instructions = """
            Focus on:
            - Critical system events
            - Application and service failures
            - Security-related events
            - Hardware and driver issues
            """
        else:
            log_type = "Windows System Log"
            specific_instructions = """
            Focus on:
            - Error and warning messages
            - System component failures
            - Configuration issues
            - Performance problems
            """
        
        prompt = f"""{self.llm_config.system_prompt}

LOG TYPE: {log_type}

{specific_instructions}

CRITICAL: You must respond ONLY with valid JSON. NO markdown, NO explanations, NO extra text.

Required JSON format:
{{
    "analysis": "Your detailed analysis here",
    "issues_found": ["List specific issues found"],
    "recommendations": ["List specific recommendations"], 
    "severity": "info|warning|error|critical",
    "confidence": 0.85
}}

ANALYSIS INSTRUCTIONS:
1. Identify all errors, warnings, and potential issues
2. Categorize severity: info, warning, error, critical  
3. Provide specific, actionable recommendations
4. Include confidence level (0.0 to 1.0)

RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT:

LOG CONTENT TO ANALYZE:
---
{log_result.content[:8000]}  # Limit to ~8k chars to avoid token limits
---"""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM endpoint with the given prompt."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.llm_config.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": self.llm_config.max_tokens,
                    "temperature": self.llm_config.temperature,
                    "stream": False
                }
                
                response = await client.post(
                    f"{self.llm_config.endpoint}/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    raise Exception("No response from LLM")
                    
        except httpx.TimeoutException:
            raise Exception("LLM request timed out")
        except httpx.HTTPError as e:
            raise Exception(f"HTTP error calling LLM: {e}")
        except Exception as e:
            raise Exception(f"Error calling LLM: {e}")
    
    def _parse_llm_response(self, response: str, source: str) -> LogAnalysisResult:
        """Parse the LLM response into structured result."""
        try:
            # Clean and extract JSON from response
            response = response.strip()
            
            # Try multiple approaches to extract JSON
            json_str = None
            
            # Method 1: Look for markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response and "{" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            
            # Method 2: Extract JSON object boundaries
            if not json_str:
                start = response.find("{")
                if start != -1:
                    # Find the matching closing brace
                    brace_count = 0
                    end = start
                    for i, char in enumerate(response[start:], start):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                    if brace_count == 0:
                        json_str = response[start:end]
            
            # Method 3: If no JSON structure found, try the whole response
            if not json_str and response.startswith("{") and response.endswith("}"):
                json_str = response
            
            if json_str:
                # Parse JSON
                parsed = json.loads(json_str)
                
                return LogAnalysisResult(
                    source=source,
                    analysis=parsed.get("analysis", "No analysis provided"),
                    issues_found=parsed.get("issues_found", []),
                    recommendations=parsed.get("recommendations", []),
                    severity=parsed.get("severity", "info"),
                    confidence=float(parsed.get("confidence", 0.5))
                )
            else:
                # No JSON found - treat as raw text
                raise ValueError("No JSON structure found in response")
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {e}")
            logger.warning(f"Raw LLM response: {repr(response)}")
            
            # Enhanced fallback: extract key information from text
            analysis_text = response
            issues = []
            recommendations = []
            severity = "info"
            confidence = 0.3
            
            # Try to extract some structured info from raw text
            if "error" in response.lower() or "failed" in response.lower():
                severity = "error"
                confidence = 0.6
            elif "warning" in response.lower() or "issue" in response.lower():
                severity = "warning"
                confidence = 0.5
            
            # Look for bullet points or numbered lists
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith(('•', '-', '*', '1.', '2.', '3.')):
                    if 'recommend' in line.lower():
                        recommendations.append(line.lstrip('•-*123456789. '))
                    elif any(word in line.lower() for word in ['error', 'issue', 'problem', 'fail']):
                        issues.append(line.lstrip('•-*123456789. '))
            
            return LogAnalysisResult(
                source=source,
                analysis=f"Parsed from raw response: {analysis_text[:500]}...",
                issues_found=issues if issues else ["Could not parse structured JSON response"],
                recommendations=recommendations if recommendations else ["Check LLM prompt and response format"],
                severity=severity,
                confidence=confidence
            )
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return LogAnalysisResult(
                source=source,
                analysis=f"Failed to parse response: {str(e)}",
                issues_found=[f"Parse error: {str(e)}"],
                recommendations=["Check LLM response format"],
                severity="error",
                confidence=0.0
            )
    
    async def _generate_client_summary(self, log_collection: ClientLogCollection, 
                                     log_analyses: List[LogAnalysisResult]) -> str:
        """Generate overall summary for the client."""
        
        # Prepare summary data
        total_logs = len(log_collection.log_results)
        successful_logs = len([r for r in log_collection.log_results if r.success])
        critical_issues = len([a for a in log_analyses if a.severity == "critical"])
        error_issues = len([a for a in log_analyses if a.severity == "error"])
        warning_issues = len([a for a in log_analyses if a.severity == "warning"])
        
        # Create summary prompt
        summary_prompt = f"""Create a concise executive summary for Windows deployment log analysis.

CLIENT: {log_collection.client_name} ({log_collection.hostname})
LOGS ANALYZED: {successful_logs}/{total_logs} successful
ISSUES FOUND: {critical_issues} critical, {error_issues} errors, {warning_issues} warnings

KEY FINDINGS:
"""
        
        for analysis in log_analyses:
            if analysis.issues_found:
                summary_prompt += f"\n{analysis.source}: {', '.join(analysis.issues_found[:2])}"
        
        summary_prompt += "\n\nProvide a 2-3 sentence executive summary highlighting the most critical issues and overall system health."
        
        try:
            summary = await self._call_llm(summary_prompt)
            return summary.strip()
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Analysis completed for {successful_logs}/{total_logs} logs. Found {critical_issues} critical issues, {error_issues} errors, {warning_issues} warnings."
    
    def _determine_overall_status(self, log_analyses: List[LogAnalysisResult]) -> str:
        """Determine overall client status based on analysis results."""
        if not log_analyses:
            return "critical"
        
        severities = [analysis.severity for analysis in log_analyses]
        
        if "critical" in severities:
            return "critical"
        elif "error" in severities:
            return "issues"
        elif "warning" in severities:
            return "issues"
        else:
            return "healthy"
    
    def _extract_action_items(self, log_analyses: List[LogAnalysisResult]) -> List[str]:
        """Extract and deduplicate action items from all analyses."""
        action_items = []
        
        for analysis in log_analyses:
            action_items.extend(analysis.recommendations)
        
        # Deduplicate while preserving order
        unique_items = []
        seen = set()
        for item in action_items:
            if item not in seen:
                unique_items.append(item)
                seen.add(item)
        
        return unique_items[:10]  # Limit to top 10 action items
    
    async def analyze_multiple_clients(self, log_collections: List[ClientLogCollection]) -> List[ClientAnalysisResult]:
        """Analyze logs from multiple clients concurrently."""
        logger.info(f"Starting concurrent LLM analysis for {len(log_collections)} clients")
        
        tasks = [self.analyze_client_logs(collection) for collection in log_collections]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception analyzing {log_collections[i].client_name}: {result}")
                final_results.append(ClientAnalysisResult(
                    client_name=log_collections[i].client_name,
                    hostname=log_collections[i].hostname,
                    overall_status="critical",
                    log_analyses=[],
                    summary=f"Analysis failed: {str(result)}",
                    action_items=["Retry analysis"]
                ))
            else:
                final_results.append(result)
        
        return final_results