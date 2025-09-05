"""
FastMCP SMB client for remote file access.
"""

import json
import logging
import asyncio
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class FastMCPSMBClient:
    """Client for interacting with the FastMCP SMB server."""
    
    def __init__(self, server_path: str = None):
        """Initialize FastMCP SMB client."""
        self.server_path = server_path or "mcp_servers/smb_server/server_fastmcp.py"
        self.process: Optional[subprocess.Popen] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Start the FastMCP server as a subprocess
        server_full_path = Path(self.server_path).absolute()
        self.process = subprocess.Popen(
            ["python", str(server_full_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        
        # Give the server a moment to start
        await asyncio.sleep(1.0)
        
        # Test server readiness
        await self._test_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error terminating FastMCP server: {e}")
                try:
                    self.process.kill()
                except:
                    pass
    
    async def _test_connection(self):
        """Test if the server is ready."""
        # For FastMCP, we'll assume it's ready after the startup delay
        logger.info("FastMCP SMB server connection ready")
    
    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool via FastMCP server."""
        try:
            # Create MCP request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Send request to server
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            # Read response
            response_line = self.process.stdout.readline()
            if not response_line:
                raise Exception("No response from FastMCP server")
            
            response = json.loads(response_line)
            
            # Check for errors
            if "error" in response:
                raise Exception(f"FastMCP error: {response['error']}")
            
            # Return the result
            if "result" in response and "content" in response["result"]:
                content = response["result"]["content"]
                if content and len(content) > 0:
                    return json.loads(content[0]["text"])
            
            return {"success": False, "error": "Invalid response format"}
            
        except Exception as e:
            logger.error(f"FastMCP tool call failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def read_file_tail(self, hostname: str, username: str, password: str,
                           file_path: str, lines: int = 1000,
                           domain: Optional[str] = None) -> Dict[str, Any]:
        """Read the last N lines of a file via SMB."""
        args = {
            "hostname": hostname,
            "username": username,
            "password": password,
            "file_path": file_path,
            "lines": lines
        }
        
        if domain:
            args["domain"] = domain
        
        return await self._call_tool("read_file_tail", args)
    
    async def list_directory(self, hostname: str, username: str, password: str,
                           dir_path: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """List contents of a directory via SMB."""
        args = {
            "hostname": hostname,
            "username": username,
            "password": password,
            "dir_path": dir_path
        }
        
        if domain:
            args["domain"] = domain
        
        return await self._call_tool("list_directory", args)
    
    async def check_file_exists(self, hostname: str, username: str, password: str,
                              file_path: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Check if a file exists and get basic information."""
        args = {
            "hostname": hostname,
            "username": username,
            "password": password,
            "file_path": file_path
        }
        
        if domain:
            args["domain"] = domain
        
        return await self._call_tool("check_file_exists", args)