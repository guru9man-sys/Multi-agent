"""
email_notifier.py - Utility for sending email alerts for audit results.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.logger import logger
from config import config
from tenacity import retry, stop_after_attempt, wait_exponential

class EmailNotifier:
    """Handles sending email notifications for system alerts and audit failures."""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("NOTIFIER_EMAIL")
        self.sender_password = os.getenv("NOTIFIER_PASSWORD")

    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=False # ไม่ให้ crash ระบบหลักหากลองครบ 3 ครั้งแล้วยังล้มเหลว
    )
    def send_audit_alert(self, audit_result: dict, record_id: str):
        """Sends an alert when a financial record is flagged as suspicious."""
        if not self.sender_email or not self.sender_password:
            logger.warning("Email notifier not configured. Skipping email send.")
            return False

        recipient = os.getenv("AUDIT_ALERT_RECIPIENT", self.sender_email)
        
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = recipient
        message["Subject"] = f"🚨 Financial Audit Alert: Record {record_id}"
        
        body = f"""

        สวัสดีครับ,

        QA Auditor พบความผิดปกติในระเบียนการเงิน (Financial Record)
        
        ID: {record_id}
        สถานะ: {audit_result.get('status')}
        รายละเอียดความผิดปกติ: {audit_result.get('issue')}
        ระดับความเชื่อมั่น: {audit_result.get('confidence')}

        กรุณาตรวจสอบไฟล์ต้นฉบับอีกครั้ง
        """
        message.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            logger.info(f"Audit alert email sent to {recipient}")
            return True
        except (smtplib.SMTPException, ConnectionError) as e:
            logger.error(f"SMTP Error occurred: {e}. Retrying...")
            raise e # raise เพื่อให้ tenacity ทำงาน
        except Exception as e:
            logger.error(f"Unexpected error during email dispatch: {e}")
            return False
