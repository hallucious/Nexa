from __future__ import annotations

import hashlib
import re
import zipfile
from dataclasses import dataclass
from html import unescape
from io import BytesIO
from typing import Optional
from xml.etree import ElementTree


@dataclass(frozen=True)
class DocumentTextExtractionResult:
    text: str
    document_type: str
    content_hash: str
    text_preview: str
    extracted_text_char_count: int
    parser_ref: str
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.document_type:
            raise ValueError("DocumentTextExtractionResult.document_type must be non-empty")
        if not self.parser_ref:
            raise ValueError("DocumentTextExtractionResult.parser_ref must be non-empty")
        if self.extracted_text_char_count < 0:
            raise ValueError("DocumentTextExtractionResult.extracted_text_char_count must be >= 0")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\x00", " ")).strip()


def _preview(value: str, *, limit: int = 500) -> str:
    normalized = _normalize_text(value)
    return normalized[:limit]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _decode_pdf_literal(value: str) -> str:
    return (
        value
        .replace(r"\(", "(")
        .replace(r"\)", ")")
        .replace(r"\\", "\\")
        .replace(r"\n", "\n")
        .replace(r"\r", "\r")
        .replace(r"\t", "\t")
    )


def extract_text_from_pdf_bytes(document_bytes: bytes) -> DocumentTextExtractionResult:
    if not document_bytes.startswith(b"%PDF"):
        raise ValueError("file_extraction.parser.pdf_magic_mismatch")
    raw = document_bytes.decode("latin-1", errors="ignore")
    literal_chunks = [_decode_pdf_literal(item) for item in re.findall(r"\(([^()]*)\)\s*(?:Tj|'|\")", raw)]
    if not literal_chunks:
        for array_body in re.findall(r"\[(.*?)\]\s*TJ", raw, flags=re.S):
            literal_chunks.extend(_decode_pdf_literal(item) for item in re.findall(r"\(([^()]*)\)", array_body))
    text = _normalize_text(" ".join(literal_chunks))
    warnings: list[str] = []
    if not text:
        warnings.append("file_extraction.parser.pdf_no_text_chunks")
    return DocumentTextExtractionResult(
        text=text,
        document_type="pdf",
        content_hash=_sha256_text(text),
        text_preview=_preview(text),
        extracted_text_char_count=len(text),
        parser_ref="builtin_pdf_text_minimum_v1",
        warnings=tuple(warnings),
    )


def extract_text_from_docx_bytes(document_bytes: bytes) -> DocumentTextExtractionResult:
    try:
        with zipfile.ZipFile(BytesIO(document_bytes)) as docx:
            xml_bytes = docx.read("word/document.xml")
    except KeyError as exc:
        raise ValueError("file_extraction.parser.docx_document_xml_missing") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError("file_extraction.parser.docx_zip_invalid") from exc

    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as exc:
        raise ValueError("file_extraction.parser.docx_xml_invalid") from exc

    chunks: list[str] = []
    for element in root.iter():
        if element.tag.endswith("}t") or element.tag == "t":
            if element.text:
                chunks.append(element.text)
    text = _normalize_text(unescape(" ".join(chunks)))
    warnings: list[str] = []
    if not text:
        warnings.append("file_extraction.parser.docx_no_text_chunks")
    return DocumentTextExtractionResult(
        text=text,
        document_type="docx",
        content_hash=_sha256_text(text),
        text_preview=_preview(text),
        extracted_text_char_count=len(text),
        parser_ref="builtin_docx_text_minimum_v1",
        warnings=tuple(warnings),
    )


def extract_document_text(
    *,
    document_bytes: bytes,
    document_type: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> DocumentTextExtractionResult:
    normalized_type = str(document_type or "").strip().lower()
    normalized_mime = str(mime_type or "").strip().lower()
    if normalized_type == "pdf" or normalized_mime == "application/pdf":
        return extract_text_from_pdf_bytes(document_bytes)
    if normalized_type == "docx" or normalized_mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx_bytes(document_bytes)
    raise ValueError(f"file_extraction.parser.unsupported_document_type:{normalized_type or normalized_mime or 'unknown'}")
