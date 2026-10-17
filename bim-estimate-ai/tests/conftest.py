import os
import sys

# Чистые функции лежат в case_01_block_takeoff/ — добавляем в sys.path для импорта из тестов
CASE_DIR = os.path.join(os.path.dirname(__file__), "..", "case_01_block_takeoff")
sys.path.insert(0, os.path.abspath(CASE_DIR))
