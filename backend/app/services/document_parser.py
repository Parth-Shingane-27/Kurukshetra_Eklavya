"""Text-layer document parsing only (Section 7.1 of the brief — deliberately no OCR/Tesseract,
matching plan.md's own non-goal boundary on document authenticity verification). A PDF's
embedded text layer can be extracted; a scanned image has no text layer to extract, so its
contents are represented purely by whatever the citizen/operator declares about it — never
inferred, never claimed to be verified.
"""

import base64
import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class DocumentParseError(ValueError):
    pass


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except PdfReadError as exc:
        raise DocumentParseError(f"Could not read PDF: {exc}") from exc
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_text_from_base64_pdf(pdf_base64: str) -> str:
    try:
        raw = base64.b64decode(pdf_base64, validate=True)
    except (base64.binascii.Error, ValueError) as exc:
        raise DocumentParseError(f"Invalid base64 PDF payload: {exc}") from exc
    return extract_text_from_pdf_bytes(raw)
