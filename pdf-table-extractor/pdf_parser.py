import camelot
import os
import pandas as pd

print("=== УТИЛИТА ИЗВЛЕЧЕНИЯ ТАБЛИЦ ИЗ PDF ===")

# Запрашиваем имя файла у пользователя
filename = input("Введите точное имя файла в Загрузках (например, spec.pdf): ").strip()

# Если пользователь забыл написать .pdf, добавляем автоматически
if not filename.endswith('.pdf'):
    filename += '.pdf'

pdf_path = os.path.expanduser(f"~/Downloads/{filename}")
excel_name = filename.replace('.pdf', '.xlsx')
excel_path = os.path.expanduser(f"~/Desktop/{excel_name}")

if not os.path.exists(pdf_path):
    print(f"\n[Ошибка] Файл '{filename}' не найден в папке Загрузки!")
    print(f"Искали по пути: {pdf_path}")
    input("\nНажмите Enter для выхода...")
    exit()

print(f"\nЧитаем '{filename}' с помощью Camelot (это может занять до 30 секунд)...")

try:
    # Сканируем линии таблицы по всему документу
    tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')

    if len(tables) > 0:
        # Объединяем все фрагменты таблиц в один массив данных
        combined_df = pd.concat([table.df for table in tables], ignore_index=True)
        
        # Сохраняем готовый Excel-файл на Рабочий стол
        combined_df.to_excel(excel_path, index=False, header=False)
        print(f"\n[Успех!] Найдено фрагментов таблиц: {len(tables)}.")
        print(f"Готовый файл сохранен на Рабочий стол под именем: {excel_name}")
    else:
        print("\n[Внимание] Camelot не смог обнаружить линии таблиц в этом PDF.")
except Exception as e:
    print(f"\nПроизошла ошибка при обработке: {e}")

input("\nНажмите Enter для завершения программы...")

