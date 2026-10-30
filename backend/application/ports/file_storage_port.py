from abc import ABC, abstractmethod


class FileStoragePort(ABC):
    """Puerto para el almacenamiento y generación de URLs temporales de archivos (ej. AWS S3)."""

    @abstractmethod
    async def upload_file(self, file_bytes: bytes, file_name: str, content_type: str) -> str:
        """Sube un archivo a almacenamiento de objetos y devuelve la clave/identificador único del archivo."""
        ...

    @abstractmethod
    async def generate_presigned_url(self, file_key: str, expires_in_seconds: int = 900) -> str:
        """Genera una URL temporal prefirmada (por defecto 15 min) para descarga segura del archivo."""
        ...
