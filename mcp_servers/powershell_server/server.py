#!/usr/bin/env python3
"""
MCP Server for remote PowerShell execution on Windows machines.
Provides tools for executing PowerShell commands remotely via WinRM.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    Tool,
    TextContent,
)
import winrm
from winrm.exceptions import WinRMError
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("powershell-mcp-server")


class PowerShellSession:
    """Manages WinRM PowerShell sessions to remote Windows machines."""
    
    def __init__(self):
        self.sessions: Dict[str, winrm.Session] = {}
    
    def get_session(self, hostname: str, username: str, password: str, 
                   transport: str = "ntlm") -> winrm.Session:
        """Get or create a WinRM session to a remote machine."""
        session_key = f"{hostname}:{username}"
        
        if session_key not in self.sessions:
            try:
                session = winrm.Session(
                    f"http://{hostname}:5985/wsman",
                    auth=(username, password),
                    transport=transport
                )
                # Test the connection
                result = session.run_ps("Write-Output 'Connection test'")
                if result.status_code != 0:
                    raise WinRMError(f"Connection test failed: {result.std_err}")
                
                self.sessions[session_key] = session
                logger.info(f"Created WinRM session to {hostname}")
            except Exception as e:
                logger.error(f"Failed to create session to {hostname}: {e}")
                raise
        
        return self.sessions[session_key]
    
    def execute_command(self, hostname: str, username: str, password: str,
                       command: str) -> Dict[str, Any]:
        """Execute a PowerShell command on a remote machine."""
        try:
            session = self.get_session(hostname, username, password)
            result = session.run_ps(command)
            
            return {
                "status_code": result.status_code,
                "stdout": result.std_out.decode('utf-8', errors='replace'),
                "stderr": result.std_err.decode('utf-8', errors='replace'),
                "success": result.status_code == 0
            }
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "status_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False
            }


# Global PowerShell session manager
ps_manager = PowerShellSession()


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available PowerShell tools."""
    return [
        Tool(
            name="execute_powershell",
            description="Execute a PowerShell command on a remote Windows machine via WinRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Target hostname or IP address"
                    },
                    "username": {
                        "type": "string", 
                        "description": "Username for authentication (domain\\user format)"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for authentication"
                    },
                    "command": {
                        "type": "string",
                        "description": "PowerShell command to execute"
                    },
                    "transport": {
                        "type": "string",
                        "description": "WinRM transport (ntlm, kerberos, basic)",
                        "default": "ntlm"
                    }
                },
                "required": ["hostname", "username", "password", "command"]
            }
        ),
        Tool(
            name="get_windows_update_log",
            description="Get Windows Update log from remote machine using Get-WindowsUpdateLog",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Target hostname or IP address"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username for authentication"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for authentication"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path for the log file (default: C:\\temp\\WindowsUpdate.log)",
                        "default": "C:\\temp\\WindowsUpdate.log"
                    }
                },
                "required": ["hostname", "username", "password"]
            }
        ),
        Tool(
            name="get_event_log",
            description="Query Windows Event Log from remote machine",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Target hostname or IP address"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username for authentication"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for authentication"
                    },
                    "log_name": {
                        "type": "string",
                        "description": "Event log name (System, Application, etc.)",
                        "default": "System"
                    },
                    "max_events": {
                        "type": "integer",
                        "description": "Maximum number of events to retrieve",
                        "default": 100
                    },
                    "event_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Specific event IDs to filter (optional)"
                    },
                    "source_filter": {
                        "type": "string",
                        "description": "Filter events by source (e.g., '*SCCM*')"
                    }
                },
                "required": ["hostname", "username", "password"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool execution requests."""
    
    if name == "execute_powershell":
        result = ps_manager.execute_command(
            hostname=arguments["hostname"],
            username=arguments["username"],
            password=arguments["password"],
            command=arguments["command"]
        )
        
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]
        )
    
    elif name == "get_windows_update_log":
        output_path = arguments.get("output_path", "C:\\temp\\WindowsUpdate.log")
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
        
        result = ps_manager.execute_command(
            hostname=arguments["hostname"],
            username=arguments["username"],
            password=arguments["password"],
            command=command
        )
        
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]
        )
    
    elif name == "get_event_log":
        log_name = arguments.get("log_name", "System")
        max_events = arguments.get("max_events", 100)
        event_ids = arguments.get("event_ids", [])
        source_filter = arguments.get("source_filter", "")
        
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
        
        result = ps_manager.execute_command(
            hostname=arguments["hostname"],
            username=arguments["username"],
            password=arguments["password"],
            command=command
        )
        
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]
        )
    
    else:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )
            ],
            isError=True
        )


async def main():
    """Main entry point for the MCP server."""
    # Run the server using stdin/stdout streams
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, 
            write_stream, 
            InitializationOptions(
                server_name="powershell-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())