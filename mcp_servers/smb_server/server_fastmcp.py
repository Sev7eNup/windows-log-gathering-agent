#!/usr/bin/env python3
"""
FastMCP Server for SMB/CIFS file access on remote Windows machines.
Provides tools for reading log files via SMB shares.
"""

import os
import stat as os_stat
import logging
from typing import Any, Dict
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP app
mcp = FastMCP("SMB File Access Server")


@mcp.tool()
def read_file_tail(hostname: str, username: str, password: str,
                  file_path: str, lines: int = 1000, domain: str = None) -> Dict[str, Any]:
    """Read the last N lines of a file via local access for localhost testing."""
    try:
        # For localhost testing, convert path format to local Windows path
        if hostname in ['localhost', '127.0.0.1']:
            # Convert C$/path format to C:\\path
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


@mcp.tool()
def list_directory(hostname: str, username: str, password: str,
                  dir_path: str, domain: str = None) -> Dict[str, Any]:
    """List contents of a directory via local access for localhost testing."""
    try:
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


@mcp.tool()
def check_file_exists(hostname: str, username: str, password: str,
                     file_path: str, domain: str = None) -> Dict[str, Any]:
    """Check if a file exists and get its basic info via local access for localhost testing."""
    try:
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


if __name__ == "__main__":
    mcp.run()