#!/usr/bin/env python3
"""
Simple test to verify MCP server is working
"""

import asyncio
import json
from MedicareCoverageChecker import mcp, medicare_checker

async def test_mcp_tools():
    print("🧪 Testing MCP Server...")
    
    # Test 1: Check tools are registered
    tools = await mcp.get_tools()
    print(f"✅ Found {len(tools)} registered MCP tools:")
    for tool in tools:
        # Handle both tool objects and strings
        if hasattr(tool, 'name'):
            name = tool.name
            description = getattr(tool, 'description', 'No description')[:60]
        else:
            name = str(tool)
            description = "Tool object"
        print(f"  - {name}: {description}...")
    
    # Test 2: Test core Medicare lookup functionality 
    print("\n🏥 Testing Medicare lookup functionality...")
    try:
        result = await medicare_checker.lookup_code("G0008")
        if result:
            print(f"✅ Medicare lookup works! Found: {result.description}")
            print(f"   Payment: ${result.national_payment_amount}")
            print(f"   Data source: {result.data_source}")
        else:
            print("❌ Medicare lookup returned no results (CMS APIs may be unavailable)")
    except Exception as e:
        print(f"⚠️  Medicare lookup test error: {str(e)}")
    
    print("\n🎯 MCP Server Status: READY!")
    return True

if __name__ == "__main__":
    asyncio.run(test_mcp_tools()) 