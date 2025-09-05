"""
Direct local client for Windows log gathering - bypasses MCP for localhost testing.
"""

import os
import stat as os_stat
import subprocess
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class DirectLocalClient:
    """Direct client that handles both SMB and PowerShell operations locally."""
    
    def __init__(self):
        """Initialize direct local client."""
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    # SMB Functions
    async def read_file_tail(self, hostname: str, username: str, password: str,
                           file_path: str, lines: int = 1000,
                           domain: Optional[str] = None) -> Dict[str, Any]:
        """Read the last N lines of a file locally."""
        try:
            # For localhost testing, convert path format to local Windows path
            if hostname in ['localhost', '127.0.0.1']:
                # Convert C$/path format to C:\\path
                if file_path.startswith("C$/"):
                    local_path = file_path.replace("C$/", "C:\\").replace("/", "\\")
                else:
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
                    "error": "Remote access not supported in test mode",
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
    
    async def list_directory(self, hostname: str, username: str, password: str,
                           dir_path: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """List contents of a directory locally."""
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
                    "error": "Remote access not supported in test mode",
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
    
    async def check_file_exists(self, hostname: str, username: str, password: str,
                              file_path: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Check if a file exists locally."""
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
                    "error": "Remote access not supported in test mode",
                    "file_path": file_path
                }
            
        except Exception as e:
            return {
                "success": True,
                "exists": False,
                "error": str(e),
                "file_path": file_path
            }
    
    # PowerShell Functions
    async def execute_powershell(self, hostname: str, username: str, password: str,
                                command: str, transport: str = "ntlm") -> Dict[str, Any]:
        """Execute a PowerShell command locally."""
        try:
            # For localhost testing, execute locally
            if hostname in ['localhost', '127.0.0.1']:
                # Set environment variables for proper encoding
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                env['POWERSHELL_TELEMETRY_OPTOUT'] = '1'
                
                result = subprocess.run(
                    ["powershell", "-OutputFormat", "Text", "-NonInteractive", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                    encoding='utf-8',
                    errors='replace'
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
    
    async def get_windows_update_log(self, hostname: str, username: str, password: str,
                                   output_path: str = "C:\\temp\\WindowsUpdate.log") -> Dict[str, Any]:
        """Get Windows Update log locally."""
        command = f'''
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
        '''
        
        return await self.execute_powershell(hostname, username, password, command)
    
    async def get_event_log(self, hostname: str, username: str, password: str,
                          log_name: str = "System", max_events: int = 100,
                          event_ids: Optional[List[int]] = None,
                          source_filter: Optional[str] = None) -> Dict[str, Any]:
        """Query Windows Event Log locally."""
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
        
        return await self.execute_powershell(hostname, username, password, command)