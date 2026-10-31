import pandas as pd

import main as cli
from compare.models import TableData


def test_main_reports_missing_files(tmp_path, capsys):
    code = cli.main(
        [
            "--excel",
            str(tmp_path / "missing.xlsx"),
            "--pdf",
            str(tmp_path / "missing.pdf"),
        ]
    )
    assert code == 1
    assert "не найден" in capsys.readouterr().out


def test_main_runs_comparison(tmp_path, monkeypatch, capsys):
    excel_path = tmp_path / "source.xlsx"
    pdf_path = tmp_path / "printed.pdf"
    report_path = tmp_path / "report.xlsx"

    pd.DataFrame({"A": [1, 2]}).to_excel(excel_path, index=False)
    pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        cli,
        "read_pdf",
        lambda path: TableData(
            source=str(path),
            headers=["A"],
            rows=[["1"], ["3"]],
            metadata={"pages": 1},
        ),
    )

    code = cli.main(
        [
            "--excel",
            str(excel_path),
            "--pdf",
            str(pdf_path),
            "--report",
            str(report_path),
        ]
    )

    assert code == 0
    assert report_path.is_file()
    output = capsys.readouterr().out
    assert "Найдено расхождений: 1" in output
    assert "Отчёт сохранён" in output
