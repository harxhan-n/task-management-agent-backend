#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.agent import TaskManagementAgent

async def test_agent():
    """Test the agent's context awareness for task updates"""
    print("Testing Task Management Agent Context Awareness...")
    print("=" * 60)
    
    agent = TaskManagementAgent()
    
    # Test 1: Create a task
    print("\n1. Creating a task...")
    result1 = await agent.process_message("Create a task called 'testing'")
    print(f"Response: {result1['response']}")
    
    # Test 2: Try to add description (should UPDATE, not create new)
    print("\n2. Adding description to the task...")
    result2 = await agent.process_message("add the description as I need to testing the task management app")
    print(f"Response: {result2['response']}")
    
    # Test 3: Add priority (should UPDATE, not create new) 
    print("\n3. Setting priority...")
    result3 = await agent.process_message("set the priority as high")
    print(f"Response: {result3['response']}")
    
    # Test 4: List all tasks to verify no duplicates
    print("\n4. Listing all tasks to verify no duplicates...")
    result4 = await agent.process_message("show me all tasks")
    print(f"Response: {result4['response']}")
    
    print("\n" + "=" * 60)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_agent())