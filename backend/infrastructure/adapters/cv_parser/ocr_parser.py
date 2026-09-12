"""Parser de CV para imágenes usando pytesseract + Pillow (OCR)."""
import io

from PIL import Image
import pytesseract

from domain.exceptions import CVProcessingError


class OcrCvParser:
    """Extrae texto de una imagen de CV usando OCR (pytesseract).

    Requiere que Tesseract OCR esté instalado en el sistema operativo.
    Configurado para reconocer texto en español e inglés.
    """

    _TESSERACT_LANG = "spa+eng"

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        try:
            image = Image.open(io.BytesIO(file_bytes))
            # Convertir a escala de grises mejora la precisión del OCR
            image = image.convert("L")
            text: str = pytesseract.image_to_string(image, lang=self._TESSERACT_LANG)
            return text.strip()
        except CVProcessingError:
            raise
        except Exception as exc:
            raise CVProcessingError(f"Error en OCR de la imagen: {exc}") from exc
