import fitz
import os
from groq import Groq

def extract_data_from_pdf(pdf_path, output_csv):
    print("Reading PDF pages...")
    doc = fitz.open(pdf_path)
    combined_text = ""
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        combined_text += f"\n--- Page {page_num + 1} ---\n" + page.get_text()
        
    print("Sending data to modern Qwen 3.8 with Construction Context...")
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    # Расширенный инженерный промпт с жестким разделением материалов
    prompt = f"""
    Ты — ведущий инженер-сметчик. Ниже представлен текстовый слой архитектурного чертежа (АР).
    В проекте заложены два типа наружных стен толщиной 200 мм:
    1. Наружная стена Тип 1: Чистый пеноблок/газосиликатный блок 200 мм (ГОСТ 31359-2007).
    2. Наружная стена Тип 2: Комбинированная стена (слой монолитного железобетона 200 мм + слой газосиликатного блока 200 мм). Слой монолита относится к разделу КР и не должен учитываться в объеме чистой кладки блоков!
    
    Твоя задача:
    1. Внимательно изучи текстовые спецификации, ведомости стен и экспликации помещений на планах.
    2. Найди все геометрические размеры (длины) и привязки, относящиеся к Наружной стене Тип 1 и Наружной стене Тип 2.
    3. Рассчитай суммарную площадь (м²) отдельно для кладки блоков Тип 1 и кладки блоков Тип 2. Умножь площади на толщину блоков (0.2 м) и высоту этажа (базово 2.8 м), чтобы получить объем в м³.
    4. Для Типа 2 выдели В ОТДЕЛЬНУЮ СТРОКУ только объем газосиликатного блока, полностью исключив сопутствующий монолитный железобетон.
    5. Добавь к итоговому объему блоков 5% запаса на подрезку и бой.
    6. Выведи результат строго в формате CSV со столбцами: Конструкция,Материал,Толщина (мм),Площадь (м2),Объем с запасом (м3). Не пиши никаких вводных слов и пояснений, только строки CSV.
    
    Текст чертежа:
    {combined_text}
    """
    
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="qwen/qwen3.8-27b",
    )
    
    result_text = chat_completion.choices[0].message.content
    
    csv_lines = [line.strip() for line in result_text.split('\n') if ',' in line and not line.startswith('Конструкция,')]
    
    with open(output_csv, 'w', encoding='utf-8') as f:
        f.write("Konstrukciya,Material,Tolshina (mm),Ploshad (m2),Volume_with_waste (m3)\n")
        f.write('\n'.join(csv_lines))
