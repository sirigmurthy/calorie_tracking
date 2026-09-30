#!/usr/bin/env python3
"""Apply formatting to a Food Tracker Google Sheet to match the .xlsx template."""

import re
import sys

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from config import SERVICE_ACCOUNT_JSON

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Color palette (RGB 0-1)
C = {
    "dark": {"red": 0.10, "green": 0.12, "blue": 0.17},       # 1A202C
    "gray_text": {"red": 0.44, "green": 0.50, "blue": 0.59},   # 718096
    "gray_dark": {"red": 0.18, "green": 0.22, "blue": 0.28},   # 2D3748
    "white": {"red": 1, "green": 1, "blue": 1},
    "off_white": {"red": 0.97, "green": 0.98, "blue": 0.99},   # F7FAFC
    "blue_light": {"red": 0.92, "green": 0.97, "blue": 1.0},   # EBF8FF
    "green_bg": {"red": 0.94, "green": 1.0, "blue": 0.96},     # F0FFF4
    "purple_bg": {"red": 0.92, "green": 0.96, "blue": 1.0},    # EBF4FF
    "cal_green": {"red": 0.78, "green": 0.96, "blue": 0.84},   # C6F6D5
    "cal_yellow": {"red": 1.0, "green": 0.99, "blue": 0.75},   # FEFCBF
    "cal_red": {"red": 1.0, "green": 0.84, "blue": 0.84},      # FED7D7
    "cal_gray": {"red": 0.93, "green": 0.95, "blue": 0.97},    # EDF2F7
    "green_text": {"red": 0.15, "green": 0.40, "blue": 0.29},  # 276749
    "yellow_text": {"red": 0.59, "green": 0.35, "blue": 0.09}, # 975A16
    "red_text": {"red": 0.61, "green": 0.17, "blue": 0.17},    # 9B2C2C
    "light_gray_text": {"red": 0.63, "green": 0.68, "blue": 0.72},  # A0AEC0
}

THIN_BOTTOM = {"bottom": {"style": "SOLID", "color": {"red": 0.85, "green": 0.85, "blue": 0.85}}}


def _rgb(color_dict):
    return {**color_dict}


def _cell_fmt(bg=None, fg=None, bold=False, size=10, halign="CENTER", valign="MIDDLE",
              wrap=None, borders=None, number_format=None):
    fmt = {
        "textFormat": {"bold": bold, "fontSize": size},
        "horizontalAlignment": halign,
        "verticalAlignment": valign,
    }
    if fg:
        fmt["textFormat"]["foregroundColorStyle"] = {"rgbColor": _rgb(fg)}
    if bg:
        fmt["backgroundColorStyle"] = {"rgbColor": _rgb(bg)}
    if wrap:
        fmt["wrapStrategy"] = wrap
    if borders:
        fmt["borders"] = borders
    if number_format:
        fmt["numberFormat"] = number_format
    return fmt


def _repeat_cell(sheet_id, r1, r2, c1, c2, fmt, fields):
    return {
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": r1, "endRowIndex": r2,
                       "startColumnIndex": c1, "endColumnIndex": c2},
            "cell": {"userEnteredFormat": fmt},
            "fields": f"userEnteredFormat({fields})",
        }
    }


def _merge(sheet_id, r1, r2, c1, c2, merge_type="MERGE_ALL"):
    return {
        "mergeCells": {
            "range": {"sheetId": sheet_id, "startRowIndex": r1, "endRowIndex": r2,
                       "startColumnIndex": c1, "endColumnIndex": c2},
            "mergeType": merge_type,
        }
    }


def _col_width(sheet_id, col, px):
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                      "startIndex": col, "endIndex": col + 1},
            "properties": {"pixelSize": px},
            "fields": "pixelSize",
        }
    }


def _row_height(sheet_id, row, px):
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "ROWS",
                      "startIndex": row, "endIndex": row + 1},
            "properties": {"pixelSize": px},
            "fields": "pixelSize",
        }
    }


def _extract_sheet_id(arg):
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", arg)
    return m.group(1) if m else arg.strip()


def get_sheet_ids(service, spreadsheet_id):
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}


