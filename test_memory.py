import sys
import os
import json
import asyncio
from pathlib import Path

# Add backend to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from memory import memory_mgr
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
load_dotenv(dotenv_path=env_path)

async def test_memory_system():
    print("--- Testing Memory System ---")
    
    # 1. Test Profile Get/Update
    print("\n1. Testing Profile...")
    profile = memory_mgr.get_profile()
    print(f"Initial Profile Keys: {list(profile.keys())}")
    
    # Test normalization and update
    updates = {"Mail ID": "test@example.com", "mob": "1234567890"}
    updated_profile = memory_mgr.update_profile(updates)
    print(f"Normalized Updates Applied. New Profile Email: {updated_profile.get('email')}, Phone: {updated_profile.get('phone')}")
    
    # 2. Test Episodic Memory (ChromaDB + Embeddings)
    print("\n2. Testing Episodic Memory...")
    print("Adding episode...")
    memory_mgr.add_episode("test_task", "User asked to test the memory system. Everything worked perfectly.", ["email", "phone"])
    
    print("Retrieving context...")
    context = memory_mgr.get_relevant_context("test memory system")
    print(f"Retrieved Context: {context}")
    
    # 3. Test LLM integration (if GEMINI_API_KEY is set)
    print("\n3. Testing LLM Integration...")
    import google.genai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            print("Client initialized. Testing extraction...")
            extraction = memory_mgr.extract_profile_updates_from_message("My new college is MIT", client)
            print(f"Extraction result: {extraction}")
            
            print("Testing summarization...")
            messages = [{"role": "user", "content": "Hello"}, {"role": "model", "content": "Hi, how can I help?"}, {"role": "user", "content": "Can you test the memory?"}]
            summary = memory_mgr.summarize_session(messages, client)
            print(f"Summary result: {summary}")
        except Exception as e:
            print(f"LLM Test failed: {e}")
    else:
        print("GEMINI_API_KEY not found, skipping LLM tests.")

if __name__ == "__main__":
    asyncio.run(test_memory_system())
