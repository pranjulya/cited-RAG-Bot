from __future__ import annotations

from io import BytesIO

from pypdf import PdfWriter


def make_text_pdf(pages: list[str]) -> bytes:
    """Minimal PDF 1.4 with one Helvetica text stream per page."""
    if not pages:
        pages = [""]

    catalog_id = 1
    pages_id = 2
    font_id = 3
    bodies: dict[int, bytes] = {
        font_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    page_ids: list[int] = []
    next_id = 4
    for text in pages:
        page_id = next_id
        content_id = next_id + 1
        next_id += 2
        page_ids.append(page_id)
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1", errors="replace")
        bodies[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream"
        )
        bodies[page_id] = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        ).encode("ascii")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    bodies[pages_id] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
    bodies[catalog_id] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")

    max_id = max(bodies)
    buf = bytearray(b"%PDF-1.4\n")
    offsets = {0: 0}
    for obj_id in range(1, max_id + 1):
        offsets[obj_id] = len(buf)
        buf.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        buf.extend(bodies[obj_id])
        buf.extend(b"\nendobj\n")
    xref_start = len(buf)
    buf.extend(f"xref\n0 {max_id + 1}\n".encode("ascii"))
    buf.extend(b"0000000000 65535 f \n")
    for obj_id in range(1, max_id + 1):
        buf.extend(f"{offsets[obj_id]:010d} 00000 n \n".encode("ascii"))
    buf.extend(
        (
            f"trailer << /Size {max_id + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(buf)


def make_blank_pdf() -> bytes:
    return make_text_pdf([""])


def make_password_pdf(password: str = "secret") -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt(password)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


CORRUPT_PDF = b"%PDF-1.4\n1 0 obj<< /Type /Catalog >>endobj\ntrailer<<>>\n%%EOF\n"
TWO_PAGE_PDF = make_text_pdf(["alpha-page-one", "beta-page-two"])
