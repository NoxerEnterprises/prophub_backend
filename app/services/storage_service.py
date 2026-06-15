from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import UploadFile

from app.core.config import settings
from app.core.enums import MediaType
from app.core.exceptions import BadRequestError


@dataclass(frozen=True)
class UploadedStorageObject:
    path: str
    public_url: str
    content_type: str
    size_bytes: int
    media_type: MediaType


class SupabaseStorageService:
    allowed_image_content_types = {"image/jpeg", "image/png", "image/webp"}
    allowed_image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    allowed_video_content_types = {"video/mp4", "video/webm", "video/quicktime"}
    allowed_video_extensions = {".mp4", ".webm", ".mov"}
    max_image_size_bytes = 5 * 1024 * 1024

    def __init__(self) -> None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise BadRequestError("Supabase storage credentials are not configured")
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.bucket = settings.SUPABASE_STORAGE_BUCKET
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        }

    async def upload_public_image(self, *, file: UploadFile, path: str) -> UploadedStorageObject:
        return await self.upload_public_media(
            file=file,
            path=path,
            allowed_media_types={MediaType.IMAGE},
            max_image_size_bytes=self.max_image_size_bytes,
        )

    async def upload_public_media(
        self,
        *,
        file: UploadFile,
        path: str,
        allowed_media_types: set[MediaType] | None = None,
        max_image_size_bytes: int | None = None,
        max_video_size_bytes: int | None = None,
    ) -> UploadedStorageObject:
        allowed_media_types = allowed_media_types or {MediaType.IMAGE, MediaType.VIDEO}
        max_image_size_bytes = max_image_size_bytes or self.max_image_size_bytes
        max_video_size_bytes = max_video_size_bytes or settings.MAX_CHAT_VIDEO_SIZE_MB * 1024 * 1024

        content_type = file.content_type or ""
        extension = Path(file.filename or "").suffix.lower()
        media_type = self._detect_media_type(content_type=content_type, extension=extension)

        if media_type not in allowed_media_types:
            raise BadRequestError("Unsupported media type for this upload endpoint")

        file_bytes = await file.read()
        size = len(file_bytes)
        if size == 0:
            raise BadRequestError("Uploaded file is empty")
        if media_type == MediaType.IMAGE and size > max_image_size_bytes:
            raise BadRequestError(f"Image size must not exceed {max_image_size_bytes // (1024 * 1024)} MB")
        if media_type == MediaType.VIDEO and size > max_video_size_bytes:
            raise BadRequestError(f"Video size must not exceed {max_video_size_bytes // (1024 * 1024)} MB")

        encoded_path = self._encode_path(path)
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{encoded_path}"
        headers = {
            **self.headers,
            "Content-Type": content_type,
            "Cache-Control": "3600",
            "x-upsert": "false",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, content=file_bytes)

        if response.status_code not in {200, 201}:
            raise BadRequestError("Supabase Storage upload failed", details=response.text)

        return UploadedStorageObject(
            path=path,
            public_url=self.get_public_url(path),
            content_type=content_type,
            size_bytes=size,
            media_type=media_type,
        )

    async def delete_object(self, path: str) -> None:
        encoded_path = self._encode_path(path)
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{encoded_path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self.headers)

        if response.status_code not in {200, 204, 404}:
            raise BadRequestError("Supabase Storage delete failed", details=response.text)

    def get_public_url(self, path: str) -> str:
        return f"{self.base_url}/storage/v1/object/public/{self.bucket}/{self._encode_path(path)}"

    def _detect_media_type(self, *, content_type: str, extension: str) -> MediaType:
        if content_type in self.allowed_image_content_types and extension in self.allowed_image_extensions:
            return MediaType.IMAGE
        if content_type in self.allowed_video_content_types and extension in self.allowed_video_extensions:
            return MediaType.VIDEO
        raise BadRequestError("Only JPEG, PNG, WEBP, MP4, WEBM, and MOV files are allowed")

    @staticmethod
    def _encode_path(path: str) -> str:
        return "/".join(quote(part, safe="") for part in path.split("/"))
