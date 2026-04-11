from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from parse_dish import (
    DEFAULT_NUTRITION_DB,
    add_nutrition as _add_nutrition,
    parse_dish as _parse_dish,
    per_person as _per_person,
)


# Multi-user data storage: keyed by username
all_user_data = {}

# Global fasting data - kept as-is for now, can be made per-user later
fasting_data = {
    "current_fast": {
        "start_time": None,
        "is_active": False,
        "target_hours": None,
        "target_seconds": None,
    },
    "history": [],
}


def _get_or_create_user_data(username: str) -> dict:
    """Get or create user data dictionary for a given username."""
    if username not in all_user_data:
        all_user_data[username] = {
            "weight_log": [],
            "steps_log": [],
            "calories_log": [],
            "meal_log": [],
            "nutrition_log": [],
            "custom_dishes": [],
            "profile": {
                "name": "",
                "height_cm": None,
                "height_feet": None,
                "height_inches": None,
                "is_registered": False,
            },
        }
    return all_user_data[username]


# Backward compatibility: provide default user_data
user_data = _get_or_create_user_data("default")


def parse_dish(file_path: str) -> list[dict[str, Any]]:
    return _parse_dish(file_path)


def calculate_per_person(dish: dict[str, Any]) -> dict[str, Any]:
    return _per_person(dish)


def calculate_nutrition(
    dish: dict[str, Any], nutrition_db: dict[str, dict[str, float]] | None = None
) -> dict[str, Any]:
    return _add_nutrition(dish, nutrition_db or DEFAULT_NUTRITION_DB)


def track_weight(date: str, weight: float) -> dict[str, Any]:
    entry = {"date": date, "weight": weight}
    user_data["weight_log"].append(entry)
    return entry


def track_steps(date: str, steps: int) -> dict[str, Any]:
    calories_lost = calculate_calories_burned(steps)
    entry = {"date": date, "steps": steps, "calories_lost": calories_lost}
    user_data["steps_log"].append(entry)
    return entry


def calculate_calories_burned(steps: int, calories_per_step: float = 0.04) -> float:
    return round(steps * calories_per_step, 2)


def start_fast(target_hours: int = 16) -> None:
    if fasting_data["current_fast"]["is_active"]:
        print("Fast already active")
        return

    target_hours = max(1, int(target_hours))

    fasting_data["current_fast"]["start_time"] = datetime.now()
    fasting_data["current_fast"]["is_active"] = True
    fasting_data["current_fast"]["target_hours"] = target_hours
    fasting_data["current_fast"]["target_seconds"] = target_hours * 3600
    print("Fasting started")


def end_fast() -> None:
    if not fasting_data["current_fast"]["is_active"]:
        print("No active fast")
        return

    start = fasting_data["current_fast"]["start_time"]
    end = datetime.now()
    duration = (end - start).total_seconds() / 3600
    target_hours = fasting_data["current_fast"].get("target_hours")
    target_seconds = fasting_data["current_fast"].get("target_seconds")
    if not target_seconds and target_hours:
        target_seconds = int(target_hours * 3600)

    completion_percent = None
    if target_seconds:
        completion_percent = round(min(100.0, (duration * 3600 / target_seconds) * 100), 2)

    fasting_data["history"].append(
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "duration_hours": round(duration, 2),
            "target_hours": target_hours,
            "completion_percent": completion_percent,
        }
    )

    fasting_data["current_fast"]["start_time"] = None
    fasting_data["current_fast"]["is_active"] = False
    fasting_data["current_fast"]["target_hours"] = None
    fasting_data["current_fast"]["target_seconds"] = None
    print(f"Fast ended. Duration: {duration:.2f} hours")


def get_fasting_duration() -> float:
    if not fasting_data["current_fast"]["is_active"]:
        return 0.0

    start = fasting_data["current_fast"]["start_time"]
    duration = (datetime.now() - start).total_seconds() / 3600
    return round(duration, 2)


def get_fasting_progress() -> dict[str, float | int]:
    if not fasting_data["current_fast"].get("is_active"):
        return {
            "elapsed_seconds": 0,
            "remaining_seconds": 0,
            "target_seconds": 0,
            "completion_percent": 0,
        }

    start = fasting_data["current_fast"].get("start_time")
    if start is None:
        return {
            "elapsed_seconds": 0,
            "remaining_seconds": 0,
            "target_seconds": 0,
            "completion_percent": 0,
        }

    elapsed_seconds = max(0, int((datetime.now() - start).total_seconds()))
    target_seconds = fasting_data["current_fast"].get("target_seconds") or 0
    remaining_seconds = max(0, int(target_seconds) - elapsed_seconds) if target_seconds else 0

    completion_percent = 0
    if target_seconds:
        completion_percent = min(100, round((elapsed_seconds / target_seconds) * 100, 2))

    return {
        "elapsed_seconds": elapsed_seconds,
        "remaining_seconds": remaining_seconds,
        "target_seconds": int(target_seconds),
        "completion_percent": completion_percent,
    }


def _merge_progress_logs() -> pd.DataFrame:
    df_w = pd.DataFrame(user_data["weight_log"])
    df_s = pd.DataFrame(user_data["steps_log"])
    df_c = pd.DataFrame(user_data["calories_log"])

    frames = [df for df in (df_w, df_s, df_c) if not df.empty]
    if not frames:
        return pd.DataFrame(columns=["date", "weight", "steps", "calories", "calories_lost"])

    merged = frames[0]
    for other in frames[1:]:
        merged = pd.merge(merged, other, on="date", how="outer")

    merged["date"] = pd.to_datetime(merged["date"])
    return merged.sort_values("date")


