"""Export analyzed reports to an Excel workbook."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .report_models import ClassReport


def export_excel(
    results: dict[str, dict[str, ClassReport]],
    output_path: str | Path,
) -> Path:
    """Write one worksheet per report and return the output path."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(destination, engine="openpyxl") as writer:
        for grade, sections in results.items():
            for section, report in sections.items():
                prefix = f"{grade[:3]}_{section}"
                report.performance_summary.to_excel(
                    writer, sheet_name=f"{prefix}_rendimiento"[:31]
                )
                report.performance_percentages.to_excel(
                    writer, sheet_name=f"{prefix}_porcentajes"[:31]
                )
                report.top_students.to_excel(
                    writer, sheet_name=f"{prefix}_mejores"[:31]
                )
                report.failed_students_by_subject.to_excel(
                    writer, sheet_name=f"{prefix}_perdidos"[:31]
                )
                report.failed_subjects_by_student.to_excel(
                    writer, sheet_name=f"{prefix}_estudiantes"[:31]
                )

    return destination
