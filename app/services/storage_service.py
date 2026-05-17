from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequestError


@dataclass(frozen=True)
class UploadedStorageObject:
    path: str
    public_url: str
    content_type: str
    size_bytes: int


class SupabaseStorageService:
    allowed_image_content_types = {"image/jpeg", "image/png", "image/webp"}
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
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
        content_type = file.content_type or ""
        extension = Path(file.filename or "").suffix.lower()

        if content_type not in self.allowed_image_content_types:
            raise BadRequestError("Only JPEG, PNG, and WEBP images are allowed")
        if extension not in self.allowed_extensions:
            raise BadRequestError("Only .jpg, .jpeg, .png, and .webp files are allowed")

        file_bytes = await file.read()
        size = len(file_bytes)
        if size == 0:
            raise BadRequestError("Uploaded file is empty")
        if size > self.max_image_size_bytes:
            raise BadRequestError("Image size must not exceed 5 MB")

        encoded_path = self._encode_path(path)
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{encoded_path}"
        headers = {
            **self.headers,
            "Content-Type": content_type,
            "Cache-Control": "3600",
            "x-upsert": "false",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, content=file_bytes)

        if response.status_code not in {200, 201}:
            raise BadRequestError("Supabase Storage upload failed", details=response.text)

        return UploadedStorageObject(
            path=path,
            public_url=self.get_public_url(path),
            content_type=content_type,
            size_bytes=size,
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

    @staticmethod
    def _encode_path(path: str) -> str:
        return "/".join(quote(part, safe="") for part in path.split("/"))
