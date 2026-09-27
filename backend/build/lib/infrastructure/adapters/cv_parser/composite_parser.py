"""Composite parser: selecciona el adaptador correcto según el mime type."""
from domain.exceptions import CVProcessingError
from infrastructure.adapters.cv_parser.ocr_parser import OcrCvParser
from infrastructure.adapters.cv_parser.pdf_parser import PdfCvParser

_PDF_MIME = "application/pdf"
_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}


class CompositeCvParser:
    """Delega la extracción al parser correcto según el tipo de archivo."""

    def __init__(self) -> None:
        self._pdf_parser = PdfCvParser()
        self._ocr_parser = OcrCvParser()

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        if mime_type == _PDF_MIME:
            return self._pdf_parser.extract_text(file_bytes, mime_type)
        if mime_type in _IMAGE_MIMES:
            return self._ocr_parser.extract_text(file_bytes, mime_type)
        raise CVProcessingError(
            f"Tipo de archivo no soportado: '{mime_type}'. "
            "Use PDF, JPG, PNG o WEBP."
        )
