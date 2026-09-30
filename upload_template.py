#!/usr/bin/env python3
"""Populate a blank Google Sheet with the Food Tracker template for a given month.

Workflow:
  1. Create a blank Google Sheet in your Drive folder (manually or via this script)
  2. Share it with the service account as Editor
  3. Run: python upload_template.py <sheet_url_or_id> [year] [month]

If no year/month given, defaults to current month.

Examples:
    python upload_template.py https://docs.google.com/spreadsheets/d/1abc.../edit
    python upload_template.py 1abc... 2026 11
"""

import calendar
import re
import sys
from datetime import date

import gspread
from google.oauth2.service_account import Credentials

from config import SERVICE_ACCOUNT_JSON, SPREADSHEET_NAME_FMT
from sheet_registry import register

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def sheet_name_for(year: int, month: int) -> str:
    return SPREADSHEET_NAME_FMT.format(month=calendar.month_name[month], year=year)


def _days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _date_str(year: int, month: int, day: int) -> str:
    return f"{year}-{month:02d}-{day:02d}"


def _first_weekday(year: int, month: int) -> int:
    """Sun=0..Sat=6 for the 1st of the month."""
    dow = calendar.weekday(year, month, 1)  # 0=Mon
    return (dow + 1) % 7


def _extract_sheet_id(arg: str) -> str:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", arg)
    if m:
        return m.group(1)
    return arg.strip()


def populate(sheet_id: str, year: int, month: int):
    if not SERVICE_ACCOUNT_JSON.exists():
        print(f"Service account key not found at {SERVICE_ACCOUNT_JSON}")
        sys.exit(1)

    creds = Credentials.from_service_account_file(str(SERVICE_ACCOUNT_JSON), scopes=SCOPES)
    gc = gspread.authorize(creds)

    title = sheet_name_for(year, month)
    month_name = calendar.month_name[month]
    days = _days_in_month(year, month)

    print(f"Opening sheet {sheet_id}...")
    spreadsheet = gc.open_by_key(sheet_id)

    # Rename the spreadsheet
    spreadsheet.update_title(title)

    # Remove all existing worksheets except the first
    existing_ws = spreadsheet.worksheets()
    keep = existing_ws[0]

    print("  Building Dashboard...")
    keep.update_title("Dashboard")
    keep.resize(rows=50, cols=13)
    _build_dashboard(keep, year, month, month_name)

    print("  Building Food Log...")
    ws = spreadsheet.add_worksheet("Food Log", rows=200, cols=12)
    _build_food_log(ws, month_name, year)

    print("  Building Exercise Log...")
    ws = spreadsheet.add_worksheet("Exercise Log", rows=100, cols=8)
    _build_exercise_log(ws, month_name, year)

    print("  Building Weight Log...")
    ws = spreadsheet.add_worksheet("Weight Log", rows=50, cols=5)
    _build_weight_log(ws, year, month, month_name)

    print("  Building Calendar...")
    ws = spreadsheet.add_worksheet("Calendar", rows=22, cols=9)
    _build_calendar(ws, year, month, month_name, days)

    print("  Building Dashboard Data...")
    ws = spreadsheet.add_worksheet("Dashboard Data", rows=146, cols=11)
    _build_dashboard_data(ws, year, month, days)

    # Remove leftover worksheets from the original blank
    for old_ws in existing_ws[1:]:
        try:
            spreadsheet.del_worksheet(old_ws)
        except Exception:
            pass

    register(year, month, sheet_id)

    print(f"\nDone: {title}")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    print(f"  Registered in sheets.json as {year}-{month:02d}")


