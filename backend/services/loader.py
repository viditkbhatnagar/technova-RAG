"""PDF text extraction."""

import re
from pathlib import Path

from pypdf import PdfReader


_WHITESPACE_RE = re.compile(r"[ \t]+")
_NEWLINES_RE = re.compile(r"\n{3,}")


class IngestionError(Exception):
    pass


def _clean(text: str) -> str:
    text = _WHITESPACE_RE.sub(" ", text)
    text = _NEWLINES_RE.sub("\n\n", text)
    return text.strip()


def load_pdf(file_path: str | Path) -> list[dict]:
    """Extract text from a PDF, page by page.

    Returns a list of {"page_number": int (1-indexed), "text": str}.
    Pages with no extractable text (e.g. scanned images) are skipped.
    """
    path = Path(file_path)
    if not path.exists():
        raise IngestionError(f"PDF not found: {path}")

    reader = PdfReader(str(path))
    pages: list[dict] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception:
            raw = ""
        text = _clean(raw)
        if not text:
            continue
        pages.append({"page_number": i, "text": text})
    return pages


def list_pdfs(docs_dir: str | Path) -> list[Path]:
    """Return sorted list of PDFs in a directory."""
    directory = Path(docs_dir)
    if not directory.exists():
        raise IngestionError(f"Docs directory not found: {directory}")
    return sorted(directory.glob("*.pdf"))
