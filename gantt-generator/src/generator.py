import datetime
import openpyxl
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

def create_gantt_chart(output_filename: str = "Gantt_Schedule_2026.xlsx") -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "График работ"
    ws.views.sheetView[0].showGridLines = True

    HEADER_BG = "1F4E78"
    MONTH_BG = "2F5597"
    HEADER_FG = "FFFFFF"
    BORDER_COLOR = "D9D9D9"

    thin_border = Border(
        left=Side(style="thin", color=BORDER_COLOR),
        right=Side(style="thin", color=BORDER_COLOR),
        top=Side(style="thin", color=BORDER_COLOR),
        bottom=Side(style="thin", color=BORDER_COLOR),
    )

    ws["A1"] = "СОГЛАСОВАНО"
    ws["A2"] = "Должность _____________"
    ws["A3"] = "Организация ___________"
    ws["A4"] = "____/_______/ (Ф.И.О.)"
    ws["A5"] = "«___» ________ 202__ г."

    ws["J1"] = "УТВЕРЖДАЮ"
    ws["J2"] = "Должность _____________"
    ws["J3"] = "Организация ___________"
    ws["J4"] = "____/_______/ (Ф.И.О.)"
    ws["J5"] = "«___» ________ 202__ г."

    for r in range(1, 6):
        ws[f"A{r}"].font = Font(name="Calibri", size=9, bold=(r == 1))
        ws[f"J{r}"].font = Font(name="Calibri", size=9, bold=(r == 1))

    ws.merge_cells("A7:N7")
    title = ws["A7"]
    title.value = "ГРАФИК ПРОИЗВОДСТВА БЕТОННЫХ РАБОТ"
    title.font = Font(name="Calibri", size=14, bold=True, color="1F4E78")
    title.alignment = Alignment(horizontal="center", vertical="center")

    headers_text = ["№", "Наименование работ", "Ед. изм.", "Кол-во", "Кол-во чел.", "Начало", "Дней", "Окончание"]
    for col_idx, h_text in enumerate(headers_text, start=1):
        col_letter = get_column_letter(col_idx)
        ws.merge_cells(f"{col_letter}9:{col_letter}10")
        cell = ws.cell(row=9, column=col_idx, value=h_text)
        cell.font = Font(name="Calibri", size=10, bold=True, color=HEADER_FG)
        cell.fill = PatternFill(start_color=HEADER_BG, end_color=HEADER_BG, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.cell(row=10, column=col_idx).border = thin_border
        cell.border = thin_border

    base_date = datetime.date(2026, 9, 1)
    days_to_generate = 122
    month_names_ru = {9: "СЕНТЯБРЬ 2026", 10: "ОКТЯБРЬ 2026", 11: "НОЯБРЬ 2026", 12: "ДЕКАБРЬ 2026"}
    months_cols = {}

    for i in range(days_to_generate):
        col_idx = 9 + i
        current_date = base_date + datetime.timedelta(days=i)
        cell_day = ws.cell(row=10, column=col_idx, value=current_date)
        cell_day.number_format = "DD"
        cell_day.font = Font(name="Calibri", size=9, bold=True, color=HEADER_FG)
        cell_day.fill = PatternFill(start_color=HEADER_BG, end_color=HEADER_BG, fill_type="solid")
        cell_day.alignment = Alignment(horizontal="center", vertical="center")
        cell_day.border = thin_border
        m_key = current_date.month
        if m_key not in months_cols:
            months_cols[m_key] = []
        months_cols[m_key].append(col_idx)

    for m_num, cols in months_cols.items():
        start_c = get_column_letter(cols[0])
        end_c = get_column_letter(cols[-1])
        ws.merge_cells(f"{start_c}9:{end_c}9")
        m_cell = ws.cell(row=9, column=cols[0], value=month_names_ru[m_num])
        m_cell.font = Font(name="Calibri", size=10, bold=True, color=HEADER_FG)
        m_cell.fill = PatternFill(start_color=MONTH_BG, end_color=MONTH_BG, fill_type="solid")
        m_cell.alignment = Alignment(horizontal="center", vertical="center")
        for c in cols:
            ws.cell(row=9, column=c).border = thin_border

    data = [
        ("1", "Захватка №1. Фундаментная плита", "", "", "", "", "", ""),
        ("1.1", "Устройство бетонной подготовки", "м3", 15, 4, datetime.date(2026, 9, 1), 1),
        ("1.2", "Гидроизоляционные работы", "м2", 120, 3, datetime.date(2026, 9, 2), 1),
        ("1.3", "Монтаж арматурных каркасов", "т", 4.5, 5, datetime.date(2026, 9, 3), 2),
        ("1.4", "Монтаж опалубки", "м2", 80, 4, datetime.date(2026, 9, 4), 1),
        ("1.5", "Бетонирование (приемка и укладка)", "м3", 45, 6, datetime.date(2026, 9, 5), 1),
        ("1.6", "Уход за бетоном (набор прочности)", "шт", 1, 2, datetime.date(2026, 9, 5), 3),
        ("1.7", "Демонтаж опалубки", "м2", 80, 3, datetime.date(2026, 9, 8), 1),
        ("2", "Захватка №2. Стены и пилоны (Оси 1-3)", "", "", "", "", "", ""),
        ("2.1", "Вязка арматуры стен", "т", 3.2, 5, datetime.date(2026, 9, 7), 2),
        ("2.2", "Установка стеновой опалубки", "м2", 110, 4, datetime.date(2026, 9, 8), 2),
        ("2.3", "Бетонирование стен", "м3", 30, 6, datetime.date(2026, 9, 10), 1),
    ]

    start_row = 11
    end_col = 8 + days_to_generate

    for row_offset, row_item in enumerate(data):
        current_row = start_row + row_offset
        if row_item[2] == "":
            ws.cell(row=current_row, column=1, value=row_item[0])
            ws.cell(row=current_row, column=2, value=row_item[1])
            for c in range(1, end_col + 1):
                cell = ws.cell(row=current_row, column=c)
                cell.font = Font(name="Calibri", size=10, bold=True)
                cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
                cell.border = thin_border
        else:
            num, name, unit, qty, crew, start_date, days = row_item
            ws.cell(row=current_row, column=1, value=num)
            ws.cell(row=current_row, column=2, value=name)
            ws.cell(row=current_row, column=3, value=unit)
            ws.cell(row=current_row, column=4, value=qty)
            ws.cell(row=current_row, column=5, value=crew)
            c_start = ws.cell(row=current_row, column=6, value=start_date)
            c_start.number_format = "YYYY-MM-DD"
            ws.cell(row=current_row, column=7, value=days)
            c_end = ws.cell(row=current_row, column=8, value=f"=F{current_row}+G{current_row}-1")
            c_end.number_format = "YYYY-MM-DD"

            for c in range(1, end_col + 1):
                cell = ws.cell(row=current_row, column=c)
                cell.font = Font(name="Calibri", size=10)
                cell.border = thin_border
                if c in [1, 3, 4, 5, 6, 7, 8]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif c == 2:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

    end_col_letter = get_column_letter(end_col)
    gantt_rule = FormulaRule(
        formula=["AND(I$10>=$F11, I$10<=$H11)"],
        stopIfTrue=True,
        fill=PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid"),
        font=Font(color="FFFFFF", bold=True),
    )
    ws.conditional_formatting.add(f"I11:{end_col_letter}50", gantt_rule)

    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 36
    ws.column_dimensions["C"].width = 8
    ws.column_dimensions["D"].width = 8
    ws.column_dimensions["E"].width = 11
    ws.column_dimensions["F"].width = 11
    ws.column_dimensions["G"].width = 7
    ws.column_dimensions["H"].width = 11

    for col_idx in range(9, end_col + 1):
        col_char = get_column_letter(col_idx)
        ws.column_dimensions[col_char].width = 3

    wb.save(output_filename)
    print(f"Успешно создан файл: {output_filename}")
