"""
telegram_bot.py - Telegram Integration Bridge
Connects the Agent System API Gateway to Telegram.
"""

import asyncio
import logging
import httpx
import os
from dotenv import load_dotenv
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- Configuration ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN") 
GATEWAY_URL = os.getenv("AGENTOS_API_URL", "http://localhost:8000") + "/chat"

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "สวัสดีครับ! ผมคือ Agent System Bot 🤖\n\n"
        "📋 ฟีเจอร์ที่รองรับ:\n"
        "1️⃣ 📅 จองนัดหมาย - พิมพ์: 'ผมต้องการจองนัดหมาย'\n"
        "2️⃣ 🔍 วิจัยข้อมูล - พิมพ์: 'ช่วยวิจัยเรื่อง [หัวข้อ]'\n"
        "3️⃣ 📝 สร้างเนื้อหา - พิมพ์: 'สร้างโพสต์สำหรับ [แพลตฟอร์ม]'\n"
        "4️⃣ 💊 วิเคราะห์ข้อมูล - พิมพ์: 'วิเคราะห์ [ข้อมูล]'\n"
        "5️⃣ 🏥 ตรวจสถานะระบบ - พิมพ์: 'ตรวจสถานะระบบ'\n\n"
        "คุณสามารถส่งข้อความให้ผมช่วยจัดการได้เลยครับ! 😊"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    user_text = update.message.text
    session_id = str(update.message.chat_id) # Use Telegram Chat ID as session_id
    
    logger.info(f"Received message from {session_id}: {user_text[:50]}...")

    # 1. Send "typing..." action to let user know the agent is thinking
    await context.bot.send_chat_action(chat_id=session_id, action=constants.ChatAction.TYPING)

    try:
        # 2. Forward request to the API Gateway
        async with httpx.AsyncClient(timeout=90.0) as client:
            payload = {
                "message": user_text,
                "session_id": session_id,
                "priority": "MEDIUM"
            }
            response = await client.post(GATEWAY_URL, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                # Extract the answer from artifacts
                artifacts = data.get("artifacts", {})
                
                # Handle different artifact formats (string or dict)
                if isinstance(artifacts, dict):
                    # For booking appointments, handle special cases
                    if "prompt" in artifacts:
                        # This is a multi-turn collection step
                        answer = artifacts.get("prompt", "")
                        if "validation_error" in artifacts:
                            answer = artifacts.get("validation_error", "")
                    elif "summary" in artifacts:
                        # Appointment confirmation
                        answer = artifacts.get("summary", "")
                    elif "progress" in artifacts:
                        # Progress update
                        progress = artifacts.get("progress", "")
                        prompt = artifacts.get("prompt", "")
                        answer = f"{progress}\n{prompt}"
                    else:
                        # Try to find the most relevant answer in the dict
                        answer = (artifacts.get("final_answer") or 
                                 artifacts.get("result") or 
                                 artifacts.get("summary") or 
                                 artifacts.get("message") or 
                                 str(artifacts))
                else:
                    answer = artifacts if artifacts else "ระบบประมวลผลสำเร็จ แต่ไม่มีคำตอบส่งกลับมาครับ"
                
                await update.message.reply_text(answer, parse_mode="HTML")
            else:
                logger.error(f"Gateway Error: {response.status_code} - {response.text}")
                await update.message.reply_text("❌ ขออภัยครับ เกิดข้อผิดพลาดในการเชื่อมต่อกับระบบ Agent")

    except httpx.ReadTimeout:
        await update.message.reply_text("⏳ คำถามนี้ใช้เวลาประมวลผลนานเกินไป กรุณาลองใหม่อีกครั้งหรือแบ่งคำถามให้เล็กลงครับ")
    except Exception as e:
        logger.exception(f"Unexpected Error: {e}")
        await update.message.reply_text("⚠️ เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาลองใหม่อีกครั้งในภายหลัง")

if __name__ == '__main__':
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("❌ Error: Please set your TELEGRAM_TOKEN in telegram_bot.py")
    else:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        # Handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

        print("🚀 Telegram Bot Bridge is running...")
        app.run_polling()
