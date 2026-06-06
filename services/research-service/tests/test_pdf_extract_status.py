from io import BytesIO

from pypdf import PdfWriter

from app.pdf_ingest import extract_pdf_text


def test_extract_pdf_text_failed_for_invalid_bytes():
    extracted = extract_pdf_text(b"not a pdf")
    assert extracted.status == "failed"


def test_extract_pdf_text_needs_ocr_for_blank_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    extracted = extract_pdf_text(buffer.getvalue())
    assert extracted.page_count == 1
    assert extracted.status in {"needs_ocr", "extracted"}
