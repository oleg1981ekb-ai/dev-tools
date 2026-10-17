import os
import sys
from pathlib import Path

# Пути строятся от расположения самого файла — работает в любой директории и на любой машине
CASE_DIR = Path(__file__).resolve().parent
DATA_DIR = CASE_DIR / "data"
sys.path.append(str(CASE_DIR))

try:
    from object_detection import extract_data_from_pdf
except ImportError:
    import object_detection
    extract_data_from_pdf = object_detection.extract_data_from_pdf


def find_pdf():
    """Возвращает путь к PDF-чертежу.

    Приоритет: 1) аргумент CLI (python main.py путь/к/файлу.pdf),
    2) первый *.pdf в папке data/.
    """
    if len(sys.argv) > 1:
        pdf = Path(sys.argv[1]).expanduser()
        if not pdf.exists():
            print(f"❌ Файл не найден: {pdf}")
            return None
        return pdf

    if not DATA_DIR.exists():
        print(f"❌ Папка данных не найдена: {DATA_DIR}")
        return None

    pdfs = sorted(DATA_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"❌ В папке {DATA_DIR} нет PDF-чертежей.")
        print("   Положите PDF в эту папку или укажите путь аргументом: python main.py /path/to/drawing.pdf")
        return None
    if len(pdfs) > 1:
        print(f"⚠️ PDF-файлов найдено несколько, беру первый: {pdfs[0].name}")
    return pdfs[0]


def run_estimation():
    pdf_path = find_pdf()
    if pdf_path is None:
        return

    output_csv = DATA_DIR / "estimated_materials.csv"

    print(f"🚀 Запуск ИИ-расчета для файла: {pdf_path.name}")

    if not os.environ.get("GROQ_API_KEY"):
        print("❌ Ошибка: переменная окружения GROQ_API_KEY не задана!")
        print("   Пример: export GROQ_API_KEY=ваш_ключ")
        return

    try:
        extract_data_from_pdf(str(pdf_path), str(output_csv))
        print(f"🎉 Готово! Итоговая ведомость объемов сохранена в: {output_csv}")
    except Exception as e:
        print(f"❌ Ошибка в работе ИИ-модуля: {e}")


if __name__ == "__main__":
    run_estimation()