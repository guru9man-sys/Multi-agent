"""
accounting_data_agent.py - Agent for processing transfer slips and financial documents.
Reads PDF or Excel transfer bills, extracts transaction details, and persists summaries to the database.
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd
from database import DBManager
from document_parser import parser
from schemas import TaskRequest, TaskResponse, TaskStatus, TaskAction
from utils.logger import logger
from config import config
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    service_account = None
    build = None
    MediaFileUpload = None


class AccountingDataAgent:
    """Agent to parse transfer slips and record accounting summaries."""

    def __init__(self, db_manager: DBManager, storage_dir: Optional[str] = None):
        self.db = db_manager
        self.storage_dir = storage_dir or os.path.join(os.path.dirname(__file__), "accounting_data")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.google_drive_folder_id = config.GOOGLE_DRIVE_FOLDER_ID
        self.google_sheets_spreadsheet_id = config.GOOGLE_SHEETS_SPREADSHEET_ID
        self.google_upload_default_target = config.GOOGLE_UPLOAD_DEFAULT_TARGET
        self.google_scopes = [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        self.google_credentials = self._build_google_credentials()

    def _build_google_credentials(self):
        if service_account is None:
            logger.warning("Google API libraries are not installed. Google Drive/Sheets integration disabled.")
            return None

        if config.GOOGLE_SERVICE_ACCOUNT_FILE and os.path.exists(config.GOOGLE_SERVICE_ACCOUNT_FILE):
            try:
                return service_account.Credentials.from_service_account_file(
                    config.GOOGLE_SERVICE_ACCOUNT_FILE,
                    scopes=self.google_scopes
                )
            except Exception as e:
                logger.error(f"Failed to build credentials from file: {e}")

        if config.GOOGLE_SERVICE_ACCOUNT_INFO:
            try:
                info = json.loads(config.GOOGLE_SERVICE_ACCOUNT_INFO)
                return service_account.Credentials.from_service_account_info(info, scopes=self.google_scopes)
            except Exception as e:
                logger.error(f"Failed to build credentials from JSON info: {e}")

        logger.info("Google service account credentials not configured.")
        return None

    def _get_drive_service(self):
        if not self.google_credentials or build is None:
            return None
        return build("drive", "v3", credentials=self.google_credentials)

    def _get_sheets_service(self):
        if not self.google_credentials or build is None:
            return None
        return build("sheets", "v4", credentials=self.google_credentials)

    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=False
    )
    def _upload_to_google_drive(self, file_path: str, file_name: str) -> Optional[str]:
        drive_service = self._get_drive_service()
        if drive_service is None:
            return None

        media = MediaFileUpload(file_path, resumable=True)
        file_metadata = {"name": file_name}
        if self.google_drive_folder_id:
            file_metadata["parents"] = [self.google_drive_folder_id]

        try:
            response = drive_service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink, webContentLink").execute()
            return response.get("webViewLink") or response.get("webContentLink")
        except Exception as e:
            logger.error(f"Google Drive upload attempt failed: {e}")
            raise e # Raise for tenacity to retry

    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=False
    )
    def _append_to_google_sheet(self, details: Dict[str, str], sheet_name: str = "Sheet1") -> Optional[str]:
        sheets_service = self._get_sheets_service()
        spreadsheet_id = self.google_sheets_spreadsheet_id
        if sheets_service is None or not spreadsheet_id:
            return None

        row = [
            details.get("transaction_date", ""),
            details.get("amount", ""),
            details.get("sender", ""),
            details.get("recipient", ""),
            details.get("reference", ""),
            details.get("summary", "")
        ]

        body = {"values": [row]}
        range_name = f"{sheet_name}!A:F"
        try:
            sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        except Exception as e:
            logger.error(f"Google Sheets append attempt failed: {e}")
            raise e # Raise for tenacity to retry

    def execute(self, request: TaskRequest) -> TaskResponse:
        task_id = request.task_id
        file_path = request.payload.get("file_path")
        upload_target = request.payload.get("upload_target", self.google_upload_default_target or "local_excel")
        sheet_name = request.payload.get("sheet_name")

        if not file_path:
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": "Missing file_path in payload."},
                error_message="Missing file_path"
            )

        if not os.path.exists(file_path):
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": f"File not found: {file_path}"},
                error_message="File not found"
            )

        logger.info(f"AccountingDataAgent: Processing {file_path}")

        parsed = self._parse_document(file_path, sheet_name)
        if "error" in parsed:
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": parsed["error"]},
                error_message=parsed["error"]
            )

        extracted_text = self._combine_parsed_text(parsed)
        summary, details = self._extract_transaction_details(extracted_text)

        saved_path, upload_result = self._save_summary_to_excel(task_id, details, upload_target)
        db_entry_id = self.db.save_accounting_entry({
            "file_path": file_path,
            "document_type": parsed.get("format", "unknown"),
            "transaction_date": details.get("transaction_date"),
            "amount": details.get("amount"),
            "sender": details.get("sender"),
            "recipient": details.get("recipient"),
            "reference": details.get("reference"),
            "summary": summary,
            "extracted_text": extracted_text,
            "metadata": {
                "source_file": file_path,
                "saved_path": saved_path,
                "upload_target": upload_target,
                "upload_result": upload_result,
                "timestamp": datetime.now().isoformat()
            }
        })

        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            artifacts={
                "summary": summary,
                "details": details,
                "saved_path": saved_path,
                "upload_result": upload_result,
                "db_entry_id": db_entry_id,
                "document_type": parsed.get("format", "unknown")
            },
            meta={
                "confidence": 0.85,
                "timestamp": datetime.now().isoformat()
            }
        )

    def _parse_document(self, file_path: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        lower = file_path.lower()
        if lower.endswith(".pdf"):
            return parser.parse_pdf(file_path)
        if lower.endswith(('.xlsx', '.xls')):
            return parser.parse_excel(file_path, sheet_name)
        return {"error": "Unsupported document format. Please provide PDF or Excel."}

    def _combine_parsed_text(self, parsed: Dict[str, Any]) -> str:
        if parsed.get("format") == "pdf":
            return parsed.get("full_text", "") + "\n\n" + parsed.get("tables", "")
        if parsed.get("format") == "excel":
            if "data" in parsed:
                return parsed["data"]
            elif "sheets" in parsed:
                return "\n\n".join(parsed["sheets"].values())
        return ""

    def _extract_transaction_details(self, text: str) -> (str, Dict[str, str]):
        normalized = self._normalize_text(text)

        transaction_date = self._extract_date(normalized)
        amount = self._extract_amount(normalized)
        sender = self._extract_field(normalized, [r"ผู้โอน[:：]?", r"ชื่อผู้โอน[:：]?", r"จากบัญชี[:：]?"])
        recipient = self._extract_field(normalized, [r"ผู้รับ[:：]?", r"ชื่อผู้รับ[:：]?", r"เข้าบัญชี[:：]?"])
        reference = self._extract_field(normalized, [r"หมายเหตุ[:：]?", r"Ref[:：]?", r"reference[:：]?", r"รายการ[:：]?"])

        amount_clean = amount or self._extract_amount(normalized, allow_decimal=True)

        details = {
            "transaction_date": transaction_date or "ไม่พบวันที่",
            "amount": amount_clean or "ไม่พบจำนวนเงิน",
            "sender": sender or "ไม่พบผู้โอน",
            "recipient": recipient or "ไม่พบผู้รับ",
            "reference": reference or "ไม่พบหมายเหตุ",
            "source_snippet": normalized[:1200]
        }

        summary_lines = [
            f"วันที่ทำรายการ: {details['transaction_date']}",
            f"จำนวนเงิน: {details['amount']}",
            f"ผู้โอน: {details['sender']}",
            f"ผู้รับ: {details['recipient']}",
            f"หมายเหตุ/รายการ: {details['reference']}"
        ]

        return "\n".join(summary_lines), details

    def _normalize_text(self, text: str) -> str:
        cleaned = text.replace("\u200b", " ").replace("\xa0", " ")
        return re.sub(r"\s+", " ", cleaned).strip()

    def _extract_field(self, text: str, patterns: list) -> Optional[str]:
        for pattern in patterns:
            match = re.search(pattern + r"\s*([\wก-๙0-9\-/,.]+)", text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        patterns = [
            r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})",
            r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})"
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_amount(self, text: str, allow_decimal: bool = False) -> Optional[str]:
        if allow_decimal:
            pattern = r"(\d{1,3}(?:[\,\.]\d{3})*(?:[\,\.]\d+))"
        else:
            pattern = r"(\d{1,3}(?:[\,\.]\d{3})+)"
        matches = re.findall(pattern, text)
        if matches:
            return matches[-1].replace(" ", "")
        return None

    def _save_summary_to_excel(self, task_id: str, details: Dict[str, str], upload_target: str) -> (str, Dict[str, Optional[str]]):
        sheet_path = os.path.join(self.storage_dir, f"accounting_summary_{task_id}.xlsx")
        try:
            df = pd.DataFrame([details])
            df.to_excel(sheet_path, index=False)
            upload_result = {"google_drive_link": None, "google_sheet_link": None}
            if upload_target in ["google_drive", "google_drive_and_sheet"]:
                drive_link = self._upload_to_google_drive(sheet_path, os.path.basename(sheet_path))
                upload_result["google_drive_link"] = drive_link
                if drive_link is None:
                    logger.warning("Google Drive upload requested, but failed or credentials missing.")
            if upload_target in ["google_sheet", "google_drive_and_sheet"]:
                sheet_link = self._append_to_google_sheet(details)
                upload_result["google_sheet_link"] = sheet_link
                if sheet_link is None:
                    logger.warning("Google Sheets append requested, but failed or credentials missing.")
            return sheet_path, upload_result
        except Exception as e:
            fallback_path = os.path.join(self.storage_dir, f"accounting_summary_{task_id}.csv")
            try:
                df = pd.DataFrame([details])
                df.to_csv(fallback_path, index=False, encoding="utf-8-sig")
                return fallback_path, {"google_drive_link": None, "google_sheet_link": None}
            except Exception as secondary_error:
                logger.error(f"Failed to save summary file: {e}; {secondary_error}")
                return "Failed to save summary file", {"google_drive_link": None, "google_sheet_link": None}
