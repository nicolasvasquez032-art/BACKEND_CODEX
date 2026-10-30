import asyncio
from pathlib import Path
from uuid import uuid4
from loguru import logger

from application.ports.file_storage_port import FileStoragePort
from infrastructure.config import settings


class S3FileStorageAdapter(FileStoragePort):
    """Adaptador de almacenamiento en AWS S3 con generación de Presigned URLs y fallback resiliente."""

    def __init__(self) -> None:
        self._bucket = settings.s3_bucket_name
        self._region = settings.aws_region
        self._access_key = settings.aws_access_key_id
        self._secret_key = settings.aws_secret_access_key
        self._local_storage_dir = Path("uploads/cvs")
        self._local_storage_dir.mkdir(parents=True, exist_ok=True)

    def _is_aws_configured(self) -> bool:
        return bool(self._access_key and self._secret_key)

    async def upload_file(self, file_bytes: bytes, file_name: str, content_type: str) -> str:
        clean_name = Path(file_name).name
        file_key = f"cvs/{uuid4()}_{clean_name}"

        if self._is_aws_configured():
            try:
                import boto3
                loop = asyncio.get_running_loop()
                def _upload():
                    s3 = boto3.client(
                        "s3",
                        region_name=self._region,
                        aws_access_key_id=self._access_key,
                        aws_secret_access_key=self._secret_key,
                    )
                    s3.put_object(  # NOSONAR
                        Bucket=self._bucket,
                        Key=file_key,
                        Body=file_bytes,
                        ContentType=content_type,
                    )
                await loop.run_in_executor(None, _upload)
                logger.info(f"Archivo subido exitosamente a S3: s3://{self._bucket}/{file_key}")
                return file_key
            except Exception as e:
                logger.error(f"Error subiendo a S3 ({e}), usando almacenamiento local de respaldo.")

        # Fallback local resiliente
        local_path = self._local_storage_dir / Path(file_key).name
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, local_path.write_bytes, file_bytes)
        logger.info(f"Archivo guardado en almacenamiento local: {local_path}")
        return file_key

    async def generate_presigned_url(self, file_key: str, expires_in_seconds: int = 900) -> str:
        if self._is_aws_configured():
            try:
                import boto3
                loop = asyncio.get_running_loop()
                def _get_url():
                    s3 = boto3.client(
                        "s3",
                        region_name=self._region,
                        aws_access_key_id=self._access_key,
                        aws_secret_access_key=self._secret_key,
                    )
                    return s3.generate_presigned_url(  # NOSONAR
                        "get_object",
                        Params={"Bucket": self._bucket, "Key": file_key},
                        ExpiresIn=expires_in_seconds,
                    )
                return await loop.run_in_executor(None, _get_url)
            except Exception as e:
                logger.error(f"Error generando presigned URL en S3 ({e})")

        clean_key = Path(file_key).name
        return f"{settings.frontend_url}/api/v1/cvs/download/{clean_key}"
