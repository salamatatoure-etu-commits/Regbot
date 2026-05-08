import io
import logging
from sqlalchemy.orm import Session

from rag.chunks import cached_sent_tokenize, token_length, clean_text
from rag.embedder import embed_text
from rag.vectorizer import store_chunks, store_embedding
from rag.document_processing_utils import deduplicate_chunks

logger = logging.getLogger("uvicorn")

CHUNK_SIZE = 400
OVERLAP    = 50


# ------------------------------------------------------------------ #
# EXTRACTION DE TEXTE                                                  #
# ------------------------------------------------------------------ #

def _extract_pdf_pymupdf(content_bytes: bytes) -> list[tuple[int, str]]:
    """Extraction via PyMuPDF avec fallback OCR Tesseract si page vide."""
    import fitz
    pages = []
    doc = fitz.open(stream=content_bytes, filetype="pdf")

    for i, page in enumerate(doc):
        text = page.get_text().strip()

        # Fallback OCR si la page ne contient pas de texte extractible
        if len(text) < 50:
            try:
                import pytesseract
                from PIL import Image
                pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(img, lang="fra+eng")
            except Exception as e:
                logger.warning(f"OCR page {i+1} échoué : {e}")

        text = clean_text(text)
        if text.strip():
            pages.append((i + 1, text))

    doc.close()
    return pages


def _extract_pdf(content_bytes: bytes) -> list[tuple[int, str]]:
    """Essaie PyMuPDF d'abord, repli sur pypdf."""
    try:
        return _extract_pdf_pymupdf(content_bytes)
    except Exception as e:
        logger.warning(f"PyMuPDF échoué, repli pypdf : {e}")
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content_bytes))
        pages = []
        for i, page in enumerate(reader.pages):
            text = clean_text(page.extract_text() or "")
            if text.strip():
                pages.append((i + 1, text))
        return pages


def _extract_txt(content_bytes: bytes) -> list[tuple[int, str]]:
    text = clean_text(content_bytes.decode("utf-8", errors="replace"))
    return [(1, text)] if text.strip() else []


def _extract_docx(content_bytes: bytes) -> list[tuple[int, str]]:
    from docx import Document as DocxDocument
    doc = DocxDocument(io.BytesIO(content_bytes))
    parts: list[str] = []

    for para in doc.paragraphs:
        t = clean_text(para.text)
        if t.strip():
            parts.append(t)

    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(
                clean_text(cell.text) for cell in row.cells if cell.text.strip()
            )
            if row_text.strip():
                parts.append(row_text)

    return [(1, " ".join(parts))] if parts else []


def _extract_xlsx(content_bytes: bytes) -> list[tuple[int, str]]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content_bytes), read_only=True, data_only=True)
    pages: list[tuple[int, str]] = []

    for sheet_num, sheet in enumerate(wb.worksheets, start=1):
        rows: list[str] = []
        for row in sheet.iter_rows(values_only=True):
            row_text = " | ".join(str(c) for c in row if c is not None and str(c).strip())
            if row_text.strip():
                rows.append(row_text)
        text = clean_text("\n".join(rows))
        if text.strip():
            pages.append((sheet_num, text))

    wb.close()
    return pages


def _extract_html(content_bytes: bytes) -> list[tuple[int, str]]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(content_bytes.decode("utf-8", errors="replace"), "html.parser")
    for tag in soup(["script", "style", "head", "meta", "link", "noscript"]):
        tag.decompose()
    text = clean_text(soup.get_text(separator=" ", strip=True))
    return [(1, text)] if text.strip() else []


_MIME_EXTRACTORS = {
    "application/pdf": _extract_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": _extract_docx,
    "application/msword": _extract_docx,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": _extract_xlsx,
    "application/vnd.ms-excel": _extract_xlsx,
    "text/html": _extract_html,
}


def extract_pages(content_bytes: bytes, mime_type: str) -> list[tuple[int, str]]:
    extractor = _MIME_EXTRACTORS.get(mime_type)
    if extractor:
        return extractor(content_bytes)
    return _extract_txt(content_bytes)


# ------------------------------------------------------------------ #
# CHUNKING                                                             #
# ------------------------------------------------------------------ #

def _chunk_text(page_num: int, text: str) -> list[tuple[int, str]]:
    sentences = cached_sent_tokenize(text)
    chunks: list[tuple[int, str]] = []
    current_sents: list[str] = []
    current_tokens = 0

    for sent in sentences:
        sent_tokens = token_length(sent)
        if current_tokens + sent_tokens > CHUNK_SIZE and current_sents:
            chunks.append((page_num, " ".join(current_sents).strip()))
            overlap_sents: list[str] = []
            overlap_tokens = 0
            for s in reversed(current_sents):
                t = token_length(s)
                if overlap_tokens + t <= OVERLAP:
                    overlap_sents.insert(0, s)
                    overlap_tokens += t
                else:
                    break
            current_sents = overlap_sents
            current_tokens = overlap_tokens
        current_sents.append(sent)
        current_tokens += sent_tokens

    if current_sents:
        chunks.append((page_num, " ".join(current_sents).strip()))
    return chunks


def build_chunks(pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
    all_chunks = []
    for page_num, text in pages:
        all_chunks.extend(_chunk_text(page_num, text))
    return all_chunks


# ------------------------------------------------------------------ #
# PIPELINE COMPLET                                                     #
# ------------------------------------------------------------------ #

def index_document(db: Session, document_id: str, content_bytes: bytes, mime_type: str) -> int:
    pages = extract_pages(content_bytes, mime_type)
    if not pages:
        logger.warning(f"Document {document_id} : aucun texte extrait.")
        return 0

    chunks = build_chunks(pages)
    if not chunks:
        logger.warning(f"Document {document_id} : aucun chunk généré.")
        return 0

    texts = [c[1] for c in chunks]
    embeddings = [embed_text(t) for t in texts]
    chunks, embeddings = deduplicate_chunks(chunks, embeddings)

    chunk_ids = store_chunks(db, document_id, chunks)
    for chunk_id, embedding in zip(chunk_ids, embeddings):
        store_embedding(db, chunk_id, embedding)

    logger.info(f"Document {document_id} : {len(chunk_ids)} chunks indexés.")
    return len(chunk_ids)
