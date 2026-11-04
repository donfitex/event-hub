from pathlib import Path
from uuid import uuid4
from PIL import Image
from django.core.exceptions import ValidationError


def image_path(instance, filename):
    return f"events/{uuid4().hex}{Path(filename).suffix.lower()}"


def validate_image(file):
    if file.size > 5 * 1024 * 1024 or Path(file.name).suffix.lower() not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }:
        raise ValidationError("Upload a JPG, PNG or WebP image under 5 MB.")
    try:
        with Image.open(file) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"} or image.width * image.height > 25000000:
                raise ValueError()
            image.verify()
    except Exception as exc:
        raise ValidationError("Upload a valid image under 25 megapixels.") from exc
    finally:
        file.seek(0)
