#!/usr/bin/env python3
"""
Daily cron job: read the current month's Google Sheet (by ID from sheets.json),
estimate missing nutrition/exercise values via local Ollama, write results back.

If no sheet is registered for the current month, logs a warning and exits.
Register a new month with: python upload_template.py <sheet_url> <year> <month>
"""

import calendar
import sys
import time
from datetime import date, datetime

import gspread
from google.oauth2.service_account import Credentials

from config import (
    SERVICE_ACCOUNT_JSON,
    FOOD_LOG_SHEET,
    FOOD_LOG_HEADER_ROW,
    FOOD_LOG_COLS,
    EXERCISE_LOG_SHEET,
    EXERCISE_LOG_HEADER_ROW,
    EXERCISE_LOG_COLS,
)
from sheet_registry import get_sheet_id
from estimator import estimate_food_nutrition, estimate_exercise_calories

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_spreadsheet(year: int, month: int):
    sheet_id = get_sheet_id(year, month)
    if not sheet_id:
        return None
    creds = Credentials.from_service_account_file(str(SERVICE_ACCOUNT_JSON), scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(sheet_id)


def col_letter(col_num: int) -> str:
    return chr(ord("A") + col_num - 1)


def fill_food_log(spreadsheet):
    ws = spreadsheet.worksheet(FOOD_LOG_SHEET)
    all_values = ws.get_all_values()
    data_start = FOOD_LOG_HEADER_ROW
    updates = []

    for i, row in enumerate(all_values[data_start:], start=data_start + 1):
        food_col = FOOD_LOG_COLS["food_item"] - 1
        calories_col = FOOD_LOG_COLS["calories"] - 1

        if len(row) <= food_col:
            continue

        food_item = (row[food_col] or "").strip()
        has_calories = len(row) > calories_col and (row[calories_col] or "").strip()

        if not food_item or has_calories:
            continue

        meal_col = FOOD_LOG_COLS["meal"] - 1
        meal = row[meal_col] if len(row) > meal_col else "Meal"
        sheet_row = i

        print(f"  Estimating: {food_item} ({meal})")
        result = estimate_food_nutrition(food_item, meal)
        if not result:
            print(f"    Skipped (estimation failed)")
            continue

        for field in ("protein", "carbs", "fibre", "fat", "vitamins", "calories"):
            col = col_letter(FOOD_LOG_COLS[field])
            updates.append({
                "range": f"{col}{sheet_row}",
                "values": [[result[field]]],
            })
        print(f"    -> P:{result['protein']}g C:{result['carbs']}g Fi:{result['fibre']}g "
              f"Fa:{result['fat']}g V:{result['vitamins']} Cal:{result['calories']}")

        time.sleep(1)

    if updates:
        ws.batch_update(updates, value_input_option="RAW")
        print(f"  Updated {len(updates) // 6} food entries")
    else:
        print("  No food entries need estimation")


def fill_exercise_log(spreadsheet):
    ws = spreadsheet.worksheet(EXERCISE_LOG_SHEET)
    all_values = ws.get_all_values()
    data_start = EXERCISE_LOG_HEADER_ROW
    updates = []

    for i, row in enumerate(all_values[data_start:], start=data_start + 1):
        exercise_col = EXERCISE_LOG_COLS["exercise"] - 1
        calories_col = EXERCISE_LOG_COLS["calories"] - 1

        if len(row) <= exercise_col:
            continue

        exercise = (row[exercise_col] or "").strip()
        has_calories = len(row) > calories_col and (row[calories_col] or "").strip()

        if not exercise or has_calories:
            continue

        duration_col = EXERCISE_LOG_COLS["duration"] - 1
        intensity_col = EXERCISE_LOG_COLS["intensity"] - 1

        try:
            duration = int(row[duration_col]) if len(row) > duration_col and row[duration_col] else 30
        except ValueError:
            duration = 30

        intensity = row[intensity_col].strip() if len(row) > intensity_col and row[intensity_col] else "Med"
        sheet_row = i

        print(f"  Estimating: {exercise} ({duration}min, {intensity})")
        cal = estimate_exercise_calories(exercise, duration, intensity)
        if cal is None:
            print(f"    Skipped (estimation failed)")
            continue

        col = col_letter(EXERCISE_LOG_COLS["calories"])
        updates.append({
            "range": f"{col}{sheet_row}",
            "values": [[cal]],
        })
        print(f"    -> {cal} kcal")

        time.sleep(1)

    if updates:
        ws.batch_update(updates, value_input_option="RAW")
        print(f"  Updated {len(updates)} exercise entries")
    else:
        print("  No exercise entries need estimation")


CAL_COLORS = {
    "green_bg": {"red": 0.78, "green": 0.96, "blue": 0.84},
    "green_fg": {"red": 0.15, "green": 0.40, "blue": 0.29},
    "yellow_bg": {"red": 1.0, "green": 0.99, "blue": 0.75},
    "yellow_fg": {"red": 0.59, "green": 0.35, "blue": 0.09},
    "red_bg": {"red": 1.0, "green": 0.84, "blue": 0.84},
    "red_fg": {"red": 0.61, "green": 0.17, "blue": 0.17},
    "gray_bg": {"red": 0.93, "green": 0.95, "blue": 0.97},
    "gray_fg": {"red": 0.63, "green": 0.68, "blue": 0.72},
}


def _cal_color(score):
    if score >= 4:
        return CAL_COLORS["green_bg"], CAL_COLORS["green_fg"]
    if score >= 2.5:
        return CAL_COLORS["yellow_bg"], CAL_COLORS["yellow_fg"]
    return CAL_COLORS["red_bg"], CAL_COLORS["red_fg"]


def fill_calendar(spreadsheet, year, month):
    dd = spreadsheet.worksheet("Dashboard Data")
    dd_vals = dd.get_all_values()
    days_in_month = calendar.monthrange(year, month)[1]

    daily_scores = {}
    for row in dd_vals[6:6 + days_in_month]:
        try:
            day = int(row[1])
            score = float(row[3]) if row[3] else 0
            if score > 0:
                daily_scores[day] = score
        except (ValueError, IndexError):
            continue

    if not daily_scores:
        print("  No days with healthiness data")
        return

    cal_ws = spreadsheet.worksheet("Calendar")
    cal_sid = cal_ws.id
    first_dow = calendar.weekday(year, month, 1)
    first_dow_sun = (first_dow + 1) % 7

    text_updates = []
    fmt_requests = []
    day = 1
    for week_idx, week_row in enumerate(range(8, 22, 3)):
        score_row = week_row + 1
        day_num_row = week_row
        for col in range(7):
            if (week_idx == 0 and col < first_dow_sun) or day > days_in_month:
                continue
            if day in daily_scores:
                score = daily_scores[day]
                col_letter_str = chr(ord("B") + col)
                text_updates.append({
                    "range": f"{col_letter_str}{score_row}",
                    "values": [[round(score, 1)]],
                })
                bg, fg = _cal_color(score)
                for target_row in (day_num_row - 1, score_row - 1):
                    fmt_requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": cal_sid,
                                "startRowIndex": target_row,
                                "endRowIndex": target_row + 1,
                                "startColumnIndex": col + 1,
                                "endColumnIndex": col + 2,
                            },
                            "cell": {"userEnteredFormat": {
                                "backgroundColorStyle": {"rgbColor": bg},
                                "textFormat": {"foregroundColorStyle": {"rgbColor": fg}},
                            }},
                            "fields": "userEnteredFormat.backgroundColorStyle,userEnteredFormat.textFormat.foregroundColorStyle",
                        }
                    })
            day += 1

    if text_updates:
        cal_ws.batch_update(text_updates, value_input_option="RAW")
    if fmt_requests:
        spreadsheet.batch_update({"requests": fmt_requests})
    print(f"  Updated {len(text_updates)} day(s) with scores and colors")


