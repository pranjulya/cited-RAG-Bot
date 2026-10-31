"""Write a small text PDF for console demos: ``samples/acme-hr-policy.pdf``.

The PDF has one policy topic per page so citations point at a clear page.
Run: ``python scripts/make_demo_pdf.py [output_path]``.
"""

from __future__ import annotations

import sys
from pathlib import Path

PAGES: list[list[str]] = [
    [
        "Acme Corp - Employee Handbook - Section 1: Annual Leave",
        "Full-time employees receive 24 days of paid annual leave per calendar year.",
        "Leave accrues monthly at two days per month of service.",
        "Up to five unused days may be carried into the next calendar year.",
    ],
    [
        "Section 2: Remote Work",
        "Remote work is allowed up to three days per week with manager approval.",
        "Employees must be reachable during core hours from 10:00 to 16:00.",
        "Acme provides a one-time home office allowance of 500 USD.",
    ],
    [
        "Section 3: Expenses",
        "Expense claims must be submitted within 30 days with original receipts.",
        "Meals during business travel are reimbursed up to 60 USD per day.",
        "Economy class is required for flights shorter than six hours.",
    ],
    [
        "Section 4: Parental Leave",
        "Primary caregivers receive 16 weeks of fully paid parental leave.",
        "Secondary caregivers receive 4 weeks of fully paid parental leave.",
        "Parental leave must start within 12 months of the birth or adoption.",
    ],
]


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(pages: list[list[str]]) -> bytes:
    """Build a PDF 1.4 file with Helvetica text, one line per string."""
    catalog_id, pages_id, font_id = 1, 2, 3
    bodies: dict[int, bytes] = {
        font_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    page_ids: list[int] = []
    next_id = 4
    for lines in pages:
        page_id, content_id = next_id, next_id + 1
        next_id += 2
        page_ids.append(page_id)
        ops = ["BT", "/F1 12 Tf", "16 TL", "72 720 Td"]
        for line in lines:
            ops.append(f"({_escape(line)}) Tj T*")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1")
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
    offsets: dict[int, int] = {}
    for obj_id in range(1, max_id + 1):
        offsets[obj_id] = len(buf)
        buf.extend(f"{obj_id} 0 obj\n".encode("ascii") + bodies[obj_id] + b"\nendobj\n")
    xref_start = len(buf)
    buf.extend(f"xref\n0 {max_id + 1}\n0000000000 65535 f \n".encode("ascii"))
    for obj_id in range(1, max_id + 1):
        buf.extend(f"{offsets[obj_id]:010d} 00000 n \n".encode("ascii"))
    buf.extend(
        f"trailer << /Size {max_id + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n".encode("ascii")
    )
    return bytes(buf)


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("samples/acme-hr-policy.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(make_pdf(PAGES))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
