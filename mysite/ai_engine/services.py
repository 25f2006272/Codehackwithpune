import hashlib
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from pypdf import PdfReader
from docx import Document as WordDocument

from .models import DocumentExtraction, DocumentChunk
from workspaces.services import record_audit


MAX_CHUNK_CHARS = 2500
CHUNK_OVERLAP = 250

EXTRACTOR_NAME = "document-extractor-v1"

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".md",
    ".csv",
    ".log",
}


# =====================================================
# 1. PDF EXTRACTION
# =====================================================

def extract_pdf(file_object):

    reader = PdfReader(file_object, strict=False)

    if reader.is_encrypted:
        try:
            reader.decrypt("")

        except Exception:
            raise ValueError(
                "Encrypted PDF files are not supported."
            )

    if reader.is_encrypted:
        raise ValueError(
            "PDF requires a password."
        )

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):

        text = page.extract_text() or ""

        if text.strip():

            pages.append({
                "page_number": page_number,
                "text": text,
            })

    return pages


# =====================================================
# 2. DOCX EXTRACTION
# =====================================================

def extract_docx(file_object):

    document = WordDocument(file_object)

    content = []

    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:
            content.append(text)

    # Extract tables too.
    for table in document.tables:

        for row in table.rows:

            cells = [
                cell.text.strip()
                for cell in row.cells
            ]

            row_text = " | ".join(
                cell for cell in cells if cell
            )

            if row_text:
                content.append(row_text)

    full_text = "\n\n".join(content)

    return [{
        "page_number": None,
        "text": full_text,
    }]


# =====================================================
# 3. TXT / MD / CSV EXTRACTION
# =====================================================

def extract_text_file(file_object):

    raw_content = file_object.read()

    encodings = [
        "utf-8-sig",
        "utf-16",
        "cp1252",
    ]

    decoded_text = None

    for encoding in encodings:

        try:

            decoded_text = raw_content.decode(encoding)
            break

        except UnicodeDecodeError:
            continue

    if decoded_text is None:

        raise ValueError(
            "Unable to decode the text file."
        )

    return [{
        "page_number": None,
        "text": decoded_text,
    }]


# =====================================================
# 4. DOCUMENT FORMAT DETECTION
# =====================================================

def extract_document(file_version):

    filename = file_version.original_filename

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:

        raise ValueError(
            f"Unsupported document format: {extension or 'unknown'}"
        )

    with file_version.file.open("rb") as file_object:

        if extension == ".pdf":

            pages = extract_pdf(file_object)

        elif extension == ".docx":

            pages = extract_docx(file_object)

        else:

            pages = extract_text_file(file_object)

    extracted_text = "\n\n".join(
        page["text"]
        for page in pages
    )

    if not extracted_text.strip():

        raise ValueError(
            "No extractable text found in this document. "
            "Scanned PDFs requiring OCR are not supported yet."
        )

    return pages, extracted_text


# =====================================================
# 5. DOCUMENT CHUNKING
# =====================================================

def split_text_into_chunks(text):

    text = text.replace("\r\n", "\n").strip()

    chunks = []

    start = 0

    while start < len(text):

        end = min(
            start + MAX_CHUNK_CHARS,
            len(text)
        )

        if end < len(text):

            minimum_boundary = start + int(
                MAX_CHUNK_CHARS * 0.65
            )

            boundary_candidates = [
                text.rfind("\n", minimum_boundary, end),
                text.rfind(". ", minimum_boundary, end),
                text.rfind(" ", minimum_boundary, end),
            ]

            boundary = max(boundary_candidates)

            if boundary > start:
                end = boundary + 1

        chunk_text = text[start:end].strip()

        if chunk_text:

            chunks.append(chunk_text)

        if end >= len(text):
            break

        next_start = end - CHUNK_OVERLAP

        start = max(
            start + 1,
            next_start
        )

    return chunks


# =====================================================
# 6. BUILD DOCUMENT CHUNKS
# =====================================================

def build_document_chunks(extraction, pages):

    chunk_records = []

    chunk_index = 0

    for page in pages:

        page_text = page["text"]

        page_chunks = split_text_into_chunks(
            page_text
        )

        for content in page_chunks:

            first_line = next(
                (
                    line.strip()
                    for line in content.splitlines()
                    if line.strip()
                ),
                ""
            )

            section_title = (
                first_line[:255]
                if len(first_line) <= 120
                else ""
            )

            chunk_records.append(
                DocumentChunk(
                    extraction=extraction,
                    chunk_index=chunk_index,
                    content=content,
                    page_number=page["page_number"],
                    section_title=section_title,
                    token_count=len(content.split()),
                    metadata={
                        "source_page": page["page_number"],
                        "extractor": EXTRACTOR_NAME,
                    },
                )
            )

            chunk_index += 1

    return chunk_records


# =====================================================
# 7. COMPLETE DOCUMENT EXTRACTION PIPELINE
# =====================================================

def extract_file_version(
    file_version,
    actor,
    force=False,
    request=None,
):

    if file_version.file_size > 50 * 1024 * 1024:

        raise ValidationError(
            "Maximum supported document size is 50 MB."
        )

    latest_extraction = (
        DocumentExtraction.objects.filter(
            file_version=file_version
        )
        .order_by("-extraction_version")
        .first()
    )

    # Reuse an already completed extraction.
    if (
        latest_extraction
        and latest_extraction.status
        == DocumentExtraction.Status.COMPLETED
        and not force
    ):

        return latest_extraction, False

    if (
        latest_extraction
        and latest_extraction.status
        == DocumentExtraction.Status.PROCESSING
    ):

        raise ValidationError(
            "This document is already being processed."
        )

    next_version = (
        latest_extraction.extraction_version + 1
        if latest_extraction
        else 1
    )

    extraction = DocumentExtraction.objects.create(
        file_version=file_version,
        extraction_version=next_version,
        extractor_name=EXTRACTOR_NAME,
        status=DocumentExtraction.Status.PROCESSING,
        created_by=actor,
    )

    try:

        pages, extracted_text = extract_document(
            file_version
        )

        chunks = build_document_chunks(
            extraction,
            pages
        )

        if not chunks:

            raise ValueError(
                "No document chunks could be generated."
            )

        with transaction.atomic():

            DocumentChunk.objects.bulk_create(
                chunks,
                batch_size=500
            )

            extraction.extracted_text = extracted_text

            extraction.status = (
                DocumentExtraction.Status.COMPLETED
            )

            extraction.extracted_at = timezone.now()

            extraction.error_message = ""

            extraction.save(
                update_fields=[
                    "extracted_text",
                    "status",
                    "extracted_at",
                    "error_message",
                    "updated_at",
                ]
            )

            record_audit(
                actor=actor,
                workspace=file_version.file_asset.workspace,
                action="OTHER",
                description=(
                    f"Document extracted: "
                    f"{file_version.original_filename}"
                ),
                object_type="DocumentExtraction",
                object_id=extraction.id,
                metadata={
                    "event": "DOCUMENT_EXTRACTION_COMPLETED",
                    "file_version_id": file_version.id,
                    "extraction_version": next_version,
                    "chunk_count": len(chunks),
                },
                request=request,
            )

        return extraction, True

    except Exception as exc:

        extraction.status = (
            DocumentExtraction.Status.FAILED
        )

        extraction.error_message = (
            f"{type(exc).__name__}: {str(exc)}"
        )[:5000]

        extraction.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )

        raise ValidationError(
            f"Document extraction failed: {str(exc)}"
        ) from exc