def _build_insights(progress_df: pd.DataFrame) -> list[str]:
    insights: list[str] = []
    if progress_df.empty or "weight" not in progress_df:
        return ["Not enough weight data to generate insights."]

    weight_values = progress_df["weight"].dropna()
    if weight_values.empty:
        return ["Not enough weight data to generate insights."]

    weight_change = round(float(weight_values.iloc[-1]) - float(weight_values.iloc[0]), 2)
    if weight_change < 0:
        insights.append(f"Weight decreased by {abs(weight_change)} kg over the logged period.")
    elif weight_change > 0:
        insights.append(f"Weight increased by {weight_change} kg over the logged period.")
    else:
        insights.append("Weight stayed the same over the logged period.")

    if "steps" in progress_df:
        avg_steps = progress_df["steps"].dropna()
        if not avg_steps.empty:
            avg_value = round(float(avg_steps.mean()), 2)
            if avg_value >= 8000:
                insights.append(f"Average daily steps are {avg_value}, which is fairly active.")
            else:
                insights.append(f"Average daily steps are {avg_value}; increasing steps may help fat loss.")

    if {"calories", "calories_lost"}.issubset(progress_df.columns):
        calories = progress_df["calories"].dropna()
        burned = progress_df["calories_lost"].dropna()
        if not calories.empty and not burned.empty:
            net = round(float(calories.mean()) - float(burned.mean()), 2)
            insights.append(f"Estimated average net calories after walking are {net}.")

    if {"weight", "calories"}.issubset(progress_df.columns):
        weight = progress_df["weight"]
        calories = progress_df["calories"]
        if weight.notna().sum() > 1 and calories.notna().sum() > 1:
            corr = round(weight.corr(calories), 3)
            insights.append(f"Weight/calorie correlation is {corr}.")

    return insights


def plot_progress() -> pd.DataFrame:
    progress_df = _merge_progress_logs()
    if progress_df.empty:
        raise ValueError("No progress data available to plot.")

    fig, ax1 = plt.subplots(figsize=(10, 5))

    if "weight" in progress_df:
        ax1.plot(progress_df["date"], progress_df["weight"], color="blue", marker="o")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Weight (kg)", color="blue")
    ax1.tick_params(axis="y", labelcolor="blue")

    ax2 = ax1.twinx()
    if "calories" in progress_df:
        ax2.plot(progress_df["date"], progress_df["calories"], color="red", marker="s")
    if "calories_lost" in progress_df:
        ax2.plot(
            progress_df["date"],
            progress_df["calories_lost"],
            color="green",
            marker="^",
            linestyle="--",
        )
    ax2.set_ylabel("Calories", color="red")
    ax2.tick_params(axis="y", labelcolor="red")

    plt.title("Weight, Calories, and Calories Burned Over Time")
    fig.tight_layout()
    plt.show()
    return progress_df


def _input_with_default(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def _ask_yes_no(prompt: str, default: str = "n") -> bool:
    value = input(f"{prompt} [{default}]: ").strip().lower()
    value = value or default.lower()
    return value in {"y", "yes"}


def main() -> None:
    print("Step 1: Choose dish file")
    dish_file = _input_with_default("Enter dish CSV file path", "dishes.csv")
    if not Path(dish_file).exists():
        print(f"File not found: {dish_file}")
        return

    dishes = parse_dish(dish_file)
    print(f"Parsed {len(dishes)} dishes")
    if not dishes:
        print("No dishes found in the selected file.")
        return

    print("\nStep 2: Calculate per-person ingredients for the first dish")
    first_dish = calculate_per_person(dishes[0])
    print(json.dumps(first_dish, indent=2))

    print("\nStep 3: Calculate nutrition for the first dish")
    first_dish_with_nutrition = calculate_nutrition(first_dish)
    print(json.dumps(first_dish_with_nutrition["nutrition_per_person"], indent=2))

    print("\nStep 4: Enter weight")
    weight_date = _input_with_default("Enter weight date (YYYY-MM-DD)", datetime.now().date().isoformat())
    weight_value = float(_input_with_default("Enter weight in kg", "78"))
    track_weight(weight_date, weight_value)
    print(json.dumps(user_data["weight_log"], indent=2))

    print("\nStep 5: Enter steps")
    steps_date = _input_with_default("Enter steps date (YYYY-MM-DD)", weight_date)
    steps_value = int(_input_with_default("Enter steps", "5000"))
    track_steps(steps_date, steps_value)
    print(json.dumps(user_data["steps_log"], indent=2))

    print("\nStep 6: Enter calories")
    calories_date = _input_with_default("Enter calories date (YYYY-MM-DD)", weight_date)
    calories_value = float(_input_with_default("Enter calories eaten", "2200"))
    user_data["calories_log"].append({"date": calories_date, "calories": calories_value})
    print(json.dumps(user_data["calories_log"], indent=2))

    print("\nStep 7: Start or stop fasting")
    if _ask_yes_no("Start fasting? y/n", "n"):
        start_fast()
        print(f"Current fasting duration: {get_fasting_duration()} hours")
    if _ask_yes_no("Stop fasting now? y/n", "n"):
        end_fast()
    print(json.dumps(fasting_data, indent=2))

    print("\nStep 8: Generate progress insights")
    progress_df = _merge_progress_logs()
    insights = _build_insights(progress_df)
    print(json.dumps(insights, indent=2))

    if _ask_yes_no("\nStep 9: Plot progress? y/n", "y"):
        plot_progress()


if __name__ == "__main__":
    main()
