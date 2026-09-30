#!/usr/bin/env python3
"""Inject all formulas into the Food Tracker Google Sheet."""

import re
import sys

import gspread
from google.oauth2.service_account import Credentials

from config import SERVICE_ACCOUNT_JSON

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = None


def _extract_sheet_id(arg):
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", arg)
    return m.group(1) if m else arg.strip()


def get_gc():
    creds = Credentials.from_service_account_file(str(SERVICE_ACCOUNT_JSON), scopes=SCOPES)
    return gspread.authorize(creds)


def add_dashboard_formulas(spreadsheet):
    ws = spreadsheet.worksheet("Dashboard")
    updates = []

    # KPI row 5 (values with units)
    updates.append({"range": "B5", "values": [['=COUNTIF(\'Dashboard Data\'!K7:K37,">"&0)']]})
    updates.append({"range": "D5", "values": [['=IFERROR(ROUND(AVERAGEIF(\'Dashboard Data\'!D7:D37,">"&0),1)&" / 5","-")']]})
    updates.append({"range": "F5", "values": [['=IFERROR(ROUND(AVERAGEIF(\'Dashboard Data\'!E7:E37,">"&0))&"g","-")']]})
    updates.append({"range": "H5", "values": [['=IFERROR(ROUND(AVERAGEIF(\'Dashboard Data\'!J7:J37,">"&0))&" kcal","-")']]})
    updates.append({"range": "J5", "values": [['=IFERROR(ROUND(AVERAGEIF(\'Dashboard Data\'!G7:G37,">"&0))&"g","-")']]})
    updates.append({"range": "L5", "values": [['=IF(\'Weight Log\'!C9="","-",\'Weight Log\'!C9&" kg")']]})

    # Weight Goal section (B9:C11)
    updates.append({"range": "B9", "values": [["Initial"]]})
    updates.append({"range": "C9", "values": [["='Weight Log'!C6&\" kg\""]]})
    updates.append({"range": "B10", "values": [["Target"]]})
    updates.append({"range": "C10", "values": [["='Weight Log'!C7&\" kg\""]]})
    updates.append({"range": "B11", "values": [["Current"]]})
    updates.append({"range": "C11", "values": [['=IF(\'Weight Log\'!C9="","-",\'Weight Log\'!C9&" kg")']]})

    # Nutrition vs Ideal rows (E10:H14) — data rows are 79-83 in Dashboard Data
    # Rows 79-82 are grams, row 83 is kcal
    for i, src_row in enumerate(range(79, 83)):
        row = 10 + i
        updates.append({"range": f"E{row}", "values": [[f"='Dashboard Data'!C{src_row}"]]})
        updates.append({"range": f"F{row}", "values": [[f"=ROUND('Dashboard Data'!D{src_row})&\"g\""]]})
        updates.append({"range": f"G{row}", "values": [[f"='Dashboard Data'!E{src_row}&\"g\""]]})
        updates.append({"range": f"H{row}", "values": [[f"='Dashboard Data'!F{src_row}&\"%\""]]})
    # Calories row
    updates.append({"range": "E14", "values": [["='Dashboard Data'!C83"]]})
    updates.append({"range": "F14", "values": [["=ROUND('Dashboard Data'!D83)&\" kcal\""]]})
    updates.append({"range": "G14", "values": [["='Dashboard Data'!E83&\" kcal\""]]})
    updates.append({"range": "H14", "values": [["='Dashboard Data'!F83&\"%\""]]})

    # Exercise section (J9:K12)
    updates.append({"range": "J9", "values": [["Avg Cal In / Day"]]})
    updates.append({"range": "K9", "values": [['=IFERROR(ROUND(AVERAGEIF(\'Dashboard Data\'!J7:J37,">"&0)),"-")']]})
    updates.append({"range": "J10", "values": [["Avg Cal Out / Day"]]})
    updates.append({"range": "K10", "values": [['=IFERROR(ROUND(AVERAGEIF(\'Dashboard Data\'!D42:D72,">"&0)),"-")']]})
    updates.append({"range": "J11", "values": [["Avg Steps / Day"]]})
    updates.append({"range": "K11", "values": [['=IFERROR(ROUND(AVERAGEIF(\'Dashboard Data\'!F42:F72,">"&0)),"-")']]})
    updates.append({"range": "J12", "values": [["Active Days"]]})
    updates.append({"range": "K12", "values": [['=COUNTIF(\'Dashboard Data\'!D42:D72,">"&0)']]})

    ws.batch_update(updates, value_input_option="USER_ENTERED")
    print(f"  Dashboard: {len(updates)} formula cells")


