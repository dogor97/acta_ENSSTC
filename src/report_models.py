"""Structured result objects shared by report exporters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class ClassReport:
    """All report tables and metadata for one grade section."""

    grade: str
    section: str
    sheet_name: str
    period: str | None
    student_count: int
    performance_summary: pd.DataFrame
    performance_percentages: pd.DataFrame
    top_students: pd.DataFrame
    failed_students_by_subject: pd.DataFrame
    failed_subjects_by_student: pd.DataFrame

    def __getitem__(self, key: str) -> Any:
        """Keep dictionary-style access convenient in notebooks."""
        return getattr(self, key)

    def as_dict(self) -> dict[str, Any]:
        return {
            "grade": self.grade,
            "section": self.section,
            "sheet_name": self.sheet_name,
            "period": self.period,
            "student_count": self.student_count,
            "performance_summary": self.performance_summary,
            "performance_percentages": self.performance_percentages,
            "top_students": self.top_students,
            "failed_students_by_subject": self.failed_students_by_subject,
            "failed_subjects_by_student": self.failed_subjects_by_student,
        }
