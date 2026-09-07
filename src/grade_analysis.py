"""Grade calculations used by the notebook and future exports."""

from __future__ import annotations

import pandas as pd

from .config import CATEGORIES, SCORE_THRESHOLDS


def analyze_grades(
    grades: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return category counts, top students, and failed-subject reports."""
    grades_with_behavior = grades.apply(pd.to_numeric, errors="coerce")
    grades_without_behavior = grades_with_behavior.drop(
        columns="Comportamiento", errors="ignore"
    )
    summary = pd.DataFrame(
        0,
        index=CATEGORIES,
        columns=grades_with_behavior.columns,
        dtype=int,
    )

    for subject in grades_with_behavior.columns:
        values = grades_with_behavior[subject]
        summary.loc["SUPERIOR", subject] = values.between(
            SCORE_THRESHOLDS["alto"], SCORE_THRESHOLDS["superior"], inclusive="both"
        ).sum()
        summary.loc["ALTO", subject] = values.between(
            SCORE_THRESHOLDS["basico"], SCORE_THRESHOLDS["alto"], inclusive="left"
        ).sum()
        summary.loc["BASICO", subject] = values.between(
            SCORE_THRESHOLDS["bajo"], SCORE_THRESHOLDS["basico"], inclusive="left"
        ).sum()
        summary.loc["BAJO", subject] = (values < SCORE_THRESHOLDS["bajo"]).sum()

    summary = summary.T
    ordered_columns = [
        subject for subject in summary.index if subject != "Comportamiento"
    ]
    if "Comportamiento" in summary.index:
        ordered_columns.append("Comportamiento")
    summary = summary.reindex(ordered_columns)

    totals = summary.sum(axis=1).replace(0, pd.NA)
    percentages = summary.div(totals, axis=0).mul(100).round(2)
    percentages.columns = [f"{column} (%)" for column in percentages.columns]

    averages = grades_without_behavior.mean(axis=1).astype(float)
    best_students = grades_without_behavior.assign(Promedio=averages).sort_values(
        "Promedio", ascending=False
    )

    failed_mask = grades_without_behavior < SCORE_THRESHOLDS["bajo"]
    failed_by_subject = {
        subject: grades_without_behavior.index[failed_mask[subject]].tolist()
        for subject in grades_without_behavior.columns
    }
    failed_subject_counts = {
        subject: len(students) for subject, students in failed_by_subject.items()
    }
    failed_per_subject = pd.DataFrame({
        "Cantidad de estudiantes que pierden": failed_subject_counts,
        "Estudiantes": failed_by_subject,
    })

    failed_students = grades_without_behavior.loc[failed_mask.any(axis=1)]
    failed_per_student = pd.DataFrame({
        "Materias perdidas": failed_mask.loc[failed_students.index].sum(axis=1),
        "Asignaturas perdidas": failed_mask.loc[failed_students.index].apply(
            lambda row: row.index[row].tolist(), axis=1
        ),
    })

    return summary, percentages, best_students, failed_per_subject, failed_per_student
