#!/usr/bin/env python3
"""
FastMCP Server for remote PowerShell execution on Windows machines.
Provides tools for executing PowerShell commands remotely via WinRM.
"""

import logging
from typing import Any, Dict, List, Optional
from fastmcp import FastMCP
import subprocess
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP app
mcp = FastMCP("PowerShell Execution Server")


@mcp.tool()
def execute_powershell(hostname: str, username: str, password: str,
                      command: str, transport: str = "ntlm") -> Dict[str, Any]:
    """Execute a PowerShell command on a remote Windows machine via WinRM."""
    try:
        # For localhost testing, execute locally
        if hostname in ['localhost', '127.0.0.1']:
            # Execute PowerShell command locally
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "status_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
        else:
            return {
                "status_code": -1,
                "stdout": "",
                "stderr": "Remote PowerShell execution not supported in test mode",
                "success": False
            }
            
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return {
            "status_code": -1,
            "stdout": "",
            "stderr": str(e),
            "success": False
        }


@mcp.tool()
def get_windows_update_log(hostname: str, username: str, password: str,
                          output_path: str = "C:\\temp\\WindowsUpdate.log") -> Dict[str, Any]:
    """Get Windows Update log from remote machine using Get-WindowsUpdateLog cmdlet."""
    command = f"""
    # Create temp directory if it doesn't exist
    New-Item -ItemType Directory -Path C:\\temp -Force | Out-Null
    
    # Generate Windows Update log
    Get-WindowsUpdateLog -LogPath "{output_path}"
    
    # Read and return the last 1000 lines
    if (Test-Path "{output_path}") {{
        $content = Get-Content "{output_path}" -Tail 1000
        $content -join "`n"
    }} else {{
        "Failed to generate Windows Update log"
    }}
    """
    
    return execute_powershell(hostname, username, password, command)


@mcp.tool()
def get_event_log(hostname: str, username: str, password: str,
                 log_name: str = "System", max_events: int = 100,
                 event_ids: Optional[List[int]] = None,
                 source_filter: Optional[str] = None) -> Dict[str, Any]:
    """Query Windows Event Log from remote machine."""
    # Build the PowerShell command
    command = f"Get-WinEvent -LogName {log_name} -MaxEvents {max_events}"
    
    filters = []
    if event_ids:
        event_id_list = ",".join(map(str, event_ids))
        filters.append(f"$_.Id -in @({event_id_list})")
    
    if source_filter:
        filters.append(f"$_.ProviderName -like '{source_filter}'")
    
    if filters:
        filter_string = " -and ".join(filters)
        command += f" | Where-Object {{{filter_string}}}"
    
    command += " | Select-Object TimeCreated, Id, LevelDisplayName, ProviderName, Message | ConvertTo-Json -Depth 3"
    
    return execute_powershell(hostname, username, password, command)


if __name__ == "__main__":
    mcp.run()