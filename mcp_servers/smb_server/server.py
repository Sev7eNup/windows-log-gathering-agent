#!/usr/bin/env python3
"""
MCP Server for SMB/CIFS file access on remote Windows machines.
Provides tools for reading log files via SMB shares.
"""

import asyncio
import json
import logging
import tempfile
from typing import Any, Dict, List, Optional
from pathlib import Path
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    Tool,
    TextContent,
)
import os
import stat as os_stat

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("smb-mcp-server")


class SMBClient:
    """Manages SMB connections and file operations."""
    
    def __init__(self):
        self.sessions: Dict[str, bool] = {}
    
    def ensure_session(self, hostname: str, username: str, password: str, 
                      domain: str = None) -> str:
        """For localhost testing, just return a mock session key."""
        session_key = f"{hostname}:{username}"
        
        if session_key not in self.sessions:
            # For localhost testing, no actual SMB session needed
            if hostname in ['localhost', '127.0.0.1']:
                self.sessions[session_key] = True
                logger.info(f"Mock SMB session created for localhost testing")
            else:
                logger.warning(f"SMB sessions to remote hosts not supported in test mode: {hostname}")
                raise Exception(f"Remote SMB access not supported in test mode: {hostname}")
        
        return session_key
    
    def read_file_tail(self, hostname: str, username: str, password: str,
                      file_path: str, lines: int = 1000, domain: str = None) -> Dict[str, Any]:
        """Read the last N lines of a file via local access for localhost testing."""
        try:
            self.ensure_session(hostname, username, password, domain)
            
            # For localhost testing, convert path format to local Windows path
            if hostname in ['localhost', '127.0.0.1']:
                # Convert C$/path format to C:\path
                if file_path.startswith("C$/"):
                    local_path = file_path.replace("C$/", "C:\\").replace("/", "\\")
                else:
                    # Use os.path.join to avoid f-string backslash issues
                    clean_path = file_path.replace('/', '\\')
                    local_path = f"C:\\{clean_path}"
                
                # Read the file locally
                if not os.path.exists(local_path):
                    return {
                        "success": False,
                        "error": f"File not found: {local_path}",
                        "content": "",
                        "file_path": file_path
                    }
                
                with open(local_path, 'r', encoding='utf-8', errors='replace') as f:
                    all_lines = f.readlines()
                    tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    content = ''.join(tail_lines)
                
                return {
                    "success": True,
                    "content": content,
                    "lines_read": len(tail_lines),
                    "total_lines": len(all_lines),
                    "file_path": file_path
                }
            else:
                return {
                    "success": False,
                    "error": "Remote SMB access not supported in test mode",
                    "content": "",
                    "file_path": file_path
                }
            
        except Exception as e:
            logger.error(f"Error reading {file_path} from {hostname}: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "file_path": file_path
            }
    
    def list_directory(self, hostname: str, username: str, password: str,
                      dir_path: str, domain: str = None) -> Dict[str, Any]:
        """List contents of a directory via local access for localhost testing."""
        try:
            self.ensure_session(hostname, username, password, domain)
            
            if hostname in ['localhost', '127.0.0.1']:
                # Convert to local path
                if dir_path.startswith("C$/"):
                    local_path = dir_path.replace("C$/", "C:\\").replace("/", "\\")
                else:
                    clean_path = dir_path.replace('/', '\\')
                    local_path = f"C:\\{clean_path}"
                
                if not os.path.exists(local_path):
                    return {
                        "success": False,
                        "error": f"Directory not found: {local_path}",
                        "files": [],
                        "directory": dir_path
                    }
                
                files = []
                for item in os.listdir(local_path):
                    try:
                        item_path = os.path.join(local_path, item)
                        file_stat = os.stat(item_path)
                        files.append({
                            "name": item,
                            "size": file_stat.st_size,
                            "modified": file_stat.st_mtime,
                            "is_dir": os_stat.S_ISDIR(file_stat.st_mode)
                        })
                    except Exception as e:
                        logger.warning(f"Failed to stat {item}: {e}")
                        files.append({
                            "name": item,
                            "size": 0,
                            "modified": 0,
                            "is_dir": False
                        })
                
                return {
                    "success": True,
                    "files": files,
                    "directory": dir_path
                }
            else:
                return {
                    "success": False,
                    "error": "Remote SMB access not supported in test mode",
                    "files": [],
                    "directory": dir_path
                }
            
        except Exception as e:
            logger.error(f"Error listing directory {dir_path} on {hostname}: {e}")
            return {
                "success": False,
                "error": str(e),
                "files": [],
                "directory": dir_path
            }
    
    def check_file_exists(self, hostname: str, username: str, password: str,
                         file_path: str, domain: str = None) -> Dict[str, Any]:
        """Check if a file exists and get its basic info via local access for localhost testing."""
        try:
            self.ensure_session(hostname, username, password, domain)
            
            if hostname in ['localhost', '127.0.0.1']:
                # Convert to local path
                if file_path.startswith("C$/"):
                    local_path = file_path.replace("C$/", "C:\\").replace("/", "\\")
                else:
                    clean_path = file_path.replace('/', '\\')
                    local_path = f"C:\\{clean_path}"
                
                if os.path.exists(local_path):
                    file_stat = os.stat(local_path)
                    return {
                        "success": True,
                        "exists": True,
                        "size": file_stat.st_size,
                        "modified": file_stat.st_mtime,
                        "is_dir": os_stat.S_ISDIR(file_stat.st_mode),
                        "file_path": file_path
                    }
                else:
                    return {
                        "success": True,
                        "exists": False,
                        "file_path": file_path
                    }
            else:
                return {
                    "success": False,
                    "exists": False,
                    "error": "Remote SMB access not supported in test mode",
                    "file_path": file_path
                }
            
        except Exception as e:
            return {
                "success": True,
                "exists": False,
                "error": str(e),
                "file_path": file_path
            }


