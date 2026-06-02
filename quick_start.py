#!/usr/bin/env python3
"""
quick_start.py - AgentOS Quick Start Guide
Demonstrates the main features of the system including:
- Simple & Complex requests
- Context Compression for long conversations
- Dashboard access
"""

import sys
import time
from database import DBManager
from orchestrator_main import AgentOrchestrator
from schemas import TaskPriority
from context_compression import ContextCompressor

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def demo_simple_request():
    """Demo 1: Simple request (direct agent execution)"""
    print_header("Demo 1: Simple Request")
    
    db = DBManager()
    orch = AgentOrchestrator(db)
    
    request = "Write a professional LinkedIn post about AI innovation"
    print(f"📝 Request: {request}")
    print("\n⏳ Processing...")
    
    result = orch.handle_request(request, priority=TaskPriority.MEDIUM)
    
    print("\n✅ Result:")
    if isinstance(result, dict):
        print(f"  Status: {result.get('status', 'unknown')}")
        print(f"  Task ID: {result.get('meta', {}).get('task_id', 'N/A')}")
    else:
        print(f"  {result}")

def demo_complex_request():
    """Demo 2: Complex request (DAG execution)"""
    print_header("Demo 2: Complex Request (DAG Execution)")
    
    db = DBManager()
    orch = AgentOrchestrator(db)
    
    request = "Research the latest advances in quantum computing, synthesize findings, and create a Twitter thread for tech enthusiasts"
    print(f"📝 Request: {request}")
    print("\n⏳ Processing (this may take 20-30 seconds)...")
    
    result = orch.handle_request(request, priority=TaskPriority.HIGH)
    
    print("\n✅ Result:")
    if isinstance(result, dict):
        print(f"  Status: {result.get('status', 'unknown')}")
        print(f"  Steps: {len(result.get('meta', {}).get('dag', []))} subtasks executed")
        print(f"  Artifacts: {len(result.get('artifacts', []))} outputs generated")
    else:
        print(f"  {result}")

def demo_context_compression():
    """Demo 3: Context Compression for long conversations"""
    print_header("Demo 3: Context Compression (Long Conversations)")
    
    compressor = ContextCompressor()
    
    # Simulate a long conversation
    long_history = [
        {"role": "user", "content": "Tell me about machine learning"},
        {"role": "assistant", "content": "Machine learning is a subset of AI that focuses on learning from data..."},
        {"role": "user", "content": "What are neural networks?"},
        {"role": "assistant", "content": "Neural networks are computational models inspired by biological neurons..."},
        {"role": "user", "content": "How do they work in practice?"},
        {"role": "assistant", "content": "In practice, neural networks are trained using backpropagation..."},
        {"role": "user", "content": "What about deep learning?"},
        {"role": "assistant", "content": "Deep learning uses multiple layers of neural networks..."},
        {"role": "user", "content": "Can you summarize the conversation so far?"},
        {"role": "assistant", "content": "Of course! We've discussed ML, neural networks, their implementation, and deep learning..."},
        {"role": "user", "content": "What's the next step for learning?"},
        {"role": "assistant", "content": "I'd recommend studying transformer architectures next..."},
    ]
    
    current_request = "Create a comprehensive study plan for mastering AI and machine learning"
    
    print(f"📊 Input: {len(long_history)} messages in history")
    print(f"📝 Current Request: {current_request}")
    print("\n⏳ Compressing context...")
    
    result = compressor.handle_context_overflow(long_history, current_request)
    
    print("\n✅ Compression Results:")
    print(f"  Original Tokens: {result['original_tokens']}")
    print(f"  Optimized Tokens: {result['optimized_tokens']}")
    compression_ratio = (1 - result['optimized_tokens']/result['original_tokens'])*100
    print(f"  Compression Ratio: {compression_ratio:.1f}% reduction")
    print(f"  Critical Items: {len(result['tiers'].get('tier_1', []))}")
    print(f"  Important Items: {len(result['tiers'].get('tier_2', []))}")
    print(f"  Optional Items: {len(result['tiers'].get('tier_3', []))}")

def demo_dashboard_guide():
    """Demo 4: Guide for using the Observability Dashboard"""
    print_header("Demo 4: Observability Dashboard Guide")
    
    print("🚀 To start the dashboard, run:")
    print("   streamlit run dashboard.py")
    print("\n📊 Dashboard Tabs:")
    print("   1. DAG Flow      - Visualize task execution timeline")
    print("   2. Token Analytics - Monitor token consumption by agent")
    print("   3. System Health  - View performance metrics and SRE report")
    print("   4. Deep Trace     - Inspect individual task execution")
    print("\n💡 Tips:")
    print("   - Auto-refresh: Set refresh rate in sidebar (5-60 seconds)")
    print("   - Filter: Select specific session ID to view related tasks")
    print("   - Export: Click on charts to download as PNG")

def print_menu():
    """Print main menu"""
    print_header("AgentOS - Quick Start Demo")
    print("Choose a demo to run:")
    print("1. Simple Request (Direct Agent)")
    print("2. Complex Request (DAG Execution)")
    print("3. Context Compression (Long Conversations)")
    print("4. Dashboard Guide")
    print("5. Run All Demos")
    print("0. Exit")

def main():
    while True:
        print_menu()
        choice = input("\n👉 Enter your choice (0-5): ").strip()
        
        if choice == "0":
            print("\n👋 Goodbye!")
            break
        elif choice == "1":
            try:
                demo_simple_request()
            except Exception as e:
                print(f"\n❌ Error: {e}")
        elif choice == "2":
            try:
                demo_complex_request()
            except Exception as e:
                print(f"\n❌ Error: {e}")
        elif choice == "3":
            try:
                demo_context_compression()
            except Exception as e:
                print(f"\n❌ Error: {e}")
        elif choice == "4":
            try:
                demo_dashboard_guide()
            except Exception as e:
                print(f"\n❌ Error: {e}")
        elif choice == "5":
            print("\n⏳ Running all demos (this may take a minute)...")
            try:
                demo_simple_request()
                time.sleep(2)
                demo_complex_request()
                time.sleep(2)
                demo_context_compression()
                time.sleep(2)
                demo_dashboard_guide()
            except Exception as e:
                print(f"\n❌ Error: {e}")
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
