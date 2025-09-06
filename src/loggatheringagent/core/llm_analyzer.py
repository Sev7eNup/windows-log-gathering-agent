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
            # Add larger delay to prevent race conditions with concurrent requests
            await asyncio.sleep(1.0)
            
            # Prepare prompt based on log source type
            prompt = self._create_analysis_prompt(log_result)
            
            # Call LLM with retry logic
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    response = await self._call_llm(prompt)
                    break
                except Exception as e:
                    if attempt == max_retries:
                        raise e
                    else:
                        logger.warning(f"LLM call attempt {attempt + 1} failed for {log_result.source}: {e}, retrying in 2 seconds...")
                        await asyncio.sleep(2.0)
            
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
    
    def _preprocess_json_string(self, json_str: str) -> str:
        """Preprocess JSON string to fix common issues."""
        try:
            # First attempt - try to load as-is
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass
        
        # Fix common issues
        processed = json_str.strip()
        
        # Fix truncated JSON - if missing closing brace, add it
        if processed.startswith('{') and not processed.endswith('}'):
            # Count braces to see if we need to close
            open_braces = processed.count('{')
            close_braces = processed.count('}')
            if open_braces > close_braces:
                processed += '}' * (open_braces - close_braces)
        
        # Replace problematic Windows path backslashes in strings
        import re
        
        # Find all string values and properly escape backslashes
        def fix_backslashes_in_string(match):
            content = match.group(1)
            # Escape single backslashes that aren't already escaped
            content = re.sub(r'(?<!\\)\\(?![\\"])', r'\\\\', content)
            return f'"{content}"'
        
        # Apply to string values only (between quotes)
        processed = re.sub(r'"([^"]*(?:\\.[^"]*)*)"', fix_backslashes_in_string, processed)
        
        # Try to parse again
        try:
            json.loads(processed)
            return processed
        except json.JSONDecodeError:
            # Still failing - return original for fallback handling
            return json_str
    
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
            log_type = "Component-Based Servicing (CBS.log)"
            specific_instructions = """
            Focus specifically on:
            - Package installation failures with exact package names, versions, and error codes
            - TrustedInstaller service operations and permission errors
            - Component store corruption with specific file paths and manifest issues
            - SxS assembly conflicts with detailed version information
            - System file corruption with specific .dll/.exe/.sys file names
            - Dependency resolution problems with component hierarchies
            - DISM operation failures and servicing stack issues
            - WinSxS store problems and cleanup operations
            - Registry operations and permissions errors
            - File system operations and access denied errors
            
            Include specific details:
            - Error codes (0x hex values, HRESULT codes)
            - File paths and registry keys
            - Package GUIDs and version numbers
            - Timestamps and operation sequences
            - Service names and process IDs"""
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

CRITICAL: You must respond ONLY with a valid JSON object. DO NOT include markdown code blocks, explanations, prefixes like "Here is the JSON object:", or any other text. Your response must start with {{ and end with }}.

Required JSON format:
{{
    "analysis": "Provide comprehensive technical analysis following the system prompt requirements above. Include specific error codes, file paths, registry keys, component versions, and detailed technical explanations as specified in the system prompt.",
    "issues_found": ["List specific issues found with technical details"],
    "recommendations": ["List specific actionable recommendations with exact commands and technical details"], 
    "severity": "info|warning|error|critical",
    "confidence": 0.85
}}

ANALYSIS INSTRUCTIONS:
1. Follow ALL requirements from the system prompt above for technical depth and specificity
2. For CBS logs: Include package names, versions, error codes, file paths, registry keys as specified
3. For Event logs: Include specific error codes, service names, process IDs as specified  
4. For all logs: Provide the detailed technical analysis format required by the system prompt
5. Include confidence level (0.0 to 1.0)

RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT:

LOG CONTENT TO ANALYZE:
---
{log_result.content[:8000]}
---"""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM endpoint with the given prompt."""
        try:
            # Add detailed logging
            logger.info(f"Making LLM request to {self.llm_config.endpoint}/v1/chat/completions")
            logger.info(f"Model: {self.llm_config.model}")
            logger.info(f"Prompt length: {len(prompt)} characters")
            
            async with httpx.AsyncClient(timeout=120.0) as client:  # Increased timeout
                payload = {
                    "model": self.llm_config.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": self.llm_config.max_tokens,
                    "temperature": self.llm_config.temperature,
                    "stream": False
                }
                
                logger.info(f"Payload size: {len(str(payload))} characters")
                
                response = await client.post(
                    f"{self.llm_config.endpoint}/v1/chat/completions",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Connection": "close"  # Force close connection after each request
                    }
                )
                
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"LLM API returned {response.status_code}: {error_text}")
                    raise Exception(f"HTTP {response.status_code}: {error_text}")
                
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    response_content = result["choices"][0]["message"]["content"]
                    logger.info(f"LLM response length: {len(response_content)} characters")
                    return response_content
                else:
                    logger.error(f"Invalid LLM response structure: {result}")
                    raise Exception("No response from LLM")
                    
        except httpx.TimeoutException:
            logger.error("LLM request timed out")
            raise Exception("LLM request timed out")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling LLM: {e}")
            raise Exception(f"HTTP error calling LLM: {e}")
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
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
            
            # Method 4: Handle truncated JSON - if starts with { but no closing brace found
            if not json_str and response.startswith("{"):
                json_str = response
            
            if json_str:
                # Preprocess JSON string to fix common issues
                json_str = self._preprocess_json_string(json_str)
                
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
                # No JSON found - log the raw response and treat as raw text
                logger.warning(f"No JSON structure found in LLM response")
                logger.warning(f"Raw LLM response: {repr(response)}")
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
                # Convert issues to strings to handle dict/object issues
                issues_str = []
                for issue in analysis.issues_found[:2]:
                    if isinstance(issue, str):
                        issues_str.append(issue)
                    else:
                        issues_str.append(str(issue))
                summary_prompt += f"\n{analysis.source}: {', '.join(issues_str)}"
        
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
            # Ensure recommendations are converted to strings
            for recommendation in analysis.recommendations:
                if isinstance(recommendation, str):
                    action_items.append(recommendation)
                elif isinstance(recommendation, dict):
                    # Convert dict to string representation
                    action_items.append(str(recommendation))
                else:
                    # Convert other types to string
                    action_items.append(str(recommendation))
        
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