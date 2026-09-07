"""Render commission reports using the institutional Word template."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from docxtpl import DocxTemplate

from .report_models import ClassReport


MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
PERIOD_LABELS = {
    "1/4": "PRIMER",
    "2/4": "SEGUNDO",
    "3/4": "TERCER",
    "4/4": "CUARTO",
}


def _performance_rows(report: ClassReport) -> list[dict[str, Any]]:
    summary = report.performance_summary
    return [
        {
            "subject": str(subject),
            "sup": int(row.get("SUPERIOR", 0)),
            "alt": int(row.get("ALTO", 0)),
            "bas": int(row.get("BASICO", 0)),
            "baj": int(row.get("BAJO", 0)),
        }
        for subject, row in summary.iterrows()
    ]


def _student_name(value: Any) -> str:
    return str(value).strip()


def _template_context(
    reports: list[ClassReport], report_date: date,
) -> dict[str, Any]:
    primary = reports[0]
    period = primary.period or ""
    context: dict[str, Any] = {
        "date": report_date.strftime("%d/%m/%Y"),
        "day": str(report_date.day),
        "month": MONTHS[report_date.month - 1],
        "grade": primary.grade,
        "period": PERIOD_LABELS.get(period, period),
    }

    for index in range(1, 5):
        report = reports[index - 1] if index <= len(reports) else None
        context[f"grade_{index}"] = (
            f"{report.grade} {report.section}" if report else ""
        )
        context[f"number_grade_{index}"] = report.student_count if report else 0
        context[f"sales{index}"] = _performance_rows(report) if report else []

        for place in range(1, 4):
            key = f"best{place}_g{index}"
            context[key] = ""
            if report is not None and len(report.top_students) >= place:
                student = report.top_students.iloc[place - 1]
                context[key] = _student_name(report.top_students.index[place - 1])

    return context


def export_word(
    results: dict[str, dict[str, ClassReport]],
    template_path: str | Path,
    output_path: str | Path,
    report_date: date | None = None,
) -> Path:
    """Render analyzed results into the supplied institutional template."""
    reports = [
        report
        for sections in results.values()
        for report in sections.values()
    ]
    if not reports:
        raise ValueError("No class reports are available for the Word document.")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    template = DocxTemplate(_sanitized_template(template_path))
    template.render(_template_context(reports[:4], report_date or date.today()))
    template.save(destination)
    return destination


def _sanitized_template(path: str | Path) -> BytesIO:
    """Return a renderable copy without changing the source template."""
    source = BytesIO()
    with ZipFile(path) as archive, ZipFile(
        source, "w", compression=ZIP_DEFLATED
    ) as sanitized:
        for item in archive.infolist():
            content = archive.read(item.filename)
            if item.filename == "word/document.xml":
                content = content.replace(
                    b"{{performance summary}}",
                    b"{{performance_summary}}",
                )
                content = content.replace(
                    b'xml:space="preserve">erformance </w:t>',
                    b'xml:space="preserve">erformance_</w:t>',
                )
            sanitized.writestr(item, content)
    source.seek(0)
    return source