# Global SMB client
smb_client = SMBClient()


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available SMB tools."""
    return [
        Tool(
            name="read_file_tail",
            description="Read the last N lines of a file via SMB share",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Target hostname or IP address"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username for SMB authentication (DOMAIN\\user format)"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for SMB authentication"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to file (e.g., 'C$/Windows/CCM/Logs/WUAHandler.log')"
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Number of lines to read from end of file",
                        "default": 1000
                    },
                    "domain": {
                        "type": "string",
                        "description": "Domain name (optional if included in username)"
                    }
                },
                "required": ["hostname", "username", "password", "file_path"]
            }
        ),
        Tool(
            name="list_directory",
            description="List contents of a directory via SMB share",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Target hostname or IP address"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username for SMB authentication"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for SMB authentication"
                    },
                    "dir_path": {
                        "type": "string",
                        "description": "Directory path (e.g., 'C$/Windows/CCM/Logs')"
                    },
                    "domain": {
                        "type": "string",
                        "description": "Domain name (optional)"
                    }
                },
                "required": ["hostname", "username", "password", "dir_path"]
            }
        ),
        Tool(
            name="check_file_exists",
            description="Check if a file exists and get basic information",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Target hostname or IP address"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username for SMB authentication"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for SMB authentication"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to check"
                    },
                    "domain": {
                        "type": "string",
                        "description": "Domain name (optional)"
                    }
                },
                "required": ["hostname", "username", "password", "file_path"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool execution requests."""
    
    if name == "read_file_tail":
        result = smb_client.read_file_tail(
            hostname=arguments["hostname"],
            username=arguments["username"],
            password=arguments["password"],
            file_path=arguments["file_path"],
            lines=arguments.get("lines", 1000),
            domain=arguments.get("domain")
        )
        
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]
        )
    
    elif name == "list_directory":
        result = smb_client.list_directory(
            hostname=arguments["hostname"],
            username=arguments["username"],
            password=arguments["password"],
            dir_path=arguments["dir_path"],
            domain=arguments.get("domain")
        )
        
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]
        )
    
    elif name == "check_file_exists":
        result = smb_client.check_file_exists(
            hostname=arguments["hostname"],
            username=arguments["username"],
            password=arguments["password"],
            file_path=arguments["file_path"],
            domain=arguments.get("domain")
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
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, 
            write_stream, 
            InitializationOptions(
                server_name="smb-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())