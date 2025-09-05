#!/usr/bin/env python3
"""
Debug script to test full log collection pipeline
"""
import asyncio
import os
import sys
sys.path.append('src')

from loggatheringagent.config.settings import Settings
from loggatheringagent.core.log_collector import WindowsLogCollector

async def test_full_collection():
    """Test complete log collection pipeline"""
    print("=== Testing Full Log Collection Pipeline ===")
    
    # Initialize settings and collector
    settings = Settings()
    collector = WindowsLogCollector(settings)
    
    # Load machines config to see what's configured
    print("1. Loading machines configuration...")
    config = settings.load_machines_config()
    
    localhost_client = None
    for client in config.clients:
        if client.name == "LOCALHOST":
            localhost_client = client
            break
    
    if localhost_client:
        print(f"Found LOCALHOST client: {localhost_client.hostname}")
        print(f"Log paths configured: {localhost_client.log_paths}")
        print(f"PowerShell commands: {len(localhost_client.powershell_commands)}")
    else:
        print("LOCALHOST client not found!")
        return
    
    # Test log collection
    print("\n2. Testing log collection...")
    log_collection = await collector.collect_client_logs("LOCALHOST")
    
    print(f"Collection success: {log_collection.success}")
    print(f"Number of log results: {len(log_collection.log_results)}")
    print(f"Errors: {log_collection.errors}")
    
    print("\n3. Log results breakdown:")
    for i, result in enumerate(log_collection.log_results):
        print(f"  [{i+1}] {result.source}")
        print(f"      Success: {result.success}")
        print(f"      Lines: {result.lines_count}")
        if result.error:
            print(f"      Error: {result.error}")
        if result.content:
            preview = result.content[:100].replace('\n', ' ')
            print(f"      Preview: {preview}...")
        print()

if __name__ == "__main__":
    asyncio.run(test_full_collection())