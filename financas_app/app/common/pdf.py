from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from financas_app.app.common.money import cents_to_brl


def _header_style() -> ParagraphStyle:
    return ParagraphStyle(
        "Header",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=12,
        fontName="Helvetica-Bold",
    )


def _subheader_style() -> ParagraphStyle:
    return ParagraphStyle(
        "SubHeader",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#475569"),
        spaceAfter=6,
        fontName="Helvetica",
    )


def _build_kpi_table(income_cents: int, expense_cents: int, net_cents: int, count: int) -> Table:
    """Build KPI summary table."""
    income = cents_to_brl(income_cents)
    expense = cents_to_brl(expense_cents)
    net = cents_to_brl(net_cents)

    data = [
        ["Receitas", "Despesas", "Resultado", "Lançamentos"],
        [income, expense, net, str(count)],
    ]

    table = Table(data, colWidths=[4 * cm] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#1E293B")),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, -1), 11),
                ("TOPPADDING", (0, 1), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _build_category_table(by_category: list[tuple[str, int]]) -> Table | None:
    """Build expenses by category table."""
    if not by_category:
        return None

    data = [["Categoria", "Valor"]]
    for name, cents in by_category[:10]:  # Top 10
        data.append([name, cents_to_brl(cents)])

    table = Table(data, colWidths=[12 * cm, 4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#334155")),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#475569")),
            ]
        )
    )
    return table


def _build_trend_table(monthly_rows: list[tuple[str, int, int]]) -> Table | None:
    """Build monthly trend table."""
    if not monthly_rows:
        return None

    data = [["Mês", "Receitas", "Despesas", "Resultado"]]
    for month, income_cents, expense_cents in monthly_rows:
        net_cents = income_cents - expense_cents
        data.append([
            month,
            cents_to_brl(income_cents),
            cents_to_brl(expense_cents),
            cents_to_brl(net_cents),
        ])

    table = Table(data, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#334155")),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#475569")),
            ]
        )
    )
    return table


def generate_report_pdf(
    *,
    start: date,
    end: date,
    income_cents: int,
    expense_cents: int,
    net_cents: int,
    count: int,
    by_category: list[tuple[str, int]],
    monthly_rows: list[tuple[str, int, int]],
) -> bytes:
    """Generate a PDF report and return as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    story: list = []

    # Title
    story.append(Paragraph("Relatório Financeiro", _header_style()))
    story.append(
        Paragraph(
            f"Período: {start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}",
            _subheader_style(),
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    # KPIs
    story.append(Paragraph("Resumo do Período", styles["Heading3"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(_build_kpi_table(income_cents, expense_cents, net_cents, count))
    story.append(Spacer(1, 0.8 * cm))

    # Categories
    cat_table = _build_category_table(by_category)
    if cat_table:
        story.append(Paragraph("Despesas por Categoria", styles["Heading3"]))
        story.append(Spacer(1, 0.2 * cm))
        story.append(cat_table)
        story.append(Spacer(1, 0.8 * cm))

    # Monthly trend
    trend_table = _build_trend_table(monthly_rows)
    if trend_table:
        story.append(Paragraph("Evolução Mensal", styles["Heading3"]))
        story.append(Spacer(1, 0.2 * cm))
        story.append(trend_table)

    # Footer
    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            f"Gerado em {date.today().strftime('%d/%m/%Y')} | Finanças App",
            styles["Normal"],
        )
    )

    doc.build(story)
    return buffer.getvalue()
