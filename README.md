# acta_ENSSTC

This project reads grade-book Excel files and generates academic performance
summaries for the ENSSTC acta workflow.

## Structure

- `Codigo_acta_ENSSTC.ipynb`: interactive entry point for Colab or VS Code.
- `src/config.py`: subjects, categories, and score thresholds.
- `src/excel_reader.py`: Excel sheet discovery, metadata validation, and normalization.
- `src/grade_analysis.py`: performance counts, rankings, and failed-subject reports.
- `src/report_models.py`: structured metadata and report objects.
- `src/report_validation.py`: validation for workbook and class reports.
- `src/report_export.py`: Excel export for checking results before Word generation.
- `src/word_export.py`: Word report generation using the institutional template.
- `requirements.txt`: Python dependencies.

## Colab setup

Clone or place the repository in Google Drive, then run this at the start of
the notebook:

```python
from google.colab import drive
drive.mount("/content/drive")
%cd "/content/drive/MyDrive/Normal/codefiles/acta_ENSSTC"
```

Install dependencies if needed:

```python
%pip install -r requirements.txt
```

The input Excel files should remain outside the public repository because they
contain student information.

## Analyze all sheets

The workbook analyzer discovers every sheet and organizes results by grade and
section. Sheet names or headers should identify the class, for example
`Septimo 1`, `Septimo 2`, and `Septimo 3`.

```python
from src.excel_reader import analyze_workbook

results, validation = analyze_workbook(input_path)

if not validation["valid"]:
    raise ValueError(validation)

for grade, sections in results.items():
	for section, reports in sections.items():
		print(grade, section)
		display(reports["performance_summary"])
		display(reports["performance_percentages"])
```

`validation` reports the discovered sheets, sections, and duplicate sections.
To check that every grade is expected to have sections 1, 2, and 3, use:

```python
results, validation = analyze_workbook(
	input_path,
	expected_grades=("SÉPTIMO", "OCTAVO"),
	expected_sections=("1", "2", "3"),
)
```

## Export an intermediate Excel report

Check the analyzed data before creating Word documents:

```python
from src.report_export import export_excel

export_excel(results, "/content/drive/MyDrive/Normal/notas/resultados_acta.xlsx")
```

Each class gets worksheets for performance counts, percentages, top students,
failed students by subject, and failed subjects by student. The same `results`
objects will later be used by the Word exporter.

## Generate the Word report locally

The institutional template is stored at
`template/template-ACTA DE COMISION DE EVALUACION ENSSTC.docx`.

```python
from src.word_export import export_word

output_path = project_root / "output" / "acta_comision_local.docx"
export_word(
	results,
	project_root / "template" / "template-ACTA DE COMISION DE EVALUACION ENSSTC.docx",
	output_path,
)
print(f"Word report written to: {output_path.resolve()}")
```