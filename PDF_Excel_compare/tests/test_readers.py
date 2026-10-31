import pandas as pd

from compare.readers import read_excel


def test_read_excel_reads_headers_and_drops_empty_rows(tmp_path):
    path = tmp_path / "source.xlsx"
    frame = pd.DataFrame({"A": [1, None, 3], "B": ["x", None, "z"]})
    frame.to_excel(path, index=False)

    table = read_excel(path)

    assert table.headers == ["A", "B"]
    assert table.rows == [[1, "x"], [3, "z"]]
    assert table.metadata["dropped_empty_rows"] == 1


def test_read_excel_can_select_sheet_by_name(tmp_path):
    path = tmp_path / "source.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"A": [1]}).to_excel(writer, sheet_name="first", index=False)
        pd.DataFrame({"B": [2]}).to_excel(writer, sheet_name="second", index=False)

    table = read_excel(path, sheet="second")

    assert table.headers == ["B"]
    assert table.rows == [[2]]
