"""In-memory BM25 index with optional allow-list filtering."""

import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(text)]


class BM25Index:
    def __init__(self) -> None:
        self.index: BM25Okapi | None = None
        self.chunk_ids: list[str] = []
        self.chunk_texts: list[str] = []
        self.chunk_metadata: list[dict] = []
        self._id_to_pos: dict[str, int] = {}

    def build(self, chunks: list[dict]) -> None:
        self.chunk_ids = [c["chunk_id"] for c in chunks]
        self.chunk_texts = [c["text"] for c in chunks]
        self.chunk_metadata = [dict(c) for c in chunks]
        self._id_to_pos = {cid: i for i, cid in enumerate(self.chunk_ids)}
        tokenized = [_tokenize(t) for t in self.chunk_texts]
        self.index = BM25Okapi(tokenized) if tokenized else None

    def is_ready(self) -> bool:
        return self.index is not None and len(self.chunk_ids) > 0

    def search(
        self,
        query: str,
        top_k: int = 10,
        allowed_chunk_ids: set[str] | None = None,
    ) -> list[dict]:
        if not self.is_ready():
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = self.index.get_scores(tokens)

        indices: list[int]
        if allowed_chunk_ids is not None:
            indices = [
                self._id_to_pos[cid]
                for cid in allowed_chunk_ids
                if cid in self._id_to_pos
            ]
        else:
            indices = list(range(len(self.chunk_ids)))

        scored = [(i, float(scores[i])) for i in indices if scores[i] > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        scored = scored[:top_k]

        results: list[dict] = []
        for i, score in scored:
            entry = dict(self.chunk_metadata[i])
            entry["score"] = score
            results.append(entry)
        return results

    # ---------- persistence ----------

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("wb") as fh:
            pickle.dump(
                {
                    "index": self.index,
                    "chunk_ids": self.chunk_ids,
                    "chunk_texts": self.chunk_texts,
                    "chunk_metadata": self.chunk_metadata,
                },
                fh,
            )

    def load(self, path: str | Path) -> bool:
        p = Path(path)
        if not p.exists():
            return False
        with p.open("rb") as fh:
            data = pickle.load(fh)
        self.index = data["index"]
        self.chunk_ids = data["chunk_ids"]
        self.chunk_texts = data["chunk_texts"]
        self.chunk_metadata = data["chunk_metadata"]
        self._id_to_pos = {cid: i for i, cid in enumerate(self.chunk_ids)}
        return True
