from pathlib import Path

SERVICE_ACCOUNT_JSON = Path.home() / ".config" / "gcloud" / "food-tracker-sa.json"

DRIVE_FOLDER_ID = "1ONnXkUYAFS7EeB6VNf2eiP099uDwBgaj"

SPREADSHEET_NAME_FMT = "Food Tracker — {month} {year}"

SHEETS_REGISTRY = Path(__file__).parent / "sheets.json"

GEMINI_API_KEY_FILE = Path.home() / ".config" / "gemini" / "api_key.txt"
GEMINI_MODEL = "gemini-3.5-flash"

FOOD_LOG_SHEET = "Food Log"
FOOD_LOG_HEADER_ROW = 7
FOOD_LOG_COLS = {
    "date": 2,        # B
    "meal": 3,        # C
    "food_item": 4,   # D
    "healthiness": 5,  # E
    "protein": 6,      # F
    "carbs": 7,        # G
    "fibre": 8,        # H
    "fat": 9,          # I
    "vitamins": 10,    # J
    "calories": 11,    # K
}

EXERCISE_LOG_SHEET = "Exercise Log"
EXERCISE_LOG_HEADER_ROW = 5
EXERCISE_LOG_COLS = {
    "date": 2,         # B
    "exercise": 3,     # C
    "duration": 4,     # D
    "intensity": 5,    # E
    "calories": 6,     # F
    "steps": 7,        # G
}
