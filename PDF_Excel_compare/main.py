"""Сравнение таблицы Excel с таблицами из PDF.

Запуск:
    python main.py
    python main.py --excel source.xlsx --pdf printed.pdf --report report.xlsx
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from compare.comparer import (
    DEFAULT_ABS_TOLERANCE,
    DEFAULT_REL_TOLERANCE,
    compare_tables,
)
from compare.pdf_reader import read_pdf
from compare.readers import read_excel
from compare.report import write_report

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_EXCEL = BASE_DIR / "source.xlsx"
DEFAULT_PDF = BASE_DIR / "printed.pdf"
DEFAULT_REPORT = BASE_DIR / "differences_report.xlsx"


def _decimal(value: str) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError(f"Некорректное число: {value}") from error
    if result < 0:
        raise argparse.ArgumentTypeError("Допуск не может быть отрицательным.")
    return result


def _sheet(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Сравнение таблицы Excel с таблицами из PDF.",
    )
    parser.add_argument(
        "--excel",
        default=str(DEFAULT_EXCEL),
        help=f"Путь к Excel (по умолчанию: {DEFAULT_EXCEL.name}).",
    )
    parser.add_argument(
        "--pdf",
        default=str(DEFAULT_PDF),
        help=f"Путь к PDF (по умолчанию: {DEFAULT_PDF.name}).",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help=f"Путь к отчёту (по умолчанию: {DEFAULT_REPORT.name}).",
    )
    parser.add_argument(
        "--sheet",
        default=0,
        type=_sheet,
        help="Лист Excel: индекс (0) или имя. По умолчанию первый.",
    )
    parser.add_argument(
        "--abs-tolerance",
        default=str(DEFAULT_ABS_TOLERANCE),
        type=_decimal,
        help="Абсолютный допуск для чисел (по умолчанию 1e-9).",
    )
    parser.add_argument(
        "--rel-tolerance",
        default=str(DEFAULT_REL_TOLERANCE),
        type=_decimal,
        help="Относительный допуск для чисел (по умолчанию 1e-6).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    excel_path = Path(args.excel).expanduser()
    pdf_path = Path(args.pdf).expanduser()
    report_path = Path(args.report).expanduser()

    if not excel_path.is_file():
        print(f"Ошибка: файл Excel не найден: {excel_path}")
        return 1
    if not pdf_path.is_file():
        print(f"Ошибка: файл PDF не найден: {pdf_path}")
        return 1

    try:
        print(f"[1/3] Чтение Excel: {excel_path}")
        excel = read_excel(excel_path, sheet=args.sheet)
        print(f"      строк: {excel.height}, колонок: {excel.width}")

        print(f"[2/3] Чтение PDF: {pdf_path}")
        pdf = read_pdf(pdf_path)
        print(f"      страниц: {pdf.metadata.get('pages', '?')}, "
              f"строк: {pdf.height}, колонок: {pdf.width}")

        print("[3/3] Сравнение и формирование отчёта...")
        result = compare_tables(
            excel,
            pdf,
            abs_tolerance=args.abs_tolerance,
            rel_tolerance=args.rel_tolerance,
        )
        write_report(result, report_path)
    except Exception as error:
        print(f"Ошибка: {error}")
        return 1

    for warning in result.warnings:
        print(f"Предупреждение: {warning}")

    if result.has_differences:
        print(f"Найдено расхождений: {len(result.differences)}")
    else:
        print("Расхождений не найдено.")
    print(f"Отчёт сохранён: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
