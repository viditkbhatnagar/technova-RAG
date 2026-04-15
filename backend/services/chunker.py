"""Text chunking with metadata tagging and SHA-256 deduplication."""

import hashlib

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import DOCUMENT_METADATA, ORG_ID


_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_document(
    pages: list[dict],
    file_name: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[dict]:
    """Split document pages into chunks with full metadata payload.

    Each chunk carries the schema defined in CONVENTIONS.md. Chunks with a
    duplicate content hash are dropped (SHA-256 dedup, first occurrence wins).
    """
    meta = DOCUMENT_METADATA.get(file_name)
    if meta is None:
        raise ValueError(f"No metadata mapping for file: {file_name}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=_SEPARATORS,
        length_function=len,
    )

    raw_chunks: list[tuple[str, int]] = []
    for page in pages:
        page_no = page["page_number"]
        page_text = page["text"]
        if not page_text.strip():
            continue
        splits = splitter.split_text(page_text)
        for piece in splits:
            piece = piece.strip()
            if piece:
                raw_chunks.append((piece, page_no))

    seen_hashes: set[str] = set()
    chunks: list[dict] = []
    total_pre_dedup = len(raw_chunks)

    for idx, (text, page_no) in enumerate(raw_chunks):
        content_hash = _hash(text)
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)

        chunk_index = len(chunks)
        chunk_id = f"{ORG_ID}_{meta['doc_slug']}_c{chunk_index:03d}"
        chunks.append({
            "chunk_id": chunk_id,
            "text": text,
            "doc_name": meta["doc_name"],
            "doc_slug": meta["doc_slug"],
            "file_name": file_name,
            "org_id": ORG_ID,
            "domain": meta["domain"],
            "security_level": meta["security_level"],
            "security_label": meta["security_label"],
            "page_number": page_no,
            "chunk_index": chunk_index,
            "total_chunks": 0,
            "char_count": len(text),
            "content_hash": content_hash,
        })

    total = len(chunks)
    for c in chunks:
        c["total_chunks"] = total

    if total_pre_dedup != total:
        print(f"[chunker] {file_name}: deduped {total_pre_dedup - total} chunks")

    return chunks