def _build_dashboard(ws, year, month, month_name):
    ws.update(values=[[f"Food & Fitness Dashboard — {month_name} {year}"]], range_name="B2")
    ws.update(values=[["Overview of nutrition, exercise, and weight progress. Data sourced from Food Log, Exercise Log, and Weight Log tabs."]], range_name="B3")
    ws.update(values=[["Days Logged", "", "Avg Health Score", "", "Avg Protein/day", "", "Avg Calories/day", "", "Avg Fibre/day", "", "Current Weight"]], range_name="B6")
    ws.update("B8", [
        ["Weight Goal", "", "", "Nutrition vs Ideal", "", "", "", "", "Exercise This Month"],
        ["Initial", "", "", "Nutrient", "Yours", "Ideal", "% Met", "", "Avg Cal In / Day"],
        ["Target", "", "", "", "", "", "", "", "Avg Cal Out / Day"],
        ["Current", "", "", "", "", "", "", "", "Avg Steps / Day"],
        ["", "", "", "", "", "", "", "", "Active Days"],
    ])


def _build_food_log(ws, month_name, year):
    ws.update(values=[[f"Food Log — {month_name} {year}"]], range_name="B2")
    ws.update(values=[["Log every meal below. The cron job will estimate Protein, Carbs, Fibre, Vitamins, and Calories from the Food Item."]], range_name="B3")
    ws.update(values=[["Healthiness (1-5): 1 = Junk/fried · 2 = Mostly unhealthy · 3 = Mixed/okay · 4 = Mostly healthy · 5 = Very healthy/home-cooked    |    Vitamins (1-5): 1 = No fruit/veg · 3 = Some · 5 = Very vitamin-rich"]], range_name="B5")
    ws.update(values=[["Date", "Meal", "Food Item", "Healthiness\n(1-5)", "Protein\n(g)", "Carbs\n(g)", "Fibre\n(g)", "Fat\n(g)", "Vitamins\n(1-5)", "Calories\n(kcal)", "Notes"]], range_name="B7")


def _build_exercise_log(ws, month_name, year):
    ws.update(values=[[f"Exercise Log — {month_name} {year}"]], range_name="B2")
    ws.update(values=[["Log your exercises. Calories burned will be estimated by the cron job based on exercise type and duration."]], range_name="B3")
    ws.update(values=[["* Calories Burned is estimated by the cron job based on exercise type, duration, and intensity. Blue cells = you fill, white cells = cron fills."]], range_name="B4")
    ws.update(values=[["Date", "Exercise", "Duration\n(min)", "Intensity\n(Low/Med/High)", "Calories\nBurned *", "Steps", "Notes"]], range_name="B5")

    ws.add_validation(
        "E6:E99",
        gspread.worksheet.ValidationConditionType.one_of_list,
        ["Low", "Med", "High"],
        strict=True,
        showCustomUi=True,
    )


def _build_weight_log(ws, year, month, month_name):
    last_day = _days_in_month(year, month)
    ws.update(values=[[f"Weight Log — {month_name} {year}"]], range_name="B2")
    ws.update(values=[["Record your weight whenever you weigh in. Feeds the weight chart and goal tracker."]], range_name="B3")
    ws.update("B5", [
        ["Goal", "Weight Loss"],
        ["Start Weight (kg)", 70],
        ["Target Weight (kg)", 65],
        ["Target Date", f"{year}-{month:02d}-{last_day:02d}"],
        ["Current Weight"],
        ["Change"],
        ["Progress"],
        ["Height assumed: 1.72m for BMI calc"],
    ])
    ws.update(values=[["Date", "Weight (kg)", "Change", "BMI"]], range_name="B14")


