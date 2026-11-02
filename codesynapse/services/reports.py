import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def build_pdf(stats):
    """Returns the career report as PDF bytes."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "CodeSynapse: Career Report")
    y = 700
    for p in stats:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, f"Platform: {p['platform']}")
        y -= 20
        c.setFont("Helvetica", 12)
        for k, v in p['stats'].items():
            c.drawString(120, y, f"- {k}: {v}")
            y -= 15
        y -= 15
    c.save()
    return buffer.getvalue()
