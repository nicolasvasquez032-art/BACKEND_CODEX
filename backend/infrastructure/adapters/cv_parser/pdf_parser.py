"""Parser de CV para archivos PDF usando pdfplumber."""
import io

import pdfplumber

from domain.exceptions import CVProcessingError


class PdfCvParser:
    """Extrae texto de un archivo PDF usando pdfplumber."""

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages_text = [
                    page.extract_text() or ""
                    for page in pdf.pages
                ]
            return "\n".join(pages_text).strip()
        except Exception as exc:
            raise CVProcessingError(f"Error al procesar el PDF: {exc}") from exc
