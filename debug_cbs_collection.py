#!/usr/bin/env python3
"""
Debug script to test CBS.log file collection directly
"""
import asyncio
import os
import sys
sys.path.append('src')

from loggatheringagent.mcp_clients.direct_local_client import DirectLocalClient

async def test_cbs_collection():
    """Test CBS.log collection directly"""
    print("=== Testing CBS.log Collection ===")
    
    async with DirectLocalClient() as client:
        # Test file existence check
        print("1. Testing file existence check...")
        exists_result = await client.check_file_exists(
            hostname="localhost",
            username="Administrator",
            password="test",
            file_path="C$/Windows/Logs/CBS/CBS.log"
        )
        print(f"File exists result: {exists_result}")
        
        # Test file reading
        print("\n2. Testing file reading...")
        read_result = await client.read_file_tail(
            hostname="localhost",
            username="Administrator", 
            password="test",
            file_path="C$/Windows/Logs/CBS/CBS.log",
            lines=50
        )
        print(f"File read success: {read_result.get('success')}")
        if read_result.get('success'):
            print(f"Lines read: {read_result.get('lines_read')}")
            print(f"Total lines: {read_result.get('total_lines')}")
            print(f"Content preview: {read_result.get('content', '')[:200]}...")
        else:
            print(f"Error: {read_result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_cbs_collection())