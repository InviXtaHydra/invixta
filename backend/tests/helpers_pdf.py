"""Build small PDFs inside tests (fpdf2), so tests don't depend on files on disk."""

from fpdf import FPDF


def make_pdf(sections: list[tuple[str, str]], title: str = "Test Document", pages: int = 1) -> bytes:
    pdf = FPDF()
    for page in range(pages):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"{title}" if page == 0 else f"{title} (continued)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, "This document is part of the SupportAI Store knowledge base.", new_x="LMARGIN", new_y="NEXT")
        for heading, body in sections:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, heading, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, body, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def make_blank_pdf() -> bytes:
    """A valid PDF without any text, like a scanned image without OCR."""
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(20, 20, 50, 50)
    return bytes(pdf.output())


RETURNS_PDF_SECTIONS = [
    ("Return window", "You can return most products within 30 days after delivery, without giving a reason."),
    ("Refunds", "We refund the full product price within 5 working days after we receive the return."),
]
SHIPPING_PDF_SECTIONS = [
    ("Delivery times", "Delivery in the Netherlands and Belgium takes 1 to 3 working days after shipping."),
    ("Shipping costs", "Shipping is free for orders of EUR 50 or more."),
]
