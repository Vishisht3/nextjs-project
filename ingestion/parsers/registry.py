"""
ingestion/parsers/registry.py
Registry mapping file extensions to document parsers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Type

from ingestion.parsers.base import BaseParser, ParsedDocument, UnsupportedFormatError


class PlainTextParser(BaseParser):
    def parse(self, path: Path) -> ParsedDocument:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return ParsedDocument(
            text=content,
            source=path.name,
            metadata={"filepath": str(path), "extension": path.suffix},
        )


class MarkdownParser(BaseParser):
    def parse(self, path: Path) -> ParsedDocument:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return ParsedDocument(
            text=content,
            source=path.name,
            metadata={"filepath": str(path), "extension": path.suffix, "format": "markdown"},
        )


class JsonParser(BaseParser):
    def parse(self, path: Path) -> ParsedDocument:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, dict):
            text = data.get("text") or data.get("content") or json.dumps(data, indent=2)
            meta = {k: v for k, v in data.items() if k not in {"text", "content"}}
        elif isinstance(data, list):
            text = "\n\n".join(str(item) for item in data)
            meta = {"items_count": len(data)}
        else:
            text = str(data)
            meta = {}
        return ParsedDocument(
            text=text,
            source=path.name,
            metadata={"filepath": str(path), "extension": path.suffix, **meta},
        )


class PdfParser(BaseParser):
    def parse(self, path: Path) -> ParsedDocument:
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            full_text = "\n\n".join(pages)
            return ParsedDocument(
                text=full_text,
                source=path.name,
                metadata={"filepath": str(path), "pages": len(reader.pages)},
            )
        except ImportError:
            # Fallback if pypdf is not installed
            with open(path, "rb") as f:
                raw = f.read().decode("latin1", errors="ignore")
            return ParsedDocument(
                text=raw,
                source=path.name,
                metadata={"filepath": str(path), "note": "pypdf not installed, raw read"},
            )


PARSER_REGISTRY: Dict[str, Type[BaseParser]] = {
    ".txt": PlainTextParser,
    ".md": MarkdownParser,
    ".markdown": MarkdownParser,
    ".json": JsonParser,
    ".csv": PlainTextParser,
    ".pdf": PdfParser,
    ".py": PlainTextParser,
    ".yaml": PlainTextParser,
    ".yml": PlainTextParser,
}


def get_parser_for(path: Path, keep_math: bool = False) -> BaseParser:
    ext = path.suffix.lower()
    parser_cls = PARSER_REGISTRY.get(ext)
    if parser_cls is None:
        raise UnsupportedFormatError(f"Unsupported file format '{ext}' for file: {path}")
    return parser_cls(keep_math=keep_math)