def add_dashboard_data_formulas(spreadsheet):
    ws = spreadsheet.worksheet("Dashboard Data")
    updates = []

    # Table 1: Daily Nutrition Summary (rows 7-37, cols D-K)
    for row in range(7, 38):
        updates.append({"range": f"D{row}", "values": [[f"=IFERROR(AVERAGEIF('Food Log'!$B$8:$B$200,C{row},'Food Log'!$E$8:$E$200),0)"]]})
        updates.append({"range": f"E{row}", "values": [[f"=SUMIF('Food Log'!$B$8:$B$200,C{row},'Food Log'!$F$8:$F$200)"]]})
        updates.append({"range": f"F{row}", "values": [[f"=SUMIF('Food Log'!$B$8:$B$200,C{row},'Food Log'!$G$8:$G$200)"]]})
        updates.append({"range": f"G{row}", "values": [[f"=SUMIF('Food Log'!$B$8:$B$200,C{row},'Food Log'!$H$8:$H$200)"]]})
        updates.append({"range": f"H{row}", "values": [[f"=SUMIF('Food Log'!$B$8:$B$200,C{row},'Food Log'!$I$8:$I$200)"]]})
        updates.append({"range": f"I{row}", "values": [[f"=IFERROR(AVERAGEIF('Food Log'!$B$8:$B$200,C{row},'Food Log'!$J$8:$J$200),0)"]]})
        updates.append({"range": f"J{row}", "values": [[f"=SUMIF('Food Log'!$B$8:$B$200,C{row},'Food Log'!$K$8:$K$200)"]]})
        updates.append({"range": f"K{row}", "values": [[f"=COUNTIF('Food Log'!$B$8:$B$200,C{row})"]]})

    # Table 2: Daily Exercise Summary (rows 42-72, cols D-G)
    for row in range(42, 73):
        updates.append({"range": f"D{row}", "values": [[f"=SUMIF('Exercise Log'!$B$6:$B$100,C{row},'Exercise Log'!$F$6:$F$100)"]]})
        updates.append({"range": f"E{row}", "values": [[f"=SUMIF('Exercise Log'!$B$6:$B$100,C{row},'Exercise Log'!$D$6:$D$100)"]]})
        updates.append({"range": f"F{row}", "values": [[f"=SUMIF('Exercise Log'!$B$6:$B$100,C{row},'Exercise Log'!$G$6:$G$100)"]]})
        updates.append({"range": f"G{row}", "values": [[f"=COUNTIF('Exercise Log'!$B$6:$B$100,C{row})"]]})

    # Table 3: Nutrition vs Ideal (rows 79-83, data rows below header at 78)
    src_cols = ["E", "F", "G", "H", "J"]  # Protein, Carbs, Fibre, Fat, Calories
    for i, (row, col) in enumerate(zip(range(79, 84), src_cols)):
        updates.append({"range": f"D{row}", "values": [[f'=IFERROR(AVERAGEIF({col}7:{col}37,">"&0),0)']]})
        updates.append({"range": f"F{row}", "values": [[f"=IFERROR(ROUND(D{row}/E{row}*100),0)"]]})

    # Table 4: Meal Healthiness Distribution (rows 85-87)
    updates.append({"range": "D85", "values": [['=COUNTIFS(\'Food Log\'!$E$8:$E$200,">="&4)']]})
    updates.append({"range": "D86", "values": [['=COUNTIFS(\'Food Log\'!$E$8:$E$200,">="&3,\'Food Log\'!$E$8:$E$200,"<"&4)']]})
    updates.append({"range": "D87", "values": [['=COUNTIFS(\'Food Log\'!$E$8:$E$200,">="&1,\'Food Log\'!$E$8:$E$200,"<"&3)']]})

    # Table 5: Daily Calorie Intake (rows 92-122)
    for day in range(1, 32):
        row = 91 + day
        nutr_row = 6 + day    # J column in nutrition table
        ex_row = 41 + day     # D column in exercise table
        updates.append({"range": f"C{row}", "values": [[f"=J{nutr_row}"]]})
        updates.append({"range": f"D{row}", "values": [[f"=D{ex_row}"]]})
        updates.append({"range": f"E{row}", "values": [[f"=C{row}-D{row}"]]})

    # Table 6: Weight Progress (rows 127-146)
    for i in range(20):
        wl_row = 15 + i
        row = 127 + i
        updates.append({"range": f"B{row}", "values": [[f"='Weight Log'!B{wl_row}"]]})
        updates.append({"range": f"C{row}", "values": [[f"='Weight Log'!C{wl_row}"]]})
        updates.append({"range": f"D{row}", "values": [[f"='Weight Log'!C7"]]})

    ws.batch_update(updates, value_input_option="USER_ENTERED")
    print(f"  Dashboard Data: {len(updates)} formula cells")


def add_weight_log_formulas(spreadsheet):
    ws = spreadsheet.worksheet("Weight Log")
    updates = []

    # Current weight = last entry (C18 in template, but dynamic — use MAX row with data)
    updates.append({"range": "C9", "values": [["=IFERROR(INDEX(C15:C49,MATCH(2,1/(C15:C49<>\"\"),1)),\"\")"]]})
    updates.append({"range": "C10", "values": [["=IF(C9=\"\",\"\",C9-C6)"]]})
    updates.append({"range": "C11", "values": [["=IF(C7-C6=0,0,(C9-C6)/(C7-C6))"]]})

    # BMI and Change for weight entries (rows 15-49)
    updates.append({"range": "E15", "values": [["=IF(C15=\"\",\"\",C15/(1.68*1.68))"]]})
    for row in range(16, 50):
        updates.append({"range": f"D{row}", "values": [[f"=IF(C{row}=\"\",\"\",C{row}-C{row-1})"]]})
        updates.append({"range": f"E{row}", "values": [[f"=IF(C{row}=\"\",\"\",C{row}/(1.68*1.68))"]]})

    ws.batch_update(updates, value_input_option="USER_ENTERED")
    print(f"  Weight Log: {len(updates)} formula cells")


def main():
    if len(sys.argv) < 2:
        print("Usage: python add_formulas.py <sheet_url_or_id>")
        sys.exit(1)

    sheet_id = _extract_sheet_id(sys.argv[1])
    gc = get_gc()
    spreadsheet = gc.open_by_key(sheet_id)

    print("Adding formulas...")
    add_dashboard_data_formulas(spreadsheet)
    add_weight_log_formulas(spreadsheet)
    add_dashboard_formulas(spreadsheet)

    print(f"\nDone! All formulas injected.")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{sheet_id}")


if __name__ == "__main__":
    main()
