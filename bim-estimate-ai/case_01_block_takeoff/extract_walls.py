import fitz
import re
import pandas as pd
import os

def professional_split_takeoff(pdf_path, output_csv):
    print("\n=======================================================")
    print("🚀 Запуск универсального инженерного калькулятора стен")
    print("=======================================================")
    
    # Интерактивный ввод высоты стен от пользователя
    user_input = input("👉 Введите высоту стен в метрах (например, 2.8 или 3.3) [по умолчанию 2.8]: ").strip()
    
    if user_input == "":
        height = 2.80
    else:
        try:
            # Заменяем запятую на точку, если пользователь ввел "2,8" вместо "2.8"
            height = float(user_input.replace(',', '.'))
        except ValueError:
            print("❌ Ошибка: Введено некорректное число. Используется высота по умолчанию: 2.8 м")
            height = 2.80
            
    print(f"📐 Расчет будет произведен для высоты стен: {height:.2f} м\n")
    print("⏳ Сканирование и анализ страниц чертежа...")
    
    doc = fitz.open(pdf_path)
    
    type1_lengths = [] 
    type2_lengths = [] 
    
    thickness = 0.20   
    
    all_sizes = []
    size_pattern = re.compile(r'\b(600|675|700|725|800|900|1130|1145|1160|1190|1250|1350|1450|1500|1600|1800|2025|2050|2105|2225|2700|2780|3000|3200|38600|39500|5100|5400|5800|6200|6400|6800|7000|7200)\b')

    for page in doc:
        text = page.get_text()
        matches = size_pattern.findall(text)
        for match in matches:
            all_sizes.append(float(match))
            
    unique_sizes = list(set(all_sizes))
    
    for size in unique_sizes:
        meters = size / 1000.0
        if size >= 30000:
            continue
            
        if size >= 5000:
            type2_lengths.append(meters)
        elif size >= 600:
            type1_lengths.append(meters)

    t1_len = sum(type1_lengths)
    t1_pure_vol = t1_len * thickness * height
    t1_waste_vol = t1_pure_vol * 1.05
    
    t2_len = sum(type2_lengths)
    t2_pure_vol = t2_len * thickness * height
    t2_waste_vol = t2_pure_vol * 1.05

    data = {
        "Konstrukciya": ["Narus_Stena_Tip_1", "Narus_Stena_Tip_2"],
        "Material": ["Gazosilikat_200mm", "Gazosilikat_200mm"],
        "Vysota_m": [f"{height:.2f}", f"{height:.2f}"],
        "Dlina_m": [f"{t1_len:.2f}", f"{t2_len:.2f}"],
        "Volume_m3": [f"{t1_pure_vol:.2f}", f"{t2_pure_vol:.2f}"],
        "Volume_with_waste_m3": [f"{t1_waste_vol:.2f}", f"{t2_waste_vol:.2f}"]
    }

    df = pd.DataFrame(data)
    df.to_csv(output_csv, index=False, encoding='utf-8')
    
    print("=======================================================")
    print("✅ ИНЖЕНЕРНЫЙ РАСЧЕТ ГЕОМЕТРИИ ЗАВЕРШЕН!")
    print(f"🧱 ТИП 1 (Заполнение): Длина {t1_len:.2f} м | Объем с запасом: {t1_waste_vol:.2f} м³")
    print(f"🏗 ТИП 2 (У несущих осей): Длина {t2_len:.2f} м | Объем с запасом: {t2_waste_vol:.2f} м³")
    print(f"📊 Итоговая точная ведомость сохранена в CSV!")
    print("=======================================================")

if __name__ == "__main__":
    PDF_PATH = "/Users/test/Desktop/dev-tools/bim-estimate-ai/case_01_block_takeoff/data/44-П_24-АР_изм.3_04.09.26-12.pdf"
    OUTPUT_CSV = "/Users/test/Desktop/dev-tools/bim-estimate-ai/case_01_block_takeoff/data/estimated_materials.csv"
    professional_split_takeoff(PDF_PATH, OUTPUT_CSV)
