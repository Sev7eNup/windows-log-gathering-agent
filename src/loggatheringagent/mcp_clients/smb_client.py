"""
SMB MCP client for remote file access.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger(__name__)


class SMBMCPClient:
    """Client for interacting with the SMB MCP server."""
    
    def __init__(self, server_path: str = None):
        """Initialize SMB MCP client."""
        self.server_path = server_path or "mcp_servers/smb_server/server.py"
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
                # Test server initialization with a simple call
                result = await self.client_session.call_tool(
                    "check_file_exists", 
                    {
                        "hostname": "localhost",
                        "username": "test",
                        "password": "test",
                        "file_path": "C$/test.txt"
                    }
                )
                # If we get a response (even if it's an error), server is initialized
                logger.info(f"SMB MCP server initialized successfully after {attempt + 1} attempts")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.debug(f"SMB server not ready, attempt {attempt + 1}/{max_retries}: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"SMB server failed to initialize after {max_retries} attempts: {e}")
                    raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client_session:
            await self.client_session.__aexit__(exc_type, exc_val, exc_tb)
        if self.stdio_client:
            await self.stdio_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def read_file_tail(self, hostname: str, username: str, password: str,
                           file_path: str, lines: int = 1000,
                           domain: Optional[str] = None) -> Dict[str, Any]:
        """Read the last N lines of a file via SMB."""
        if not self.client_session:
            raise RuntimeError("Client session not initialized. Use as async context manager.")
        
        try:
            args = {
                "hostname": hostname,
                "username": username,
                "password": password,
                "file_path": file_path,
                "lines": lines
            }
            
            if domain:
                args["domain"] = domain
            
            result = await self.client_session.call_tool("read_file_tail", args)
            
            if result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            else:
                return {"success": False, "error": "No content returned"}
                
        except Exception as e:
            logger.error(f"Error reading file {file_path} from {hostname}: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "file_path": file_path
            }
    
    async def list_directory(self, hostname: str, username: str, password: str,
                           dir_path: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """List contents of a directory via SMB."""
        if not self.client_session:
            raise RuntimeError("Client session not initialized. Use as async context manager.")
        
        try:
            args = {
                "hostname": hostname,
                "username": username,
                "password": password,
                "dir_path": dir_path
            }
            
            if domain:
                args["domain"] = domain
            
            result = await self.client_session.call_tool("list_directory", args)
            
            if result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            else:
                return {"success": False, "error": "No content returned"}
                
        except Exception as e:
            logger.error(f"Error listing directory {dir_path} on {hostname}: {e}")
            return {
                "success": False,
                "error": str(e),
                "files": [],
                "directory": dir_path
            }
    
    async def check_file_exists(self, hostname: str, username: str, password: str,
                              file_path: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Check if a file exists and get basic information."""
        if not self.client_session:
            raise RuntimeError("Client session not initialized. Use as async context manager.")
        
        try:
            args = {
                "hostname": hostname,
                "username": username,
                "password": password,
                "file_path": file_path
            }
            
            if domain:
                args["domain"] = domain
            
            result = await self.client_session.call_tool("check_file_exists", args)
            
            if result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            else:
                return {"success": False, "error": "No content returned"}
                
        except Exception as e:
            logger.error(f"Error checking file {file_path} on {hostname}: {e}")
            return {
                "success": False,
                "error": str(e),
                "exists": False,
                "file_path": file_path
            }