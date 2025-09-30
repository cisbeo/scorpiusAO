"""
Storage service for MinIO/S3.
"""
import io
from typing import BinaryIO
from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class StorageService:
    """Service for file storage operations using MinIO."""

    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket_name
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"✅ Created MinIO bucket: {self.bucket_name}")
        except S3Error as e:
            print(f"⚠️  MinIO bucket check error: {e}")

    def upload_file(
        self,
        file_content: bytes,
        object_name: str,
        content_type: str = "application/pdf"
    ) -> str:
        """
        Upload a file to MinIO.

        Args:
            file_content: File content as bytes
            object_name: Object name/path in bucket
            content_type: MIME type of the file

        Returns:
            Object path in bucket
        """
        try:
            file_stream = io.BytesIO(file_content)
            file_size = len(file_content)

            self.client.put_object(
                self.bucket_name,
                object_name,
                file_stream,
                file_size,
                content_type=content_type
            )

            print(f"✅ Uploaded file to MinIO: {object_name} ({file_size} bytes)")
            return object_name

        except S3Error as e:
            print(f"❌ MinIO upload error: {e}")
            raise

    def download_file(self, object_name: str) -> bytes:
        """
        Download a file from MinIO.

        Args:
            object_name: Object name/path in bucket

        Returns:
            File content as bytes
        """
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            file_content = response.read()
            response.close()
            response.release_conn()

            return file_content

        except S3Error as e:
            print(f"❌ MinIO download error: {e}")
            raise

    def delete_file(self, object_name: str) -> None:
        """
        Delete a file from MinIO.

        Args:
            object_name: Object name/path in bucket
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            print(f"✅ Deleted file from MinIO: {object_name}")

        except S3Error as e:
            print(f"❌ MinIO delete error: {e}")
            raise

    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in MinIO.

        Args:
            object_name: Object name/path in bucket

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False

    def get_file_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Get a presigned URL for a file.

        Args:
            object_name: Object name/path in bucket
            expires: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=expires
            )
            return url

        except S3Error as e:
            print(f"❌ MinIO presigned URL error: {e}")
            raise


# Global instance
storage_service = StorageService()
