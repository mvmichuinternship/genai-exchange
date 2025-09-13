import re
from typing import List

def clean_text(text: str) -> str:
    """Remove extra whitespace and unwanted characters."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    """Split text into smaller chunks for embeddings."""
    words = text.split()
    return [
        " ".join(words[i:i + chunk_size])
        for i in range(0, len(words), chunk_size)
    ]