def format_dashboard(sid):
    reqs = []
    # Col A narrow spacer
    reqs.append(_col_width(sid, 0, 20))
    reqs.append(_col_width(sid, 1, 100))

    # Title row 2 (idx 1): bold 18pt
    reqs.append(_merge(sid, 1, 2, 1, 13))
    reqs.append(_repeat_cell(sid, 1, 2, 1, 13,
        {"textFormat": {"bold": True, "fontSize": 18, "foregroundColorStyle": {"rgbColor": C["dark"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))
    reqs.append(_row_height(sid, 1, 40))

    # Subtitle row 3 (idx 2)
    reqs.append(_merge(sid, 2, 3, 1, 13))
    reqs.append(_repeat_cell(sid, 2, 3, 1, 13,
        {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_text"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))

    # KPI values row 5 (idx 4): big bold numbers, green bg
    reqs.append(_row_height(sid, 4, 46))
    for c1, c2 in [(1,3),(3,5),(5,7),(7,9),(9,11),(11,13)]:
        reqs.append(_merge(sid, 4, 5, c1, c2))
    reqs.append(_repeat_cell(sid, 4, 5, 1, 13,
        {"textFormat": {"bold": True, "fontSize": 18, "foregroundColorStyle": {"rgbColor": C["dark"]}},
         "backgroundColorStyle": {"rgbColor": C["green_bg"]},
         "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"},
        "textFormat,backgroundColorStyle,horizontalAlignment,verticalAlignment"))

    # KPI labels row 6 (idx 5)
    for c1, c2 in [(1,3),(3,5),(5,7),(7,9),(9,11),(11,13)]:
        reqs.append(_merge(sid, 5, 6, c1, c2))
    reqs.append(_repeat_cell(sid, 5, 6, 1, 13,
        {"textFormat": {"fontSize": 9, "foregroundColorStyle": {"rgbColor": C["gray_text"]}},
         "backgroundColorStyle": {"rgbColor": C["green_bg"]},
         "horizontalAlignment": "CENTER"},
        "textFormat,backgroundColorStyle,horizontalAlignment"))

    # Section headers row 8 (idx 7): bold 13pt
    reqs.append(_repeat_cell(sid, 7, 8, 1, 13,
        {"textFormat": {"bold": True, "fontSize": 13, "foregroundColorStyle": {"rgbColor": C["dark"]}}},
        "textFormat"))

    # Nutrition vs Ideal header row (E9-H9, idx 8): dark bg, white text
    reqs.append(_repeat_cell(sid, 8, 9, 4, 8,
        {"textFormat": {"bold": True, "fontSize": 10, "foregroundColorStyle": {"rgbColor": C["white"]}},
         "backgroundColorStyle": {"rgbColor": C["gray_dark"]},
         "horizontalAlignment": "CENTER"},
        "textFormat,backgroundColorStyle,horizontalAlignment"))

    # Nutrition data rows (E10-H14, idx 9-13): alternating white/off-white, centered, thin border
    for r in range(9, 14):
        bg = C["white"] if r % 2 == 0 else C["off_white"]
        reqs.append(_repeat_cell(sid, r, r+1, 4, 8,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": bg},
             "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,borders"))

    # Weight Goal section (B9-C13): labels + values
    for r in range(8, 13):
        bg = C["white"] if r % 2 == 0 else C["off_white"]
        reqs.append(_repeat_cell(sid, r, r+1, 1, 3,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": bg},
             "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,borders"))

    # Exercise section (J9-K12): labels + values
    for r in range(8, 12):
        reqs.append(_repeat_cell(sid, r, r+1, 9, 11,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "horizontalAlignment": "LEFT"},
            "textFormat,horizontalAlignment"))

    return reqs


def format_food_log(sid):
    reqs = []
    reqs.append(_col_width(sid, 0, 20))   # A
    reqs.append(_col_width(sid, 1, 110))   # B date
    reqs.append(_col_width(sid, 2, 100))   # C meal
    reqs.append(_col_width(sid, 3, 250))   # D food item
    reqs.append(_col_width(sid, 4, 100))   # E healthiness
    reqs.append(_col_width(sid, 5, 85))    # F protein
    reqs.append(_col_width(sid, 6, 85))    # G carbs
    reqs.append(_col_width(sid, 7, 85))    # H fibre
    reqs.append(_col_width(sid, 8, 85))    # I fat
    reqs.append(_col_width(sid, 9, 90))    # J vitamins
    reqs.append(_col_width(sid, 10, 90))   # K calories
    reqs.append(_col_width(sid, 11, 200))  # L notes

    # Title
    reqs.append(_merge(sid, 1, 2, 1, 12))
    reqs.append(_repeat_cell(sid, 1, 2, 1, 12,
        {"textFormat": {"bold": True, "fontSize": 16, "foregroundColorStyle": {"rgbColor": C["dark"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))
    reqs.append(_row_height(sid, 1, 26))

    # Subtitle
    reqs.append(_merge(sid, 2, 3, 1, 12))
    reqs.append(_repeat_cell(sid, 2, 3, 1, 12,
        {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_text"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))

    # Scale legend row 5
    reqs.append(_merge(sid, 4, 5, 1, 12))
    reqs.append(_repeat_cell(sid, 4, 5, 1, 12,
        {"textFormat": {"fontSize": 9, "foregroundColorStyle": {"rgbColor": C["gray_text"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))

    # Header row 7 (idx 6): dark bg, white bold
    reqs.append(_row_height(sid, 6, 36))
    reqs.append(_repeat_cell(sid, 6, 7, 1, 12,
        {"textFormat": {"bold": True, "fontSize": 11, "foregroundColorStyle": {"rgbColor": C["white"]}},
         "backgroundColorStyle": {"rgbColor": C["gray_dark"]},
         "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
         "wrapStrategy": "WRAP", "borders": THIN_BOTTOM},
        "textFormat,backgroundColorStyle,horizontalAlignment,verticalAlignment,wrapStrategy,borders"))

    # Data rows 8-199 (idx 7-198): user-input cols (B-D) blue, rest white/off-white alternating
    for r in range(7, 199):
        even = (r % 2 == 0)
        # B-D: light blue (user fills)
        reqs.append(_repeat_cell(sid, r, r+1, 1, 4,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": C["blue_light"]},
             "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,borders"))
        # E-K: white/off-white (cron fills)
        bg = C["white"] if even else C["off_white"]
        reqs.append(_repeat_cell(sid, r, r+1, 4, 11,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": bg},
             "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,borders"))
        # L: notes, blue
        reqs.append(_repeat_cell(sid, r, r+1, 11, 12,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": C["blue_light"]},
             "horizontalAlignment": "LEFT", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,borders"))

    return reqs


def format_exercise_log(sid):
    reqs = []
    reqs.append(_col_width(sid, 0, 20))
    reqs.append(_col_width(sid, 1, 110))   # B date
    reqs.append(_col_width(sid, 2, 210))   # C exercise
    reqs.append(_col_width(sid, 3, 100))   # D duration
    reqs.append(_col_width(sid, 4, 120))   # E intensity
    reqs.append(_col_width(sid, 5, 100))   # F calories
    reqs.append(_col_width(sid, 6, 85))    # G steps
    reqs.append(_col_width(sid, 7, 210))   # H notes

    # Title
    reqs.append(_merge(sid, 1, 2, 1, 8))
    reqs.append(_repeat_cell(sid, 1, 2, 1, 8,
        {"textFormat": {"bold": True, "fontSize": 16, "foregroundColorStyle": {"rgbColor": C["dark"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))
    reqs.append(_row_height(sid, 1, 26))

    # Subtitle
    reqs.append(_merge(sid, 2, 3, 1, 8))
    reqs.append(_repeat_cell(sid, 2, 3, 1, 8,
        {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_text"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))

    # Note row 4
    reqs.append(_merge(sid, 3, 4, 1, 8))
    reqs.append(_repeat_cell(sid, 3, 4, 1, 8,
        {"textFormat": {"fontSize": 8, "foregroundColorStyle": {"rgbColor": C["gray_text"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))

    # Header row 5 (idx 4)
    reqs.append(_row_height(sid, 4, 50))
    reqs.append(_repeat_cell(sid, 4, 5, 1, 8,
        {"textFormat": {"bold": True, "fontSize": 11, "foregroundColorStyle": {"rgbColor": C["white"]}},
         "backgroundColorStyle": {"rgbColor": C["gray_dark"]},
         "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
         "wrapStrategy": "WRAP", "borders": THIN_BOTTOM},
        "textFormat,backgroundColorStyle,horizontalAlignment,verticalAlignment,wrapStrategy,borders"))

    # Data rows 6-99 (idx 5-98): blue for user cols, white for cron col F
    for r in range(5, 99):
        # B-E, G-H: blue (user fills)
        reqs.append(_repeat_cell(sid, r, r+1, 1, 5,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": C["blue_light"]},
             "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,borders"))
        # F: white (cron fills)
        reqs.append(_repeat_cell(sid, r, r+1, 5, 6,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": C["white"]},
             "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,borders"))
        # G-H: blue
        reqs.append(_repeat_cell(sid, r, r+1, 6, 8,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": C["blue_light"]},
             "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,borders"))

    return reqs


def format_weight_log(sid):
    reqs = []
    reqs.append(_col_width(sid, 0, 20))
    reqs.append(_col_width(sid, 1, 135))
    reqs.append(_col_width(sid, 2, 115))
    reqs.append(_col_width(sid, 3, 100))
    reqs.append(_col_width(sid, 4, 85))

    # Title
    reqs.append(_merge(sid, 1, 2, 1, 5))
    reqs.append(_repeat_cell(sid, 1, 2, 1, 5,
        {"textFormat": {"bold": True, "fontSize": 16, "foregroundColorStyle": {"rgbColor": C["dark"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))
    reqs.append(_row_height(sid, 1, 26))

    # Subtitle
    reqs.append(_merge(sid, 2, 3, 1, 5))
    reqs.append(_repeat_cell(sid, 2, 3, 1, 5,
        {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_text"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))

    # Goal section rows 5-12 (idx 4-11): purple/blue bg for labels
    for r in range(4, 12):
        reqs.append(_repeat_cell(sid, r, r+1, 1, 2,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": C["purple_bg"]}},
            "textFormat,backgroundColorStyle"))
        reqs.append(_repeat_cell(sid, r, r+1, 2, 4,
            {"textFormat": {"bold": True, "fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": C["blue_light"]}},
            "textFormat,backgroundColorStyle"))

    # Height note row 12
    reqs.append(_repeat_cell(sid, 11, 12, 1, 5,
        {"textFormat": {"fontSize": 8, "foregroundColorStyle": {"rgbColor": C["light_gray_text"]}},
         "backgroundColorStyle": {"rgbColor": C["white"]}},
        "textFormat,backgroundColorStyle"))

    # Header row 14 (idx 13)
    reqs.append(_repeat_cell(sid, 13, 14, 1, 5,
        {"textFormat": {"bold": True, "fontSize": 11, "foregroundColorStyle": {"rgbColor": C["white"]}},
         "backgroundColorStyle": {"rgbColor": C["gray_dark"]},
         "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
        "textFormat,backgroundColorStyle,horizontalAlignment,borders"))

    # Data rows 15+ (idx 14+): alternating
    for r in range(14, 49):
        bg = C["blue_light"] if r % 2 == 0 else C["white"]
        reqs.append(_repeat_cell(sid, r, r+1, 1, 3,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": bg},
             "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,borders"))
        reqs.append(_repeat_cell(sid, r, r+1, 3, 5,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": C["white"]},
             "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,borders"))

    return reqs


def format_calendar(sid):
    reqs = []
    reqs.append(_col_width(sid, 0, 20))
    for col in range(1, 8):
        reqs.append(_col_width(sid, col, 115))

    # Title
    reqs.append(_merge(sid, 1, 2, 1, 8))
    reqs.append(_repeat_cell(sid, 1, 2, 1, 8,
        {"textFormat": {"bold": True, "fontSize": 16, "foregroundColorStyle": {"rgbColor": C["dark"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))
    reqs.append(_row_height(sid, 1, 26))

    # Subtitle
    reqs.append(_merge(sid, 2, 3, 1, 8))
    reqs.append(_repeat_cell(sid, 2, 3, 1, 8,
        {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_text"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))

    # Legend row 5 (idx 4): colored badges
    reqs.append(_repeat_cell(sid, 4, 5, 1, 2,
        {"textFormat": {"bold": True, "fontSize": 9, "foregroundColorStyle": {"rgbColor": C["green_text"]}},
         "backgroundColorStyle": {"rgbColor": C["cal_green"]},
         "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
        "textFormat,backgroundColorStyle,horizontalAlignment,borders"))
    reqs.append(_repeat_cell(sid, 4, 5, 3, 4,
        {"textFormat": {"bold": True, "fontSize": 9, "foregroundColorStyle": {"rgbColor": C["yellow_text"]}},
         "backgroundColorStyle": {"rgbColor": C["cal_yellow"]},
         "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
        "textFormat,backgroundColorStyle,horizontalAlignment,borders"))
    reqs.append(_repeat_cell(sid, 4, 5, 5, 6,
        {"textFormat": {"bold": True, "fontSize": 9, "foregroundColorStyle": {"rgbColor": C["red_text"]}},
         "backgroundColorStyle": {"rgbColor": C["cal_red"]},
         "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
        "textFormat,backgroundColorStyle,horizontalAlignment,borders"))
    reqs.append(_repeat_cell(sid, 4, 5, 7, 8,
        {"textFormat": {"fontSize": 9, "foregroundColorStyle": {"rgbColor": C["gray_text"]}},
         "backgroundColorStyle": {"rgbColor": C["cal_gray"]},
         "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
        "textFormat,backgroundColorStyle,horizontalAlignment,borders"))

    # Day-of-week header row 7 (idx 6)
    reqs.append(_repeat_cell(sid, 6, 7, 1, 8,
        {"textFormat": {"bold": True, "fontSize": 11, "foregroundColorStyle": {"rgbColor": C["white"]}},
         "backgroundColorStyle": {"rgbColor": C["gray_dark"]},
         "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
        "textFormat,backgroundColorStyle,horizontalAlignment,borders"))

    # Calendar grid: day number rows (bold 12pt) + score rows (9pt) + spacer rows
    for week_start in range(7, 22, 3):  # idx 7,10,13,16,19
        day_row = week_start
        score_row = week_start + 1
        spacer_row = week_start + 2
        reqs.append(_row_height(sid, day_row, 37))
        reqs.append(_row_height(sid, score_row, 24))
        if spacer_row < 22:
            reqs.append(_row_height(sid, spacer_row, 5))

        # Default: gray "no data" for all calendar cells
        reqs.append(_repeat_cell(sid, day_row, day_row+1, 1, 8,
            {"textFormat": {"bold": True, "fontSize": 12, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": C["cal_gray"]},
             "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,verticalAlignment,borders"))
        reqs.append(_repeat_cell(sid, score_row, score_row+1, 1, 8,
            {"textFormat": {"fontSize": 9, "foregroundColorStyle": {"rgbColor": C["light_gray_text"]}},
             "backgroundColorStyle": {"rgbColor": C["cal_gray"]},
             "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,borders"))

    return reqs


def _fmt_section_title(sid, row_idx, col_end=9):
    """Bold section title (e.g. 'Daily Nutrition Summary')."""
    return _repeat_cell(sid, row_idx, row_idx + 1, 1, col_end,
        {"textFormat": {"bold": True, "fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}}},
        "textFormat")


def _fmt_header_row(sid, row_idx, col_end, height=36):
    """Dark bg, white bold header row."""
    reqs = [_row_height(sid, row_idx, height)]
    reqs.append(_repeat_cell(sid, row_idx, row_idx + 1, 1, col_end,
        {"textFormat": {"bold": True, "fontSize": 11, "foregroundColorStyle": {"rgbColor": C["white"]}},
         "backgroundColorStyle": {"rgbColor": C["gray_dark"]},
         "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
         "wrapStrategy": "WRAP", "borders": THIN_BOTTOM},
        "textFormat,backgroundColorStyle,horizontalAlignment,verticalAlignment,wrapStrategy,borders"))
    return reqs


def _fmt_data_rows(sid, start_idx, end_idx, col_end):
    """Alternating white/off-white data rows."""
    reqs = []
    for r in range(start_idx, end_idx):
        bg = C["white"] if r % 2 == 0 else C["off_white"]
        reqs.append(_repeat_cell(sid, r, r + 1, 1, col_end,
            {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_dark"]}},
             "backgroundColorStyle": {"rgbColor": bg},
             "horizontalAlignment": "CENTER", "borders": THIN_BOTTOM},
            "textFormat,backgroundColorStyle,horizontalAlignment,borders"))
    return reqs


def format_dashboard_data(sid):
    reqs = []
    reqs.append(_col_width(sid, 0, 20))
    reqs.append(_col_width(sid, 1, 35))    # B: day#
    reqs.append(_col_width(sid, 2, 110))   # C: date
    for col in range(3, 10):
        reqs.append(_col_width(sid, col, 100))

    # Title row 2 (idx 1)
    reqs.append(_merge(sid, 1, 2, 1, 9))
    reqs.append(_repeat_cell(sid, 1, 2, 1, 9,
        {"textFormat": {"bold": True, "fontSize": 16, "foregroundColorStyle": {"rgbColor": C["dark"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))
    reqs.append(_row_height(sid, 1, 26))

    # Subtitle row 3 (idx 2)
    reqs.append(_merge(sid, 2, 3, 1, 9))
    reqs.append(_repeat_cell(sid, 2, 3, 1, 9,
        {"textFormat": {"fontSize": 10, "foregroundColorStyle": {"rgbColor": C["gray_text"]}},
         "horizontalAlignment": "LEFT"},
        "textFormat,horizontalAlignment"))

    # --- Table 1: Daily Nutrition Summary (rows 5-37, idx 4-36) ---
    reqs.append(_fmt_section_title(sid, 4))          # row 5
    reqs.extend(_fmt_header_row(sid, 5, 10))          # row 6
    reqs.extend(_fmt_data_rows(sid, 6, 37, 10))       # rows 7-37

    # --- Table 2: Daily Exercise Summary (rows 41-73, idx 40-72) ---
    reqs.append(_fmt_section_title(sid, 40, 6))       # row 41
    reqs.extend(_fmt_header_row(sid, 41, 6))           # row 42
    reqs.extend(_fmt_data_rows(sid, 42, 73, 6))        # rows 43-73

    # --- Table 3: Nutrition vs Ideal (rows 77-83, idx 76-82) ---
    reqs.append(_fmt_section_title(sid, 76, 5))       # row 77
    reqs.extend(_fmt_header_row(sid, 77, 5))           # row 78
    reqs.extend(_fmt_data_rows(sid, 78, 83, 5))        # rows 79-83

    # --- Table 4: Meal Healthiness Distribution (rows 85-89, idx 84-88) ---
    reqs.append(_fmt_section_title(sid, 84, 3))       # row 85
    reqs.extend(_fmt_header_row(sid, 85, 3))           # row 86
    reqs.extend(_fmt_data_rows(sid, 86, 89, 3))        # rows 87-89

    # --- Table 5: Daily Calorie Intake (rows 92-124, idx 91-123) ---
    reqs.append(_fmt_section_title(sid, 91, 5))       # row 92
    reqs.extend(_fmt_header_row(sid, 92, 5))           # row 93
    reqs.extend(_fmt_data_rows(sid, 93, 124, 5))       # rows 94-124

    # --- Table 6: Weight Progress (rows 128-129, idx 127-128) ---
    reqs.append(_fmt_section_title(sid, 127, 4))      # row 128
    reqs.extend(_fmt_header_row(sid, 128, 4))          # row 129

    return reqs


def main():
    if len(sys.argv) < 2:
        print("Usage: python format_sheet.py <sheet_url_or_id>")
        sys.exit(1)

    spreadsheet_id = _extract_sheet_id(sys.argv[1])

    creds = Credentials.from_service_account_file(str(SERVICE_ACCOUNT_JSON), scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)

    sheet_ids = get_sheet_ids(service, spreadsheet_id)
    print(f"Found tabs: {list(sheet_ids.keys())}")

    all_requests = []

    if "Dashboard" in sheet_ids:
        print("  Formatting Dashboard...")
        all_requests.extend(format_dashboard(sheet_ids["Dashboard"]))

    if "Food Log" in sheet_ids:
        print("  Formatting Food Log...")
        all_requests.extend(format_food_log(sheet_ids["Food Log"]))

    if "Exercise Log" in sheet_ids:
        print("  Formatting Exercise Log...")
        all_requests.extend(format_exercise_log(sheet_ids["Exercise Log"]))

    if "Weight Log" in sheet_ids:
        print("  Formatting Weight Log...")
        all_requests.extend(format_weight_log(sheet_ids["Weight Log"]))

    if "Calendar" in sheet_ids:
        print("  Formatting Calendar...")
        all_requests.extend(format_calendar(sheet_ids["Calendar"]))

    if "Dashboard Data" in sheet_ids:
        print("  Formatting Dashboard Data...")
        all_requests.extend(format_dashboard_data(sheet_ids["Dashboard Data"]))

    # Send in batches (API limit ~100k requests, but we batch for safety)
    batch_size = 500
    for i in range(0, len(all_requests), batch_size):
        batch = all_requests[i:i+batch_size]
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": batch},
        ).execute()
        print(f"  Applied batch {i//batch_size + 1} ({len(batch)} requests)")

    print(f"\nFormatting complete! ({len(all_requests)} total requests)")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")


if __name__ == "__main__":
    main()
