import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from apps.results.models import ExaminationResult


def generate_scorecard_pdf(result: ExaminationResult) -> bytes:
    """
    Renders an authoritative, cryptographically stamped institutional PDF scorecard.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    header_style = ParagraphStyle(
        "InstHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        alignment=1, # Center
    )
    sub_header = ParagraphStyle(
        "InstSubHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#3b82f6"),
        alignment=1,
    )
    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
    )
    val_style = ParagraphStyle(
        "ValStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
    )
    hash_style = ParagraphStyle(
        "HashStyle",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0369a1"),
        alignment=1,
    )

    story = []

    # 1. Institution Header Banner
    story.append(Paragraph("EPS PHOENIX INSTITUTIONAL ACADEMY", header_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("OFFICIAL VERIFIED EXAMINATION SCORECARD", sub_header))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=15))

    # 2. Candidate & Academic Context
    student = result.student
    roll_num = student.student_profile.roll_number if hasattr(student, "student_profile") else "PENDING"
    cohort = result.examination.batch.name
    subject_title = f"{result.examination.subject.code} — {result.examination.subject.name}"

    candidate_data = [
        [
            Paragraph("Candidate Full Name:", label_style),
            Paragraph(student.get_full_name() or student.username, val_style),
            Paragraph("Official Roll Number:", label_style),
            Paragraph(roll_num, val_style),
        ],
        [
            Paragraph("Degree Course / Batch:", label_style),
            Paragraph(cohort, val_style),
            Paragraph("Examination Code:", label_style),
            Paragraph(result.examination.code, val_style),
        ],
        [
            Paragraph("Academic Subject:", label_style),
            Paragraph(subject_title, val_style),
            Paragraph("Publication Date:", label_style),
            Paragraph(result.published_at.strftime("%B %d, %Y"), val_style),
        ],
    ]

    cand_table = Table(candidate_data, colWidths=[130, 160, 120, 120])
    cand_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(cand_table)
    story.append(Spacer(1, 20))

    # 3. Assessment Performance Breakdown Table
    verdict_color = "#16a34a" if result.is_passed else "#dc2626"
    verdict_text = "PASS" if result.is_passed else "FAIL"

    perf_headers = [
        Paragraph("Maximum Marks", label_style),
        Paragraph("Awarded Score", label_style),
        Paragraph("Percentage", label_style),
        Paragraph("Grade Letter", label_style),
        Paragraph("Verdict", label_style),
    ]

    perf_values = [
        Paragraph(f"{result.maximum_score} pts", val_style),
        Paragraph(f"{result.total_score} pts", val_style),
        Paragraph(f"{result.percentage}%", val_style),
        Paragraph(f"<b>{result.grade_letter}</b>", val_style),
        Paragraph(f"<font color='{verdict_color}'><b>{verdict_text}</b></font>", val_style),
    ]

    perf_table = Table([perf_headers, perf_values], colWidths=[105, 105, 105, 105, 110])
    perf_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(perf_table)
    story.append(Spacer(1, 25))

    # 4. Cryptographic Proof & Verification Box
    story.append(Paragraph("DIGITAL CRYPTOGRAPHIC AUTHENTICITY STAMP", label_style))
    story.append(Spacer(1, 4))
    hash_box_content = [
        [Paragraph(f"SHA-256 Certificate Hash: {result.verification_hash}", hash_style)],
        [Paragraph("This transcript is cryptographically sealed by EPS Phoenix Examination Infrastructure.", hash_style)],
    ]
    hash_table = Table(hash_box_content, colWidths=[530])
    hash_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f9ff")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0284c7")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(hash_table)
    story.append(Spacer(1, 30))

    # 5. Signatures Block
    sig_data = [
        [
            Paragraph("____________________________<br/>Registrar / Exam Controller", label_style),
            Paragraph("____________________________<br/>Dean of Academic Affairs", label_style),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[265, 265])
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(sig_table)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
