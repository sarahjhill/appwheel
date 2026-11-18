"""Makes a tidy PDF of the care diary between two dates, ready to send to someone."""
import io
from datetime import date

from django.utils.html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import DiaryEntry

HEADINGS = ['Date', 'Carer on time', 'Kindness and respect', 'Medication', 'Food, washing, dressing', 'Overall', 'Notes']
CONCERN_RED = colors.HexColor('#b91c1c')


def diary_pdf(user, entries, start, end):
    """Return the PDF as bytes."""
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
        title=f'Care diary {start:%d %b %Y} to {end:%d %b %Y}', author=user.email,
    )
    styles = getSampleStyleSheet()
    small = ParagraphStyle('small', parent=styles['BodyText'], fontSize=9, leading=12)
    bold = ParagraphStyle('bold', parent=small, fontName='Helvetica-Bold')
    concern = ParagraphStyle('concern', parent=bold, textColor=CONCERN_RED)

    story = [
        Paragraph('Care diary', styles['Title']),
        Paragraph(
            f'Kept by {escape(user.get_full_name() or user.email)} · '
            f'{start.day} {start:%B %Y} to {end.day} {end:%B %Y} · '
            f'{len(entries)} day{"s" if len(entries) != 1 else ""} recorded',
            styles['BodyText'],
        ),
        Spacer(1, 6 * mm),
    ]

    if not entries:
        story.append(Paragraph('No diary entries between these dates.', styles['BodyText']))
    else:
        rows = [[Paragraph(heading, bold) for heading in HEADINGS]]
        for entry in sorted(entries, key=lambda entry: entry.date):
            cells = [Paragraph(f'{entry.date:%a} {entry.date.day} {entry.date:%b %Y}', bold)]
            for field, _ in DiaryEntry.QUESTIONS:
                value = getattr(entry, field)
                label = getattr(entry, f'get_{field}_display')() or '–'
                cells.append(Paragraph(label, concern if value == 'no' else small))
            rating = entry.get_rating_display() or '–'
            cells.append(Paragraph(rating, concern if entry.rating == 'poor' else small))
            cells.append(Paragraph(escape(entry.notes).replace('\n', '<br/>') or '–', small))
            rows.append(cells)

        widths = [34 * mm, 24 * mm, 26 * mm, 24 * mm, 30 * mm, 20 * mm, None]
        table = Table(rows, colWidths=widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ede9fe')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#a1a1aa')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(table)

        concerns = sum(1 for entry in entries if entry.has_concern)
        story += [
            Spacer(1, 5 * mm),
            Paragraph(
                f'Days with a concern (any "No" or "Poor", shown in red): {concerns}', styles['BodyText'],
            ),
        ]

    story += [
        Spacer(1, 4 * mm),
        Paragraph(
            f'Written by the person receiving care, using AppWheel. Created on {date.today():%d %B %Y}.',
            small,
        ),
    ]
    document.build(story)
    return buffer.getvalue()
