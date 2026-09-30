"""Nutrition and exercise estimation via Google Gemini API."""

import json
import re
import time
import requests
from config import GEMINI_API_KEY_FILE, GEMINI_MODEL

_api_key = None


def _get_api_key() -> str:
    global _api_key
    if _api_key is None:
        _api_key = GEMINI_API_KEY_FILE.read_text().strip()
    return _api_key


def _query_gemini(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    for attempt in range(3):
        resp = requests.post(
            url,
            params={"key": _get_api_key()},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        if resp.status_code == 503 and attempt < 2:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def estimate_food_nutrition(food_item: str, meal_type: str) -> dict | None:
    """Return {"protein": g, "carbs": g, "fibre": g, "fat": g, "vitamins": 1-5, "calories": kcal} or None."""
    prompt = (
        f"Estimate the nutritional content for one typical serving of this {meal_type.lower()} food item: \"{food_item}\".\n"
        "Respond ONLY with a JSON object, no explanation:\n"
        '{"protein": <grams>, "carbs": <grams>, "fibre": <grams>, "fat": <grams>, "vitamins": <1-5 score>, "calories": <kcal>}\n'
        "Vitamins score: 1 = no fruit/veg, 3 = some, 5 = very vitamin-rich.\n"
        "Use realistic values for Indian/home-cooked portions where applicable."
    )
    try:
        raw = _query_gemini(prompt)
        match = re.search(r"\{[^}]+\}", raw)
        if not match:
            return None
        data = json.loads(match.group())
        return {
            "protein": round(float(data["protein"])),
            "carbs": round(float(data["carbs"])),
            "fibre": round(float(data["fibre"])),
            "fat": round(float(data["fat"])),
            "vitamins": max(1, min(5, round(float(data["vitamins"])))),
            "calories": round(float(data["calories"])),
        }
    except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"  [estimator] Failed for '{food_item}': {e}")
        return None


def estimate_exercise_calories(exercise: str, duration_min: int, intensity: str) -> int | None:
    """Return estimated calories burned or None."""
    prompt = (
        f"Estimate calories burned for this exercise: \"{exercise}\", duration {duration_min} minutes, intensity {intensity}.\n"
        "Assume a person weighing ~70 kg.\n"
        "Respond ONLY with a single integer (kcal), no explanation."
    )
    try:
        raw = _query_gemini(prompt)
        match = re.search(r"\d+", raw)
        if not match:
            return None
        return int(match.group())
    except (requests.RequestException, ValueError) as e:
        print(f"  [estimator] Failed for '{exercise}': {e}")
        return None
