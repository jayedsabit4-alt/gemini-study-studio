"""Document Extraction Module for RAG Pipeline.

Optimized PDF parsing using PyPDF as primary reader to handle large files efficiently.
"""

import io
import json
import logging
from typing import Any, Dict, List, Set, Tuple
import pandas as pd

from config import MAX_TABLE_ROWS
from rag.ocr import extract_text_from_image

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: Set[str] = {
    "pdf", "docx", "pptx", "txt", "md", "json", "csv", "xlsx", "xls", "png", "jpg", "jpeg"
}


def _flatten_json(data: Any, prefix: str = "") -> List[str]:
    lines = []
    if isinstance(data, dict):
        for key, val in data.items():
            new_key = f"{prefix}.{key}" if prefix else str(key)
            lines.extend(_flatten_json(val, new_key))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            new_key = f"{prefix}[{idx}]"
            lines.extend(_flatten_json(item, new_key))
    else:
        lines.append(f"{prefix}: {data}")
    return lines


def extract_pdf(file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any], List[str]]:
    pages_data: List[Dict[str, Any]] = []
    full_text_segments: List[str] = []
    warnings: List[str] = []

    # Primary Parser: PyPDF (Fast & Memory Efficient)
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes), strict=False)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                warnings.append("Could not decrypt protected PDF file.")

        for page_idx, page in enumerate(reader.pages):
            try:
                txt = page.extract_text() or ""
                pages_data.append({"page_number": page_idx + 1, "text": txt})
                if txt.strip():
                    full_text_segments.append(f"--- Page {page_idx + 1} ---\n{txt}")
            except Exception as p_err:
                warnings.append(f"Failed to read page {page_idx + 1}: {str(p_err)}")

    except Exception as pypdf_err:
        logger.warning(f"PyPDF failed for {filename}: {pypdf_err}. Falling back to pdfplumber.")
        pages_data.clear()
        full_text_segments.clear()

        # Fallback Parser: pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    txt = page.extract_text() or ""
                    pages_data.append({"page_number": page_idx + 1, "text": txt})
                    if txt.strip():
                        full_text_segments.append(f"--- Page {page_idx + 1} ---\n{txt}")
        except Exception as plumber_err:
            logger.error(f"pdfplumber fallback failed for {filename}: {plumber_err}")
            warnings.append(f"Fatal PDF parsing error: {str(plumber_err)}")

    metadata = {"total_pages": len(pages_data)}
    return pages_data, "\n\n".join(full_text_segments), metadata, warnings


def extract_docx(file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any], List[str]]:
    warnings: List[str] = []
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        joined_text = "\n".join(paragraphs)
        return [{"page_number": 1, "text": joined_text}], joined_text, {"total_paragraphs": len(paragraphs)}, warnings
    except Exception as err:
        return [{"page_number": 1, "text": ""}], "", {"total_paragraphs": 0}, [f"Failed to parse Word document: {str(err)}"]


def extract_pptx(file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any], List[str]]:
    warnings: List[str] = []
    pages_data: List[Dict[str, Any]] = []
    full_text_segments: List[str] = []

    try:
        from pptx import Presentation
        prs = Presentation(io.BytesIO(file_bytes))
        for idx, slide in enumerate(prs.slides):
            slide_texts = [shape.text.strip() for shape in slide.shapes if hasattr(shape, "text") and shape.text.strip()]
            slide_content = "\n".join(slide_texts)
            pages_data.append({"page_number": idx + 1, "text": slide_content})
            if slide_content:
                full_text_segments.append(f"--- Slide {idx + 1} ---\n{slide_content}")
    except Exception as err:
        warnings.append(f"Failed to parse PowerPoint presentation: {str(err)}")

    return pages_data, "\n\n".join(full_text_segments), {"total_slides": len(pages_data)}, warnings


def extract_csv_excel(file_bytes: bytes, filename: str, ext: str) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any], List[str]]:
    warnings: List[str] = []
    pages_data: List[Dict[str, Any]] = []
    full_text_segments: List[str] = []
    total_rows = 0

    try:
        if ext == "csv":
            df = None
            for encoding in ["utf-8-sig", "utf-8", "cp1252", "latin-1"]:
                try:
                    df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding, on_bad_lines="skip", nrows=MAX_TABLE_ROWS)
                    break
                except Exception:
                    continue

            if df is None:
                raise ValueError("CSV decoding failed.")

            text_rep = df.to_string(index=False)
            pages_data.append({"page_number": 1, "sheet_name": "CSV", "text": text_rep})
            full_text_segments.append(text_rep)
            total_rows = len(df)
            sheet_names = ["CSV"]

        else:
            excel_file = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
            sheet_names = list(excel_file.keys())
            for idx, (sheet, df) in enumerate(excel_file.items()):
                if df.empty:
                    continue
                df = df.head(MAX_TABLE_ROWS)
                sheet_text = f"=== Sheet: {sheet} ===\n" + df.to_string(index=False)
                pages_data.append({"page_number": idx + 1, "sheet_name": sheet, "text": sheet_text})
                full_text_segments.append(sheet_text)
                total_rows += len(df)

    except Exception as err:
        warnings.append(f"Failed to parse tabular file: {str(err)}")
        sheet_names = []

    return pages_data, "\n\n".join(full_text_segments), {"total_rows": total_rows, "sheets": sheet_names}, warnings


def extract_txt_md_json(file_bytes: bytes, filename: str, ext: str) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any], List[str]]:
    warnings: List[str] = []
    raw_text = ""
    for encoding in ["utf-8-sig", "utf-8", "cp1252", "latin-1"]:
        try:
            raw_text = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if ext == "json":
        try:
            parsed = json.loads(raw_text)
            text_content = "\n".join(_flatten_json(parsed))
        except Exception:
            text_content = raw_text
    else:
        text_content = raw_text

    return [{"page_number": 1, "text": text_content}], text_content, {"character_count": len(text_content)}, warnings


def extract_file(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    if not filename or "." not in filename:
        raise ValueError(f"Invalid filename: '{filename}'.")

    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported format '.{ext}'.")

    file_size = len(file_bytes)

    if ext == "pdf":
        pages, text, specific_meta, warnings = extract_pdf(file_bytes, filename)
    elif ext == "docx":
        pages, text, specific_meta, warnings = extract_docx(file_bytes, filename)
    elif ext == "pptx":
        pages, text, specific_meta, warnings = extract_pptx(file_bytes, filename)
    elif ext in ["csv", "xlsx", "xls"]:
        pages, text, specific_meta, warnings = extract_csv_excel(file_bytes, filename, ext)
    elif ext in ["png", "jpg", "jpeg"]:
        img_text, specific_meta, warnings = extract_text_from_image(file_bytes, filename)
        pages = [{"page_number": 1, "text": img_text}]
        text = img_text
    elif ext in ["txt", "md", "json"]:
        pages, text, specific_meta, warnings = extract_txt_md_json(file_bytes, filename, ext)

    return {
        "filename": filename,
        "file_type": ext,
        "pages": pages,
        "text": text,
        "metadata": {"filename": filename, "extension": ext, "size_bytes": file_size, **specific_meta},
        "warnings": warnings,
    }
