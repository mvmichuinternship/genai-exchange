from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ParsedDocument:
    source: str              # file name or identifier
    content: List[str]       # extracted text chunks
    metadata: Dict[str, str] # extra info like file type, author, etc.