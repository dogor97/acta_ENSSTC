"""Excel loading and normalization for grade books."""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pandas as pd

from .config import GRADE_NUMBERS, GRADES, PERIODS, SUBJECTS
from .grade_analysis import analyze_grades
from .report_models import ClassReport
from .report_validation import validate_results


SPREADSHEETML_NAMESPACE = "urn:schemas-microsoft-com:office:spreadsheet"
SS = f"{{{SPREADSHEETML_NAMESPACE}}}"


def _is_spreadsheetml(path: str | Path) -> bool:
    return Path(path).read_bytes().lstrip().startswith(b"<?xml")


def _spreadsheetml_sheets(path: str | Path) -> list[ET.Element]:
    root = ET.parse(path).getroot()
    return root.findall(f"{SS}Worksheet")


def _read_spreadsheetml_sheet(path: str | Path, sheet_number: int) -> pd.DataFrame:
    worksheets = _spreadsheetml_sheets(path)
    worksheet = worksheets[sheet_number - 1]
    rows = []

    for row_element in worksheet.findall(f".//{SS}Row"):
        values = []
        next_column = 1
        for cell in row_element.findall(f"{SS}Cell"):
            cell_index = cell.get(f"{SS}Index")
            if cell_index:
                next_column = int(cell_index)
            while len(values) < next_column - 1:
                values.append(None)
            data = cell.find(f"{SS}Data")
            values.append(data.text if data is not None else None)
            next_column += 1
        rows.append(values)

    width = max((len(row) for row in rows), default=0)
    return pd.DataFrame([row + [None] * (width - len(row)) for row in rows])


def _workbook_sheet_names(path: str | Path) -> list[str]:
    if _is_spreadsheetml(path):
        return [sheet.get(f"{SS}Name", "") for sheet in _spreadsheetml_sheets(path)]
    return pd.ExcelFile(path).sheet_names


def _normalized_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(char for char in text if not unicodedata.combining(char)).upper()


def _find_grade(header_text: str, sheet_name: str) -> str | None:
    search_text = _normalized_text(f"{header_text} {sheet_name}")
    return next(
        (grade for grade in GRADES if _normalized_text(grade) in search_text),
        None,
    )


def _find_section(header_text: str, sheet_name: str) -> str | None:
    search_text = f"{header_text} {sheet_name}"
    numeric_section = re.search(r"(?:^|\s)([1-5])(?:\s|$)", search_text)
    if numeric_section:
        return numeric_section.group(1)

    normalized_text = _normalized_text(search_text)
    for section_number, section_name in enumerate(GRADE_NUMBERS, start=1):
        if re.search(rf"(?:^|\s){_normalized_text(section_name)}(?:\s|$)", normalized_text):
            return str(section_number)
    return None


def _subject_name(value: Any) -> str:
    normalized = _normalized_text(value).rstrip(".")
    aliases = {
        "CATEDRA DE LA PAZ": "Cátedra de la paz",
        "CIENCIAS NATURALES": "Ciencias naturales",
        "CIENCIAS SOCIALES": "Ciencias sociales",
        "COMPORTAMIENTO": "Comportamiento",
        "EDUCACION ARTISTICA": "Educación artística",
        "EDUCACION FISICA": "Educación física",
        "INFORMATICA": "Informática",
        "INGLES": "Inglés",
        "INVESTIGACION": "Investigación",
        "L. CASTELLANA": "Español",
        "MATEMATICAS": "Matemáticas",
        "PEDAGOGIA": "Pedagogía",
        "RELIGION": "Religión",
    }
    return aliases.get(normalized, str(value).strip())


def _format_spreadsheetml(
    path: str | Path,
    sheet_number: int,
    period_id: str,
) -> pd.DataFrame:
    raw = _read_spreadsheetml_sheet(path, sheet_number)
    period_row = next(
        index for index, value in raw.iloc[:, 0].items()
        if str(value).strip().lower().startswith("periodo")
    )
    names_row = next(
        index for index in range(period_row + 1, len(raw))
        if any("COMPORTAMIENTO" in _normalized_text(value)
               for value in raw.iloc[index].tolist())
    )
    values_row = names_row + 1
    selected_columns = [
        column for column, value in raw.iloc[values_row].items()
        if column == 0 or period_id in str(value)
    ]
    available_subjects = [
        _subject_name(value)
        for value in raw.iloc[names_row, 1:].tolist()
        if pd.notna(value) and str(value).strip()
    ]
    subject_names = ["NOMBRE", *available_subjects[:len(selected_columns) - 1]]
    grades = raw.iloc[values_row + 1:, selected_columns].copy()
    grades = grades[grades.iloc[:, 0].notna()]
    grades.columns = subject_names
    return grades.set_index("NOMBRE")


