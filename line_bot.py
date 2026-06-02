from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# --- Configuration ---
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "YOUR_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_CHANNEL_SECRET")
AGENTOS_API_URL = os.getenv("AGENTOS_API_URL", "http://localhost:8000")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle_body(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    user_id = event.source.user_id
    
    # ส่งต่อไปยัง AgentOS API
    try:
        response = requests.post(
            f"{AGENTOS_API_URL}/chat",
            json={"session_id": user_id, "message": user_text},
            timeout=60
        )
        answer = response.json().get("answer", "ขออภัยครับ เกิดข้อผิดพลาด")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=answer))
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❌ Error: {str(e)}"))

if __name__ == "__main__":
    app.run(port=5000)
