"""
PowerShell MCP client for remote PowerShell execution.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
import httpx
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger(__name__)


class PowerShellMCPClient:
    """Client for interacting with the PowerShell MCP server."""
    
    def __init__(self, server_path: str = None):
        """Initialize PowerShell MCP client."""
        self.server_path = server_path or "mcp_servers/powershell_server/server.py"
        self.client_session: Optional[ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_path]
        )
        
        self.stdio_client = stdio_client(server_params)
        read_stream, write_stream = await self.stdio_client.__aenter__()
        self.client_session = ClientSession(read_stream, write_stream)
        await self.client_session.__aenter__()
        
        # Wait for server to be fully initialized by testing connection
        await self._wait_for_initialization()
        return self
    
    async def _wait_for_initialization(self, max_retries: int = 10, delay: float = 0.5):
        """Wait for MCP server to be fully initialized."""
        for attempt in range(max_retries):
            try:
                # Test server initialization with a simple PowerShell command
                result = await self.client_session.call_tool(
                    "execute_powershell",
                    {
                        "hostname": "localhost",
                        "username": "test",
                        "password": "test",
                        "command": "Write-Output 'test'"
                    }
                )
                # If we get a response (even if it's an error), server is initialized
                logger.info(f"PowerShell MCP server initialized successfully after {attempt + 1} attempts")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.debug(f"PowerShell server not ready, attempt {attempt + 1}/{max_retries}: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"PowerShell server failed to initialize after {max_retries} attempts: {e}")
                    raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client_session:
            await self.client_session.__aexit__(exc_type, exc_val, exc_tb)
        if self.stdio_client:
            await self.stdio_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def execute_powershell(self, hostname: str, username: str, password: str,
                                command: str, transport: str = "ntlm") -> Dict[str, Any]:
        """Execute a PowerShell command on a remote machine."""
        if not self.client_session:
            raise RuntimeError("Client session not initialized. Use as async context manager.")
        
        try:
            result = await self.client_session.call_tool(
                "execute_powershell",
                {
                    "hostname": hostname,
                    "username": username,
                    "password": password,
                    "command": command,
                    "transport": transport
                }
            )
            
            if result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            else:
                return {"success": False, "error": "No content returned"}
                
        except Exception as e:
            logger.error(f"Error executing PowerShell command: {e}")
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }
    
    async def get_windows_update_log(self, hostname: str, username: str, password: str,
                                   output_path: str = "C:\\temp\\WindowsUpdate.log") -> Dict[str, Any]:
        """Get Windows Update log using Get-WindowsUpdateLog cmdlet."""
        if not self.client_session:
            raise RuntimeError("Client session not initialized. Use as async context manager.")
        
        try:
            result = await self.client_session.call_tool(
                "get_windows_update_log",
                {
                    "hostname": hostname,
                    "username": username,
                    "password": password,
                    "output_path": output_path
                }
            )
            
            if result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            else:
                return {"success": False, "error": "No content returned"}
                
        except Exception as e:
            logger.error(f"Error getting Windows Update log: {e}")
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }
    
    async def get_event_log(self, hostname: str, username: str, password: str,
                          log_name: str = "System", max_events: int = 100,
                          event_ids: Optional[List[int]] = None,
                          source_filter: Optional[str] = None) -> Dict[str, Any]:
        """Query Windows Event Log from remote machine."""
        if not self.client_session:
            raise RuntimeError("Client session not initialized. Use as async context manager.")
        
        try:
            args = {
                "hostname": hostname,
                "username": username,
                "password": password,
                "log_name": log_name,
                "max_events": max_events
            }
            
            if event_ids:
                args["event_ids"] = event_ids
            if source_filter:
                args["source_filter"] = source_filter
            
            result = await self.client_session.call_tool("get_event_log", args)
            
            if result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            else:
                return {"success": False, "error": "No content returned"}
                
        except Exception as e:
            logger.error(f"Error getting Event Log: {e}")
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }