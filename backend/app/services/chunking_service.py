import hashlib
from typing import List, Dict


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = "\n".join(line for line in text.split("\n") if line.strip())
    return text.strip()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def estimate_token_count(text: str) -> int:
    # lightweight approximation for now
    return max(1, len(text.split()))


def chunk_text(
    text: str,
    chunk_size_words: int = 200,
    overlap_words: int = 40
) -> List[Dict]:
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = min(start + chunk_size_words, len(words))
        chunk_words = words[start:end]
        chunk_text_value = " ".join(chunk_words).strip()

        if chunk_text_value:
            chunks.append({
                "chunk_index": chunk_index,
                "chunk_text": chunk_text_value,
                "chunk_hash": hash_text(chunk_text_value),
                "token_count": estimate_token_count(chunk_text_value),
            })

        if end == len(words):
            break

        start = max(0, end - overlap_words)
        chunk_index += 1

    return chunks