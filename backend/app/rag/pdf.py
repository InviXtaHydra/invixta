"""PDF text extraction with pypdf."""

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.exceptions import BadRequestError


def extract_pages(data: bytes, max_pages: int) -> list[str]:
    """Return the raw text of every page. Raises BadRequestError for broken, encrypted or huge PDFs."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise BadRequestError("Encrypted PDFs aren't supported")
        if len(reader.pages) > max_pages:
            raise BadRequestError(f"The PDF has {len(reader.pages)} pages; the limit is {max_pages}")
        return [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as exc:
        raise BadRequestError("The file is not a readable PDF") from exc