class XLSFormatter:
    """Read one grade-book sheet and calculate its reports.

    This facade keeps the original notebook API while the implementation is
    separated into importable modules.
    """

    def __init__(self, path: str, sheet_number: int, sheet_name: str | None = None):
        self.path = path
        self.sheet_number = sheet_number
        self.sheet_name = sheet_name or str(sheet_number)
        self.grade_id: int | None = None
        self.grade_number_id: int | None = None
        self.period_id: str | None = None
        self.grade: str | None = None
        self.section: str | None = None
        self.performance_summary = None
        self.performance_percentages = None
        self.top_students = None
        self.failed_students_by_subject = None
        self.failed_subjects_by_student = None

    def formatxlsx(self) -> pd.DataFrame:
        if _is_spreadsheetml(self.path):
            raw = _read_spreadsheetml_sheet(self.path, self.sheet_number)
            header_text = next(
                str(value) for value in raw.iloc[:, 0]
                if str(value).strip().lower().startswith("clase:")
            )
            self.grade = _find_grade(header_text, self.sheet_name)
            self.section = _find_section(header_text, self.sheet_name)
            period_text = next(
                str(value) for value in raw.iloc[:, 0]
                if str(value).strip().lower().startswith("periodo")
            )
            self.period_id = next(period for period in PERIODS if period in period_text)
            self.grade_id = next(
                (index for index, grade in enumerate(GRADES) if grade == self.grade),
                None,
            )
            self.grade_number_id = next(
                (index for index in range(len(GRADE_NUMBERS))
                 if str(index + 1) == self.section),
                None,
            )
            return _format_spreadsheetml(self.path, self.sheet_number, self.period_id)

        raw = pd.read_excel(
            self.path,
            sheet_name=self.sheet_number - 1,
            header=None,
        )
        raw = raw.drop([0, 1]).reset_index(drop=True)

        header_text = str(raw.iloc[0, 0])
        self.grade = _find_grade(header_text, self.sheet_name)
        self.section = _find_section(header_text, self.sheet_name)
        self.grade_id = next(
            (index for index, grade in enumerate(GRADES) if grade == self.grade),
            None,
        )
        self.grade_number_id = next(
            (index for index, number in enumerate(GRADE_NUMBERS)
             if str(index + 1) == self.section or number == self.section),
            None,
        )
        self.period_id = next(period for period in PERIODS if period in str(raw.iloc[2, 0]))

        raw = raw.drop([0, 1, 2, 3]).reset_index(drop=True)
        period_columns = raw.iloc[1].astype(str).str.contains(self.period_id, na=False)
        columns_to_keep = raw.columns[period_columns]
        raw = raw.loc[:, [column for column in raw.columns if column == 0 or column in columns_to_keep]]
        raw = raw.drop(raw.index[1]).reset_index(drop=True)
        raw.iloc[0] = SUBJECTS
        raw = raw.T.set_index(raw.T.iloc[:, 0]).drop(columns=raw.columns[0]).T
        raw = raw.set_index(raw.iloc[:, 0]).drop(columns=raw.columns[0])

        if "Comportamiento" in raw.columns:
            behavior = raw.pop("Comportamiento")
            raw["Comportamiento"] = behavior

        return raw

    def notas_sum(self, grades: pd.DataFrame):
        reports = analyze_grades(grades)
        (
            self.performance_summary,
            self.performance_percentages,
            self.top_students,
            self.failed_students_by_subject,
            self.failed_subjects_by_student,
        ) = reports
        return reports


def analyze_workbook(
    path: str,
    expected_grades: tuple[str, ...] | None = None,
    expected_sections: tuple[str, ...] | None = None,
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, Any]]:
    """Analyze every workbook sheet and organize reports by grade and section."""
    sheet_names = _workbook_sheet_names(path)
    results: dict[str, dict[str, dict[str, Any]]] = {}
    sheets_by_class: dict[tuple[str, str], list[str]] = {}

    for sheet_number, sheet_name in enumerate(sheet_names, start=1):
        formatter = XLSFormatter(path, sheet_number, sheet_name)
        grades = formatter.formatxlsx()
        reports = formatter.notas_sum(grades)

        if formatter.grade is None or formatter.section is None:
            raise ValueError(
                f"Could not identify grade and section in sheet '{sheet_name}'. "
                "Use a sheet name or header such as 'SÉPTIMO 1'."
            )

        class_key = (formatter.grade, formatter.section)
        sheets_by_class.setdefault(class_key, []).append(sheet_name)
        results.setdefault(formatter.grade, {})[formatter.section] = ClassReport(
            grade=formatter.grade,
            section=formatter.section,
            sheet_name=sheet_name,
            period=formatter.period_id,
            student_count=len(grades),
            performance_summary=reports[0],
            performance_percentages=reports[1],
            top_students=reports[2],
            failed_students_by_subject=reports[3],
            failed_subjects_by_student=reports[4],
        )

    duplicate_sections = {
        f"{grade} {section}": sheet_names
        for (grade, section), sheet_names in sheets_by_class.items()
        if len(sheet_names) > 1
    }
    found_sections = {
        grade: sorted(sections) for grade, sections in results.items()
    }
    missing_sections = {}
    if expected_sections is not None:
        missing_sections = {
            grade: [section for section in expected_sections if section not in sections]
            for grade, sections in found_sections.items()
            if any(section not in sections for section in expected_sections)
        }
    missing_grades = []
    if expected_grades is not None:
        missing_grades = [grade for grade in expected_grades if grade not in results]

    validation = {
        "sheet_names": sheet_names,
        "found_sections": found_sections,
        "missing_grades": missing_grades,
        "missing_sections": missing_sections,
        "duplicate_sections": duplicate_sections,
    }
    validation = validate_results(results, validation)
    return results, validation
