"""
test_booking_appointment.py - Test the Booking Appointment Agent
Tests the multi-turn appointment booking flow.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

from database import DBManager
from booking_appointment_agent import BookingAppointmentAgent
from schemas import TaskRequest, TaskAction, AgentRole, TaskPriority


async def test_multi_turn_booking():
    """Test multi-turn appointment booking flow."""
    print("\n" + "="*70)
    print("[TEST] Multi-Turn Appointment Booking")
    print("="*70 + "\n")
    
    # Initialize database and agent
    db = DBManager()
    agent = BookingAppointmentAgent(db)
    
    session_id = "test_session_001"
    
    # Test data: simulating user responses
    user_responses = [
        "สมชาย",  # first_name
        "สมศรี",  # last_name
        "08x-xxx-xxxx",  # phone (invalid first)
        "0812345678",  # phone (valid)
        "2026-05-20",  # date
        "14:30",  # time
        "มีอาการปวดศีรษะ"  # notes
    ]
    
    print("📋 Simulating booking appointment conversation...\n")
    
    current_step = 0
    for i, response in enumerate(user_responses):
        print(f"\n--- Step {i+1} ---")
        
        # Create task request for information collection
        task = TaskRequest(
            task_id=f"task_{i}",
            agent_role=AgentRole.BOOKING_AGENT,
            action=TaskAction.COLLECT_INFO,
            priority=TaskPriority.MEDIUM,
            payload={
                "session_id": session_id,
                "user_input": response if i > 0 else ""  # First request has no input
            }
        )
        
        # Process the task
        result = await agent.process_task(task)
        
        print(f"Status: {result.status}")
        print(f"Response:")
        
        artifacts = result.artifacts
        if "prompt" in artifacts:
            print(f"  📝 {artifacts['prompt']}")
        if "validation_error" in artifacts:
            print(f"  ❌ {artifacts['validation_error']}")
        if "summary" in artifacts:
            print(f"  ✓ Appointment confirmed!")
            print(artifacts['summary'])
        if "progress" in artifacts:
            print(f"  📊 {artifacts['progress']}")
        
        if result.status.value == "completed":
            print("\n✅ Booking completed successfully!")
            break
    
    print("\n" + "="*70)
    print("✓ Test completed")
    print("="*70 + "\n")


async def test_direct_booking():
    """Test direct appointment booking (all info at once)."""
    print("\n" + "="*70)
    print("🧪 TEST: Direct Appointment Booking")
    print("="*70 + "\n")
    
    db = DBManager()
    agent = BookingAppointmentAgent(db)
    
    # Create task with all information
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    task = TaskRequest(
        task_id="direct_booking_001",
        agent_role=AgentRole.BOOKING_AGENT,
        action=TaskAction.BOOK_APPOINTMENT,
        priority=TaskPriority.HIGH,
        payload={
            "session_id": "direct_test_session",
            "first_name": "นายดำ",
            "last_name": "น้อย",
            "phone_number": "0891234567",
            "preferred_date": tomorrow,
            "preferred_time": "10:00",
            "notes": "ต้องการตรวจสุขภาพทั่วไป"
        }
    )
    
    print("📋 Direct booking request:")
    print(f"  Name: {task.payload['first_name']} {task.payload['last_name']}")
    print(f"  Phone: {task.payload['phone_number']}")
    print(f"  Date: {task.payload['preferred_date']}")
    print(f"  Time: {task.payload['preferred_time']}")
    print(f"  Notes: {task.payload['notes']}\n")
    
    result = await agent.process_task(task)
    
    print(f"Result: {result.status}")
    if result.status.value == "completed":
        apt = result.artifacts.get("appointment")
        print(f"\n[OK] Appointment created successfully!")
        print(f"  Appointment ID: {result.artifacts['appointment_id']}")
        print(f"  Status: {result.artifacts['status']}")
    else:
        print(f"[ERROR] Error: {result.error_message}")
    
    print("\n" + "="*70)
    print("✓ Test completed")
    print("="*70 + "\n")


async def test_appointment_management():
    """Test appointment status checking."""
    print("\n" + "="*70)
    print("🧪 TEST: Appointment Status Checking")
    print("="*70 + "\n")
    
    db = DBManager()
    agent = BookingAppointmentAgent(db)
    
    # First, create an appointment
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    create_task = TaskRequest(
        task_id="create_for_check",
        agent_role=AgentRole.BOOKING_AGENT,
        action=TaskAction.BOOK_APPOINTMENT,
        priority=TaskPriority.MEDIUM,
        payload={
            "session_id": "check_test_session",
            "first_name": "นางสาว",
            "last_name": "ชมพู",
            "phone_number": "0898765432",
            "preferred_date": tomorrow,
            "preferred_time": "15:00",
            "notes": None
        }
    )
    
    create_result = await agent.process_task(create_task)
    if create_result.status.value != "completed":
        print("[ERROR] Failed to create appointment for testing")
        return
    
    appointment_id = create_result.artifacts['appointment_id']
    print(f"[OK] Created test appointment: {appointment_id}\n")
    
    # Now check its status
    check_task = TaskRequest(
        task_id="check_status",
        agent_role=AgentRole.BOOKING_AGENT,
        action=TaskAction.MANAGE_APPOINTMENT,
        priority=TaskPriority.MEDIUM,
        payload={
            "operation": "check_status",
            "appointment_id": appointment_id
        }
    )
    
    check_result = await agent.process_task(check_task)
    
    if check_result.status.value == "completed":
        artifacts = check_result.artifacts
        print("[INFO] Appointment Status:")
        print(f"  ID: {artifacts['appointment_id']}")
        print(f"  Status: {artifacts['status']}")
        print(f"  Date: {artifacts['date']}")
        print(f"  Time: {artifacts['time']}")
        print(f"  Customer: {artifacts['customer']}")
        print("\n[OK] Status check successful!")
    else:
        print(f"[ERROR] Error: {check_result.error_message}")
    
    print("\n" + "="*70)
    print("✓ Test completed")
    print("="*70 + "\n")


async def main():
    """Run all tests."""
    print("\n🚀 Starting Booking Appointment Agent Tests\n")
    
    # Test 1: Multi-turn booking
    await test_multi_turn_booking()
    
    # Test 2: Direct booking
    await test_direct_booking()
    
    # Test 3: Appointment management
    await test_appointment_management()
    
    print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
