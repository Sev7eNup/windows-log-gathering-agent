"""
Log collector that orchestrates gathering logs from Windows machines using MCP clients.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..config.settings import Settings, MachinesConfig, ClientConfig, CredentialConfig
from ..mcp_clients.direct_local_client import DirectLocalClient
from ..mcp_clients.smb_client import SMBMCPClient
from ..mcp_clients.powershell_client import PowerShellMCPClient

logger = logging.getLogger(__name__)


@dataclass
class LogCollectionResult:
    """Result of log collection from a single source."""
    source: str
    success: bool
    content: str
    error: Optional[str] = None
    lines_count: int = 0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ClientLogCollection:
    """Complete log collection result for a client machine."""
    client_name: str
    hostname: str
    success: bool
    log_results: List[LogCollectionResult]
    errors: List[str]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class WindowsLogCollector:
    """Collects logs from Windows machines using MCP servers."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.machines_config = settings.load_machines_config()
    
    async def collect_client_logs(self, client_name: str) -> ClientLogCollection:
        """Collect all logs from a specific client machine."""
        logger.info(f"Starting log collection for client: {client_name}")
        
        # Find client configuration
        client_config = None
        for client in self.machines_config.clients:
            if client.name == client_name:
                client_config = client
                break
        
        if not client_config:
            return ClientLogCollection(
                client_name=client_name,
                hostname="unknown",
                success=False,
                log_results=[],
                errors=[f"Client '{client_name}' not found in configuration"]
            )
        
        # Get credentials
        cred_config = self.machines_config.credentials.get(client_config.credentials)
        if not cred_config:
            return ClientLogCollection(
                client_name=client_name,
                hostname=client_config.hostname,
                success=False,
                log_results=[],
                errors=[f"Credentials '{client_config.credentials}' not found"]
            )
        
        log_results = []
        errors = []
        
        # Choose client based on hostname - use DirectLocalClient for localhost, MCP clients for remote
        is_localhost = client_config.hostname in ['localhost', '127.0.0.1']
        
        if is_localhost:
            # Use DirectLocalClient for localhost
            async with DirectLocalClient() as local_client:
                # Collect file-based logs
                smb_results = await self._collect_file_logs(client_config, cred_config, local_client)
                log_results.extend(smb_results["results"])
                errors.extend(smb_results["errors"])
                
                # Collect PowerShell-based logs
                ps_results = await self._collect_powershell_logs(client_config, cred_config, local_client)
                log_results.extend(ps_results["results"])
                errors.extend(ps_results["errors"])
        else:
            # Use MCP clients for remote machines
            try:
                # Collect file-based logs using SMB MCP client
                async with SMBMCPClient() as smb_client:
                    smb_results = await self._collect_file_logs_mcp(client_config, cred_config, smb_client)
                    log_results.extend(smb_results["results"])
                    errors.extend(smb_results["errors"])
                
                # Collect PowerShell-based logs using PowerShell MCP client
                async with PowerShellMCPClient() as ps_client:
                    ps_results = await self._collect_powershell_logs_mcp(client_config, cred_config, ps_client)
                    log_results.extend(ps_results["results"])
                    errors.extend(ps_results["errors"])
            except Exception as e:
                logger.error(f"MCP client error for {client_config.hostname}: {e}")
                errors.append(f"MCP client connection failed: {e}")
        
        overall_success = len(errors) == 0 and any(result.success for result in log_results)
        
        return ClientLogCollection(
            client_name=client_name,
            hostname=client_config.hostname,
            success=overall_success,
            log_results=log_results,
            errors=errors
        )
    
    async def _collect_file_logs(self, client_config: ClientConfig, 
                              cred_config: CredentialConfig, local_client: DirectLocalClient) -> Dict[str, Any]:
        """Collect file-based logs using direct local client."""
        results = []
        errors = []
        
        try:
            # Collect all file-based logs
            all_log_paths = []
            for category, paths in client_config.log_paths.items():
                all_log_paths.extend(paths)
            
            for log_path in all_log_paths:
                try:
                    logger.info(f"Reading log file: {log_path}")
                    
                    result = await local_client.read_file_tail(
                        hostname=client_config.hostname,
                        username=cred_config.username,
                        password=cred_config.password,
                        file_path=log_path,
                        lines=self.settings.log_tail_lines,
                        domain=cred_config.domain
                    )
                    
                    if result["success"]:
                        log_result = LogCollectionResult(
                            source=f"FILE:{log_path}",
                            success=True,
                            content=result["content"],
                            lines_count=result.get("lines_read", 0)
                        )
                    else:
                        log_result = LogCollectionResult(
                            source=f"FILE:{log_path}",
                            success=False,
                            content="",
                            error=result.get("error", "Unknown file error")
                        )
                        errors.append(f"File error for {log_path}: {result.get('error', 'Unknown error')}")
                    
                    results.append(log_result)
                    
                except Exception as e:
                    error_msg = f"Exception collecting {log_path}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    
                    results.append(LogCollectionResult(
                        source=f"FILE:{log_path}",
                        success=False,
                        content="",
                        error=str(e)
                    ))
        
        except Exception as e:
            error_msg = f"File collection failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        return {"results": results, "errors": errors}
    
    async def _collect_powershell_logs(self, client_config: ClientConfig,
                                     cred_config: CredentialConfig, local_client: DirectLocalClient) -> Dict[str, Any]:
        """Collect PowerShell-based logs using direct local client."""
        results = []
        errors = []
        
        try:
            for command in client_config.powershell_commands:
                try:
                    logger.info(f"Executing PowerShell command: {command}")
                    
                    if "Get-WindowsUpdateLog" in command:
                        # Special handling for Windows Update Log
                        result = await local_client.get_windows_update_log(
                            hostname=client_config.hostname,
                            username=cred_config.username,
                            password=cred_config.password
                        )
                    elif "Get-WinEvent" in command:
                        # Extract parameters for Event Log query
                        if "System" in command:
                            log_name = "System"
                        elif "Application" in command:
                            log_name = "Application"
                        else:
                            log_name = "System"
                        
                        # Extract event IDs if specified
                        event_ids = []
                        if "@(" in command and ")" in command:
                            ids_part = command.split("@(")[1].split(")")[0]
                            event_ids = [int(x.strip()) for x in ids_part.split(",")]
                        
                        # Extract source filter
                        source_filter = None
                        if "Source -like" in command:
                            source_part = command.split("Source -like")[1].strip()
                            source_filter = source_part.strip("'\"").replace("*", "*")
                        
                        result = await local_client.get_event_log(
                            hostname=client_config.hostname,
                            username=cred_config.username,
                            password=cred_config.password,
                            log_name=log_name,
                            max_events=100,
                            event_ids=event_ids if event_ids else None,
                            source_filter=source_filter
                        )
                    else:
                        # Generic PowerShell command execution
                        result = await local_client.execute_powershell(
                            hostname=client_config.hostname,
                            username=cred_config.username,
                            password=cred_config.password,
                            command=command
                        )
                    
                    if result["success"]:
                        log_result = LogCollectionResult(
                            source=f"PowerShell:{command[:50]}...",
                            success=True,
                            content=result["stdout"],
                            lines_count=result["stdout"].count("\n") if result["stdout"] else 0
                        )
                    else:
                        log_result = LogCollectionResult(
                            source=f"PowerShell:{command[:50]}...",
                            success=False,
                            content=result.get("stdout", ""),
                            error=result.get("stderr", "Unknown PowerShell error")
                        )
                        errors.append(f"PowerShell error for '{command}': {result.get('stderr', 'Unknown error')}")
                    
                    results.append(log_result)
                    
                except Exception as e:
                    error_msg = f"Exception executing '{command}': {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    
                    results.append(LogCollectionResult(
                        source=f"PowerShell:{command[:50]}...",
                        success=False,
                        content="",
                        error=str(e)
                    ))
        
        except Exception as e:
            error_msg = f"PowerShell command execution failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        return {"results": results, "errors": errors}
    
    async def collect_multiple_clients(self, client_names: List[str]) -> List[ClientLogCollection]:
        """Collect logs from multiple clients concurrently."""
        logger.info(f"Starting concurrent log collection for {len(client_names)} clients")
        
        tasks = [self.collect_client_logs(client_name) for client_name in client_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that occurred
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception collecting logs for {client_names[i]}: {result}")
                final_results.append(ClientLogCollection(
                    client_name=client_names[i],
                    hostname="unknown",
                    success=False,
                    log_results=[],
                    errors=[f"Collection failed with exception: {str(result)}"]
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _collect_file_logs_mcp(self, client_config: ClientConfig, 
                                   cred_config: CredentialConfig, smb_client: SMBMCPClient) -> Dict[str, Any]:
        """Collect file-based logs using SMB MCP client for remote machines."""
        results = []
        errors = []
        
        try:
            # Collect all file-based logs
            all_log_paths = []
            for category, paths in client_config.log_paths.items():
                all_log_paths.extend(paths)
            
            for log_path in all_log_paths:
                try:
                    logger.info(f"Reading remote log file: {log_path}")
                    
                    result = await smb_client.read_file_tail(
                        hostname=client_config.hostname,
                        username=cred_config.username,
                        password=cred_config.password,
                        file_path=log_path,
                        lines=self.settings.log_tail_lines,
                        domain=cred_config.domain
                    )
                    
                    success = result.get("success", False)
                    content = result.get("content", "")
                    lines_read = result.get("lines_read", 0)
                    
                    results.append(LogCollectionResult(
                        source=f"SMB:{log_path}",
                        success=success,
                        content=content,
                        error=result.get("error") if not success else None,
                        lines_count=lines_read
                    ))
                    
                except Exception as e:
                    error_msg = f"Failed to read {log_path}: {str(e)}"
                    logger.error(error_msg)
                    results.append(LogCollectionResult(
                        source=f"SMB:{log_path}",
                        success=False,
                        content="",
                        error=error_msg
                    ))
        
        except Exception as e:
            error_msg = f"SMB MCP client error: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        return {"results": results, "errors": errors}
    
    async def _collect_powershell_logs_mcp(self, client_config: ClientConfig, 
                                         cred_config: CredentialConfig, ps_client: PowerShellMCPClient) -> Dict[str, Any]:
        """Collect PowerShell-based logs using PowerShell MCP client for remote machines."""
        results = []
        errors = []
        
        try:
            for command in client_config.powershell_commands:
                try:
                    logger.info(f"Executing remote PowerShell command: {command}")
                    
                    if "Get-WindowsUpdateLog" in command:
                        # Special handling for Windows Update Log
                        result = await ps_client.get_windows_update_log(
                            hostname=client_config.hostname,
                            username=cred_config.username,
                            password=cred_config.password
                        )
                    elif "Get-WinEvent" in command:
                        # Extract parameters for Event Log query
                        if "System" in command:
                            log_name = "System"
                        elif "Application" in command:
                            log_name = "Application"
                        else:
                            log_name = "System"
                        
                        # Extract max events
                        max_events = 100
                        if "MaxEvents" in command:
                            try:
                                max_events = int(command.split("MaxEvents")[1].split()[0])
                            except:
                                max_events = 100
                        
                        result = await ps_client.get_event_log(
                            hostname=client_config.hostname,
                            username=cred_config.username,
                            password=cred_config.password,
                            log_name=log_name,
                            max_events=max_events
                        )
                    else:
                        # Generic PowerShell command execution
                        result = await ps_client.execute_powershell(
                            hostname=client_config.hostname,
                            username=cred_config.username,
                            password=cred_config.password,
                            command=command
                        )
                    
                    success = result.get("success", False)
                    content = result.get("stdout", "") or result.get("content", "")
                    
                    results.append(LogCollectionResult(
                        source=f"PowerShell:{command[:50]}...",
                        success=success,
                        content=content,
                        error=result.get("stderr") or result.get("error") if not success else None,
                        lines_count=len(content.split('\n')) if content else 0
                    ))
                    
                except Exception as e:
                    error_msg = f"PowerShell command '{command}' failed: {str(e)}"
                    logger.error(error_msg)
                    results.append(LogCollectionResult(
                        source=f"PowerShell:{command[:50]}...",
                        success=False,
                        content="",
                        error=error_msg
                    ))
        
        except Exception as e:
            error_msg = f"PowerShell MCP client error: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        return {"results": results, "errors": errors}