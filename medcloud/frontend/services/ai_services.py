"""
Placeholder service module for future AI integration.
Contains stub functions and integration points for:
- OCR Processing
- Report Text Extraction
- AI Summary Generation
- Medical Scan Analysis

Do NOT implement actual AI here; instead, call these functions from views/tasks when ready.
"""


def ocr_process(file_path: str) -> str:
    """Run OCR on the given file and return extracted plain text.

    Integration point: Replace body with call to OCR engine (Tesseract, AWS Textract, GCP Vision).
    """
    # TODO: integrate OCR engine
    return ""


def extract_report_text(ocr_text: str) -> dict:
    """Extract structured fields from OCR text (dates, values, diagnoses).

    Returns a dict with extracted fields.
    """
    # TODO: implement extraction logic or call to NLP pipeline
    return {}


def generate_ai_summary(extracted_data: dict) -> str:
    """Generate a short AI summary from extracted report data.

    Integration point: call a model or external API to produce summary.
    """
    # TODO: call AI model / service
    return ""


def analyze_medical_scan(file_path: str) -> dict:
    """Analyze medical scans (xray, ct) and return findings placeholder.

    Integration point for future scan analysis models.
    """
    # TODO: integrate scan analysis model
    return {}
