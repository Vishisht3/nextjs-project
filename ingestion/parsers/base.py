"""
ingestion/parsers/base.py
Base parser classes and common exceptions for document ingestion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict


class UnsupportedFormatError(Exception):
    """Raised when no parser exists for the given file extension."""
    pass


@dataclass
class ParsedDocument:
    text: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseParser:
    """Base class for all document format parsers."""

    def __init__(self, keep_math: bool = False):
        self.keep_math = keep_math

    def parse(self, path: Path) -> ParsedDocument:
        raise NotImplementedError
