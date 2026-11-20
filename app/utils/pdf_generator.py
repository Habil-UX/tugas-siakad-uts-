from datetime import datetime
from io import BytesIO
import os
from xml.sax.saxutils import escape


def render_transcript_html(data: dict) -> str:
    """
    Merender template HTML Transkrip Akademik (app/templates/transcript.html)
    lengkap dengan tampilan historis per semester dan predikat kelulusan di footer.
    """
    tpl_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "templates",
        "transcript.html",
    )
    if os.path.exists(tpl_path):
        with open(tpl_path, "r", encoding="utf-8") as f:
            html = f.read()
    else:
        html = "<html><body><h1>TRANSKRIP AKADEMIK</h1>{ROWS_HTML}<footer>Predikat Kelulusan: {{ predikat }}</footer></body></html>"

    records = sorted(
        data.get("records", []),
        key=lambda item: (item.get("semester", 1), item.get("kode_mk", "")),
    )
    rows = []
    for item in records:
        sks_val = float(item.get("sks", 0))
        bobot_val = float(item.get("bobot", 0))
        mutu_val = float(item.get("mutu", sks_val * bobot_val))
        rows.append(
            f"<tr>"
            f"<td>{escape(str(item.get('semester', '-')))}</td>"
            f"<td>{escape(str(item.get('kode_mk', '-')))}</td>"
            f"<td>{escape(str(item.get('nama_mk', '-')))}</td>"
            f"<td>{escape(str(item.get('sks', '-')))}</td>"
            f"<td>{escape(str(item.get('nilai_huruf', '-')))}</td>"
            f"<td>{bobot_val:.2f}</td>"
            f"<td>{mutu_val:.2f}</td>"
            f"<td>{escape(str(item.get('status', 'LULUS')))}</td>"
            f"</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan='8'>Belum ada data nilai</td></tr>")

    nim_val = str(data.get("nim", "-"))
    angkatan_val = str(
        data.get("angkatan")
        or (nim_val[:4] if len(nim_val) >= 4 and nim_val[:4].isdigit() else "2025")
    )

    replacements = {
        "{{ nama }}": escape(str(data.get("nama", "-"))),
        "{{ nim }}": escape(nim_val),
        "{{ program_studi }}": escape(str(data.get("program_studi") or "-")),
        "{{ angkatan }}": escape(angkatan_val),
        "{{ total_sks_lulus }}": str(data.get("total_sks_lulus", 0)),
        "{{ total_sks }}": str(data.get("total_sks", 0)),
        "{{ ipk }}": f"{float(data.get('ipk', 0)):.2f}",
        "{{ predikat }}": escape(str(data.get("predikat", "-"))),
        "{{ fakultas }}": escape(str(data.get("fakultas") or "Fakultas Ilmu Komputer")),
        "{ROWS_HTML}": "\n".join(rows),
    }
    for k, v in replacements.items():
        html = html.replace(k, v)
    return html

from reportlab.graphics.shapes import Circle, Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _build_university_logo() -> Drawing:
    drawing = Drawing(22 * mm, 22 * mm)
    drawing.add(
        Circle(
            11 * mm,
            11 * mm,
            10 * mm,
            fillColor=colors.HexColor("#263B5E"),
            strokeColor=colors.HexColor("#D4AF37"),
            strokeWidth=2,
        )
    )
    drawing.add(
        Circle(
            11 * mm,
            11 * mm,
            7.5 * mm,
            fillColor=colors.HexColor("#1E2F4D"),
            strokeColor=colors.white,
            strokeWidth=0.8,
        )
    )
    drawing.add(
        String(
            11 * mm,
            9.5 * mm,
            "SIAKAD",
            fontName="Helvetica-Bold",
            fontSize=8,
            fillColor=colors.white,
            textAnchor="middle",
        )
    )
    return drawing


