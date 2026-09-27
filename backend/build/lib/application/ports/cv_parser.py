from typing import Protocol


class CvParserPort(Protocol):
    """Puerto para la extracción de texto desde archivos de CV.

    Soporta PDF y archivos de imagen (JPG, PNG).
    """

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        """Extrae el texto de un archivo de CV.

        Args:
            file_bytes: Contenido binario del archivo.
            mime_type:  Tipo MIME del archivo, p. ej. 'application/pdf',
                        'image/jpeg', 'image/png'.

        Returns:
            Texto extraído como cadena de caracteres.

        Raises:
            CVProcessingError: Si el formato no está soportado o la extracción falla.
        """
        raise NotImplementedError
