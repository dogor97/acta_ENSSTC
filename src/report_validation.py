"""Validation rules for analyzed class reports."""

from __future__ import annotations

from typing import Any

from .report_models import ClassReport


def validate_report(report: ClassReport) -> list[str]:
    """Return validation messages for one report; an empty list means valid."""
    errors: list[str] = []
    if not report.grade or not report.section:
        errors.append("Grade and section are required.")
    if report.student_count == 0:
        errors.append("The sheet contains no students.")
    if report.performance_summary.empty:
        errors.append("The performance summary is empty.")
    if report.top_students.empty:
        errors.append("The top-students report is empty.")
    if report.performance_summary.index.duplicated().any():
        errors.append("The performance summary contains duplicate subjects.")
    return errors


def validate_results(
    results: dict[str, dict[str, ClassReport]],
    validation: dict[str, Any],
) -> dict[str, Any]:
    """Combine workbook discovery checks with per-report checks."""
    report_errors = {
        f"{grade} {section}": validate_report(report)
        for grade, sections in results.items()
        for section, report in sections.items()
    }
    report_errors = {key: errors for key, errors in report_errors.items() if errors}
    return {
        **validation,
        "report_errors": report_errors,
        "valid": not (
            validation.get("missing_grades")
            or validation.get("missing_sections")
            or validation.get("duplicate_sections")
            or report_errors
        ),
    }