def _build_calendar(ws, year, month, month_name, days):
    ws.update(values=[[f"Health Calendar — {month_name} {year}"]], range_name="B2")
    ws.update(values=[["Each day is color-coded by average healthiness score from the Food Log."]], range_name="B3")
    ws.update(values=[["Healthy (4-5)", "", "Mixed (2.5-3.9)", "", "Unhealthy (<2.5)", "", "No data"]], range_name="B5")
    ws.update(values=[["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]], range_name="B7")

    first_dow = _first_weekday(year, month)
    day = 1
    for week_row in range(8, 22, 3):
        day_row = [""] * 7
        score_row = [""] * 7
        for col in range(7):
            if (week_row == 8 and col < first_dow) or day > days:
                continue
            day_row[col] = day
            score_row[col] = "-"
            day += 1
        ws.update(values=[day_row], range_name=f"B{week_row}")
        ws.update(values=[score_row], range_name=f"B{week_row + 1}")
        if day > days:
            break


def _build_dashboard_data(ws, year, month, days):
    ws.update(values=[["Dashboard Data (Auto-calculated)"]], range_name="B2")
    ws.update(values=[["This tab is populated by formulas. Do not edit manually."]], range_name="B3")

    # Daily Nutrition Summary
    ws.update(values=[["Daily Nutrition Summary"]], range_name="B5")
    ws.update("B6", [["Date", "Avg Health\nScore", "Total\nProtein (g)", "Total\nCarbs (g)",
                       "Total\nFibre (g)", "Total\nFat (g)", "Avg Vitamin\nScore", "Total\nCalories", "Meals\nCount"]])
    nutrition_rows = [[d, _date_str(year, month, d)] for d in range(1, days + 1)]
    ws.update("B7", nutrition_rows)

    # Daily Exercise Summary
    ex_start = 7 + days + 3
    ws.update(values=[["Daily Exercise Summary"]], range_name=f"B{ex_start}")
    ws.update(values=[["Date", "Total Cal\nBurned", "Total\nDuration (min)", "Total\nSteps", "Sessions"]], range_name=f"B{ex_start + 1}")
    exercise_rows = [[d, _date_str(year, month, d)] for d in range(1, days + 1)]
    ws.update(f"B{ex_start + 2}", exercise_rows)

    # Nutrition vs Ideal
    nvi_start = ex_start + 2 + days + 3
    ws.update(values=[["Nutrition vs Ideal (Monthly Avg)"]], range_name=f"B{nvi_start}")
    ws.update(values=[["Nutrient", "Your Avg\n(per day)", "Ideal\n(per day)", "% of Ideal"]], range_name=f"B{nvi_start + 1}")
    ws.update(f"B{nvi_start + 2}", [
        [1, "Protein (g)", "", 65],
        [2, "Carbs (g)", "", 225],
        [3, "Fibre (g)", "", 25],
        [4, "Fat (g)", "", 50],
        [5, "Calories (kcal)", "", 1800],
    ])

    # Meal Healthiness Distribution
    mhd_start = nvi_start + 8
    ws.update(values=[["Meal Healthiness Distribution"]], range_name=f"B{mhd_start}")
    ws.update(values=[["Band", "Meal Count"]], range_name=f"B{mhd_start + 1}")
    ws.update(values=[["Healthy (4-5)"], ["Mixed (3-3.9)"], ["Unhealthy (1-2.9)"]], range_name=f"C{mhd_start + 2}")

    # Daily Calorie Intake chart data
    cal_start = mhd_start + 7
    ws.update(values=[["Daily Calorie Intake (Chart Data)"]], range_name=f"B{cal_start}")
    ws.update(values=[["Day", "Calories In", "Calories Out", "Net"]], range_name=f"B{cal_start + 1}")
    cal_rows = [[d] for d in range(1, days + 1)]
    ws.update(f"B{cal_start + 2}", cal_rows)

    # Weight Progress chart data
    wt_start = cal_start + 2 + days + 3
    ws.update(values=[["Weight Progress (Chart Data)"]], range_name=f"B{wt_start}")
    ws.update(values=[["Date", "Weight", "Target"]], range_name=f"B{wt_start + 1}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_template.py <sheet_url_or_id> [year] [month]")
        print()
        print("Steps:")
        print("  1. Create a blank Google Sheet in your Drive folder")
        print("  2. Share it with: spend-tracker-sheets@groovy-plating-467305-r7.iam.gserviceaccount.com (Editor)")
        print("  3. Run this script with the sheet URL or ID")
        sys.exit(1)

    sheet_id = _extract_sheet_id(sys.argv[1])

    if len(sys.argv) >= 4:
        year, month = int(sys.argv[2]), int(sys.argv[3])
    else:
        today = date.today()
        year, month = today.year, today.month

    populate(sheet_id, year, month)


if __name__ == "__main__":
    main()
