"""
document_parser.py - Advanced Document Analysis Layer
Provides capabilities to extract and structure data from PDF and Excel files.
"""

import os
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from utils.logger import logger

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

class DocumentParser:
    """
    Handles extraction of text and tables from complex document formats.
    Converts binary/structured files into LLM-friendly Markdown/JSON.
    """

    def __init__(self):
        logger.info("DocumentParser initialized. PDF and Excel support enabled.")

    def parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Extracts text and tables from a PDF file.
        Returns a dictionary containing the full text and extracted tables.
        """
        if pdfplumber is None:
            return {"error": "pdfplumber library not installed. Please run 'pip install pdfplumber'"}

        if not os.path.exists(file_path):
            return {"error": f"PDF file not found at {file_path}"}

        try:
            logger.info(f"Parsing PDF: {file_path}")
            full_text = []
            all_tables = []

            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    # Extract Text
                    text = page.extract_text()
                    if text:
                        full_text.append(f"--- Page {i+1} ---\n{text}")
                    
                    # Extract Tables
                    tables = page.extract_tables()
                    for table in tables:
                        # Convert table to a simple markdown-like string
                        table_str = self._table_to_markdown(table)
                        all_tables.append(f"Table on Page {i+1}:\n{table_str}")

            return {
                "full_text": "\n\n".join(full_text),
                "tables": "\n\n".join(all_tables),
                "page_count": len(pdf.pages),
                "format": "pdf"
            }
        except Exception as e:
            logger.exception(f"PDF Parsing Error: {e}")
            return {"error": f"Failed to parse PDF: {str(e)}"}

    def parse_excel(self, file_path: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts data from an Excel file (.xlsx, .xls).
        Returns a dictionary with sheet names and their content as markdown tables.
        """
        if not os.path.exists(file_path):
            return {"error": f"Excel file not found at {file_path}"}

        try:
            logger.info(f"Parsing Excel: {file_path}")
            
            # Read excel file
            # If sheet_name is provided, read only that sheet, otherwise read all
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                return {
                    "sheet_name": sheet_name,
                    "data": df.to_markdown(index=False),
                    "format": "excel"
                }
            else:
                excel_file = pd.ExcelFile(file_path)
                all_sheets = {}
                for sheet in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                    all_sheets[sheet] = df.to_markdown(index=False)
                
                return {
                    "sheets": all_sheets,
                    "format": "excel"
                }
        except Exception as e:
            logger.exception(f"Excel Parsing Error: {e}")
            return {"error": f"Failed to parse Excel: {str(e)}"}

    def _table_to_markdown(self, table: List[List[Any]]) -> str:
        """Helper to convert a list of lists (table) to a markdown table string."""
        if not table or not table[0]:
            return ""
        
        # Clean data: replace None with empty string and remove newlines
        cleaned_table = []
        for row in table:
            cleaned_row = [str(cell).replace("\n", " ").strip() if cell is not None else "" for cell in row]
            cleaned_table.append(cleaned_row)
        
        # Create Markdown table
        headers = cleaned_table[0]
        rows = cleaned_table[1:]
        
        header_line = "| " + " | ".join(headers) + " |"
        separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
        
        body = []
        for row in rows:
            body.append("| " + " | ".join(row) + " |")
            
        return f"{header_line}\n{separator_line}\n" + "\n".join(body)

# Global instance for easy access
parser = DocumentParser()
