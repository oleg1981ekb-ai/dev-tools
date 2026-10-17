import os
import sys

# Жестко прописываем абсолютные пути для стабильности на Mac
BASE_DIR = "/Users/test/Desktop/dev-tools/bim-estimate-ai"
CASE_DIR = os.path.join(BASE_DIR, "case_01_block_takeoff")
sys.path.append(CASE_DIR)

try:
    from object_detection import extract_data_from_pdf
except ImportError:
    import object_detection
    extract_data_from_pdf = object_detection.extract_data_from_pdf

if not os.environ.get("GROQ_API_KEY"):
    print("❌ Ошибка: API-ключ GROQ_API_KEY не задан в сессии Терминала!")
    exit(1)

def run_estimation():
    # Точные, проверенные абсолютные координаты файлов
    pdf_path = os.path.join(CASE_DIR, "data", "44-П_24-АР_изм.3_04.09.26-12.pdf")
    output_csv = os.path.join(CASE_DIR, "data", "estimated_materials.csv")
    
    print(f"🚀 Запуск ИИ-расчета для файла: {os.path.basename(pdf_path)}")
    
    if not os.path.exists(pdf_path):
        print(f"❌ Чертеж не найден по абсолютному пути: {pdf_path}")
        print("\nПожалуйста, выполните команду 'open /Users/test/Desktop/dev-tools/bim-estimate-ai/case_01_block_takeoff/data' и убедитесь, что ваш PDF лежит внутри этой папки!")
        return

    try:
        extract_data_from_pdf(pdf_path, output_csv)
        print(f"🎉 Готово! Итоговая ведомость объемов сохранена в: {output_csv}")
    except Exception as e:
        print(f"❌ Ошибка в работе ИИ-модуля: {e}")

if __name__ == "__main__":
    run_estimation()
