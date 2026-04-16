"""Image ingestion and preprocessing utilities for accessibility audits."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Iterable, List, Optional, Sequence
from uuid import uuid4

from pydantic import BaseModel, Field
from PIL import Image, ImageOps, UnidentifiedImageError


class PreparedImage(BaseModel):
    """Metadata for a normalized image saved on disk."""

    image_id: str = Field(...)
    original_name: str = Field(...)
    stored_path: str = Field(...)
    stop_id: Optional[str] = Field(default=None)
    width: int = Field(...)
    height: int = Field(...)
    format: str = Field(default="unknown")
    size_bytes: int = Field(default=0)


class ImageProcessor:
    """Validate and normalize accessibility images before inference."""

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    def __init__(self, max_dimension: int = 1280):
        self.max_dimension = max_dimension

    @staticmethod
    def _safe_suffix(filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        return suffix if suffix in ImageProcessor.ALLOWED_EXTENSIONS else ".jpg"

    @staticmethod
    def _extract_stop_id(filename: str) -> Optional[str]:
        stem = Path(filename).stem
        if "_" in stem:
            candidate = stem.split("_", 1)[0].strip()
            return candidate or None
        return None

    def prepare_bytes(
        self,
        file_name: str,
        content: bytes,
        destination_dir: Path,
        stop_id: Optional[str] = None,
    ) -> PreparedImage:
        destination_dir.mkdir(parents=True, exist_ok=True)

        if not content:
            raise ValueError(f"Empty image upload: {file_name}")

        image_id = f"IMG_{uuid4().hex[:12]}"
        stop_id = stop_id or self._extract_stop_id(file_name)
        output_path = destination_dir / f"{image_id}.jpg"

        try:
            with Image.open(io.BytesIO(content)) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((self.max_dimension, self.max_dimension))
                image.save(output_path, format="JPEG", quality=90)
                return PreparedImage(
                    image_id=image_id,
                    original_name=file_name,
                    stored_path=str(output_path),
                    stop_id=stop_id,
                    width=image.width,
                    height=image.height,
                    format=image.format or "JPEG",
                    size_bytes=os.path.getsize(output_path),
                )
        except UnidentifiedImageError as exc:
            raise ValueError(f"Unsupported image file: {file_name}") from exc

    async def prepare_uploads(
        self,
        upload_files: Sequence,
        destination_dir: Path,
        stop_ids: Optional[Sequence[Optional[str]]] = None,
    ) -> List[PreparedImage]:
        prepared: List[PreparedImage] = []
        stop_id_list = list(stop_ids) if stop_ids is not None else []

        for index, upload_file in enumerate(upload_files):
            content = await upload_file.read()
            explicit_stop_id = stop_id_list[index] if index < len(stop_id_list) else None
            prepared.append(
                self.prepare_bytes(
                    file_name=upload_file.filename or f"image_{index}.jpg",
                    content=content,
                    destination_dir=destination_dir,
                    stop_id=explicit_stop_id,
                )
            )

        return prepared