def generate_transcript_pdf(data: dict) -> bytes:
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TranscriptTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#263B5E"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "TranscriptSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        leading=14,
        spaceAfter=10,
    )

    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=colors.HexColor("#263B5E"),
        spaceBefore=10,
        spaceAfter=6,
    )

    normal_style = styles["Normal"]

    small_style = ParagraphStyle(
        "SmallText",
        parent=normal_style,
        fontSize=8,
        leading=11,
    )

    story = []

    # ==================================
    # HEADER DENGAN LOGO UNIVERSITAS
    # ==================================
    logo = _build_university_logo()
    header_center = [
        Paragraph("UNIVERSITAS NUSANTARA TEKNOLOGI", subtitle_style),
        Paragraph("TRANSKRIP AKADEMIK", title_style),
        Paragraph("SISTEM INFORMASI AKADEMIK RESMI", subtitle_style),
    ]
    header_table = Table(
        [[logo, header_center, ""]],
        colWidths=[30 * mm, 207 * mm, 30 * mm],
    )
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("LINEBELOW", (0, 0), (-1, 0), 1.2, colors.HexColor("#263B5E")),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 8))

    # ==================================
    # BIODATA MAHASISWA (NIM, Nama, Prodi, Angkatan)
    # ==================================
    nim_val = str(data.get("nim", "-"))
    angkatan_val = str(
        data.get("angkatan")
        or (nim_val[:4] if len(nim_val) >= 4 and nim_val[:4].isdigit() else "2025")
    )

    identity_data = [
        [
            Paragraph("<b>Nama Mahasiswa</b>", normal_style),
            escape(str(data.get("nama", "-"))),
            Paragraph("<b>NIM</b>", normal_style),
            escape(nim_val),
        ],
        [
            Paragraph("<b>Program Studi</b>", normal_style),
            escape(str(data.get("program_studi") or "-")),
            Paragraph("<b>Angkatan</b>", normal_style),
            escape(angkatan_val),
        ],
    ]

    identity_table = Table(
        identity_data,
        colWidths=[35 * mm, 100 * mm, 35 * mm, 97 * mm],
    )

    identity_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EDF5")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E8EDF5")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(identity_table)
    story.append(Spacer(1, 10))

    # ==================================
    # TABEL NILAI PER SEMESTER [Kode MK | Nama MK | SKS | Nilai | Mutu]
    # ==================================
    story.append(
        Paragraph(
            "DAFTAR NILAI MATA KULIAH PER SEMESTER",
            section_style,
        )
    )

    table_data = [[
        "Semester",
        "Kode MK",
        "Nama MK",
        "SKS",
        "Nilai",
        "Bobot",
        "Mutu",
        "Status",
    ]]

    records = sorted(
        data.get("records", []),
        key=lambda item: (
            item.get("semester", 1),
            item.get("kode_mk", ""),
        ),
    )

    for item in records:
        sks_val = float(item.get("sks", 0))
        bobot_val = float(item.get("bobot", 0))
        mutu_val = float(item.get("mutu", sks_val * bobot_val))
        table_data.append([
            str(item.get("semester", "-")),
            escape(str(item.get("kode_mk", "-"))),
            Paragraph(
                escape(str(item.get("nama_mk", "-"))),
                small_style,
            ),
            str(item.get("sks", "-")),
            str(item.get("nilai_huruf", "-")),
            f"{bobot_val:.2f}",
            f"{mutu_val:.2f}",
            str(item.get("status", "LULUS")),
        ])

    if len(table_data) == 1:
        table_data.append([
            "-",
            "-",
            "Belum ada data nilai",
            "-",
            "-",
            "-",
            "-",
            "-",
        ])

    grade_table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            22 * mm,
            28 * mm,
            95 * mm,
            18 * mm,
            20 * mm,
            24 * mm,
            25 * mm,
            35 * mm,
        ],
    )

    grade_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263B5E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#F0F3F8")],
            ),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(grade_table)
    story.append(Spacer(1, 12))

    # ==================================
    # REKAP IPS PER SEMESTER
    # ==================================
    story.append(
        Paragraph(
            "REKAPITULASI INDEKS PRESTASI SEMESTER (IPS)",
            section_style,
        )
    )

    semester_data = [[
        "Semester",
        "IPS",
        "Total SKS",
        "SKS Lulus",
        "Total Mutu",
    ]]

    for item in data.get("rekap_semester", []):
        semester_data.append([
            str(item["semester"]),
            f"{float(item['ips']):.2f}",
            str(item["total_sks"]),
            str(item["total_sks_lulus"]),
            f"{float(item['total_mutu']):.2f}",
        ])

    if len(semester_data) == 1:
        semester_data.append([
            "-", "-", "-", "-", "-"
        ])

    semester_table = Table(
        semester_data,
        repeatRows=1,
        colWidths=[
            45 * mm,
            45 * mm,
            55 * mm,
            55 * mm,
            67 * mm,
        ],
    )

    semester_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263B5E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#F0F3F8")],
            ),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(semester_table)
    story.append(Spacer(1, 12))

    # ==================================
    # RINGKASAN AKADEMIK (Total SKS, IPK, Predikat Kelulusan)
    # ==================================
    summary_data = [
        [
            "TOTAL SKS",
            "TOTAL SKS LULUS",
            "IPK KUMULATIF",
            "PREDIKAT KELULUSAN",
        ],
        [
            str(data.get("total_sks", 0)),
            str(data.get("total_sks_lulus", 0)),
            f"{float(data.get('ipk', 0)):.2f}",
            escape(str(data.get("predikat", "-"))),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[66 * mm, 66 * mm, 67 * mm, 68 * mm],
    )

    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263B5E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E8EDF5")),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )

    story.append(summary_table)
    story.append(Spacer(1, 20))

    # ==================================
    # FOOTER & AREA TANDA TANGAN DEKAN
    # ==================================
    printed_date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    fakultas_name = escape(
        str(data.get("fakultas") or "Fakultas Ilmu Komputer")
    )

    signature_content = [
        Paragraph(
            f"Dicetak pada: {printed_date}",
            small_style,
        ),
        Spacer(1, 10),
        Paragraph(
            f"<b>Dekan {fakultas_name},</b>",
            small_style,
        ),
        Spacer(1, 38),
        Paragraph(
            "<b>(________________________)</b>",
            small_style,
        ),
        Paragraph(
            "NIP / NIDN Dekan",
            small_style,
        ),
    ]

    story.append(
        Table(
            [["", signature_content]],
            colWidths=[150 * mm, 117 * mm],
            style=TableStyle([
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]),
        )
    )

    document.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