def main():
    today = date.today()
    year, month = today.year, today.month
    month_label = f"{calendar.month_name[month]} {year}"

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Food Tracker sync starting...")

    spreadsheet = get_spreadsheet(year, month)
    if not spreadsheet:
        print(f"No sheet registered for {month_label}.")
        print(f"Create a blank Google Sheet, share it with the SA, then run:")
        print(f"  python upload_template.py <sheet_url> {year} {month}")
        print(f"  python add_formulas.py <sheet_url>")
        print(f"  python format_sheet.py <sheet_url>")
        sys.exit(1)

    sheet_id = get_sheet_id(year, month)
    print(f"Working on: {month_label} (ID: {sheet_id})")

    print("\n--- Food Log ---")
    fill_food_log(spreadsheet)

    print("\n--- Exercise Log ---")
    fill_exercise_log(spreadsheet)

    print("\n--- Calendar ---")
    fill_calendar(spreadsheet, year, month)

    # On the 1st, check if next month is registered and warn if not
    if today.day == 1:
        next_month = month % 12 + 1
        next_year = year + (1 if next_month == 1 else 0)
        next_label = f"{calendar.month_name[next_month]} {next_year}"
        if not get_sheet_id(next_year, next_month):
            print(f"\n*** REMINDER: No sheet registered for {next_label}. ***")
            print(f"    Create a blank Google Sheet, share with SA, then run:")
            print(f"    python upload_template.py <sheet_url> {next_year} {next_month}")
            print(f"    python add_formulas.py <sheet_url>")
            print(f"    python format_sheet.py <sheet_url>")

    print(f"\n[{datetime.now():%Y-%m-%d %H:%M}] Done.")


if __name__ == "__main__":
    main()
