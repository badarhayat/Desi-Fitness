from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


EXCLUDED_ITEMS = {
    "bulab mess",
    "gas",
    "gas cylinder",
    "gas lpg",
    "knor",
    "mandi",
    "rent",
    "saban",
    "saban bartan",
    "saban hand",
    "saraf bonas",
    "saraf bunas",
    "store",
    "tissue",
    "wood",
}

LIQUID_ITEMS = {
    "oil",
    "sirka",
    "ketchup",
    "soya sauce",
}

MASALA_KEYWORDS = ("masala",)
MASALA_EXCEPTIONS = {"garm masala"}
REMOVED_DISH_RECORDS = {("chicken karhai", "54")}
ATTA_ITEM_NAMES = {"atta"}
COUNT_BASED_ITEMS = {"egg"}
SABZ_DHANIA_ITEM_NAMES = {"sabz dhania"}

DEFAULT_NUTRITION_DB = {
    "aaloo": {"calories": 77, "protein": 2.0, "carbs": 17.0, "fat": 0.1},
    "achaar": {"calories": 25, "protein": 0.5, "carbs": 5.0, "fat": 0.2},
    "achar": {"calories": 25, "protein": 0.5, "carbs": 5.0, "fat": 0.2},
    "atta": {"calories": 364, "protein": 10.3, "carbs": 76.3, "fat": 1.0},
    "band gobhi": {"calories": 25, "protein": 1.3, "carbs": 5.8, "fat": 0.1},
    "band gobi": {"calories": 25, "protein": 1.3, "carbs": 5.8, "fat": 0.1},
    "biryani masala": {"calories": 300, "protein": 10, "carbs": 45, "fat": 8},
    "chanay": {"calories": 164, "protein": 8.9, "carbs": 27.4, "fat": 2.6},
    "chicken": {"calories": 239, "protein": 27, "carbs": 0, "fat": 14},
    "chicken qema": {"calories": 250, "protein": 26, "carbs": 0, "fat": 17},
    "dahi": {"calories": 61, "protein": 3.5, "carbs": 4.7, "fat": 3.3},
    "dara chli": {"calories": 282, "protein": 12, "carbs": 50, "fat": 14},
    "dara mirch": {"calories": 282, "protein": 12, "carbs": 50, "fat": 14},
    "egg": {"calories": 72, "protein": 6.3, "carbs": 0.4, "fat": 4.8},
    "gajar": {"calories": 41, "protein": 0.9, "carbs": 10, "fat": 0.2},
    "garm masala": {"calories": 375, "protein": 12, "carbs": 58, "fat": 15},
    "haldai": {"calories": 312, "protein": 9.7, "carbs": 67, "fat": 3.3},
    "haldi": {"calories": 312, "protein": 9.7, "carbs": 67, "fat": 3.3},
    "haleem masala": {"calories": 320, "protein": 12, "carbs": 50, "fat": 8},
    "imli": {"calories": 239, "protein": 2.8, "carbs": 62.5, "fat": 0.6},
    "karahi masala": {"calories": 320, "protein": 10, "carbs": 50, "fat": 8},
    "kasuri methe": {"calories": 323, "protein": 23, "carbs": 58, "fat": 6.4},
    "ketchup": {"calories": 112, "protein": 1.3, "carbs": 27.4, "fat": 0.2},
    "kheeray": {"calories": 15, "protein": 0.7, "carbs": 3.6, "fat": 0.1},
    "lemon": {"calories": 29, "protein": 1.1, "carbs": 9.3, "fat": 0.3},
    "mahthi": {"calories": 323, "protein": 23, "carbs": 58, "fat": 6.4},
    "masoor mong": {"calories": 347, "protein": 24, "carbs": 63, "fat": 1.2},
    "mathi": {"calories": 323, "protein": 23, "carbs": 58, "fat": 6.4},
    "milk": {"calories": 61, "protein": 3.2, "carbs": 4.8, "fat": 3.3},
    "pakorian": {"calories": 280, "protein": 6, "carbs": 28, "fat": 16},
    "pissa dhania": {"calories": 298, "protein": 12.4, "carbs": 55, "fat": 17.8},
    "podina": {"calories": 44, "protein": 3.3, "carbs": 8.4, "fat": 0.7},
    "red chilli": {"calories": 318, "protein": 12, "carbs": 57, "fat": 17},
    "rice": {"calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3},
    "sabat dhania": {"calories": 298, "protein": 12.4, "carbs": 55, "fat": 17.8},
    "sabz dhania": {"calories": 23, "protein": 2.1, "carbs": 3.7, "fat": 0.5},
    "sabz mirch": {"calories": 40, "protein": 2, "carbs": 9, "fat": 0.2},
    "salt": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
    "shamla": {"calories": 20, "protein": 0.9, "carbs": 4.6, "fat": 0.2},
    "shmalia": {"calories": 20, "protein": 0.9, "carbs": 4.6, "fat": 0.2},
    "sirka": {"calories": 21, "protein": 0, "carbs": 0.9, "fat": 0},
    "soya sauce": {"calories": 53, "protein": 8.1, "carbs": 4.9, "fat": 0.6},
    "sugar": {"calories": 387, "protein": 0, "carbs": 100, "fat": 0},
    "tea": {"calories": 1, "protein": 0, "carbs": 0.2, "fat": 0},
    "thoom adrak": {"calories": 80, "protein": 3.2, "carbs": 17, "fat": 0.6},
    "zarda rang": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
    "zeera": {"calories": 375, "protein": 18, "carbs": 44, "fat": 22},
    "oil": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100},
    "daal": {"calories": 116, "protein": 9, "carbs": 20, "fat": 0.4},
    "piyaaz": {"calories": 40, "protein": 1.1, "carbs": 9, "fat": 0.1},
    "tamatar": {"calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2},
}


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\ufeff", "").split()).strip()


def _is_dish_header(value: Any) -> bool:
    return _normalize(value).lower() == "dish"


def _is_persons_header(value: Any) -> bool:
    return _normalize(value).lower() == "number of persons"


def _is_end_marker(value: Any) -> bool:
    return _normalize(value).lower() in {"", "total"}


def _should_skip_item(value: Any) -> bool:
    lowered = _normalize(value).lower()
    return lowered in {"", "item", "quantity", "total"} or lowered in EXCLUDED_ITEMS


def _infer_unit(item_name: str) -> str:
    if item_name.lower() in COUNT_BASED_ITEMS:
        return "pieces"
    return "litres" if item_name.lower() in LIQUID_ITEMS else "kilograms"


def _normalize_quantity_and_unit(item_name: str, quantity: str) -> tuple[float, str]:
    lowered = item_name.lower()
    if lowered in SABZ_DHANIA_ITEM_NAMES:
        return round(float(quantity) * 0.02, 6), "kilograms"
    if any(keyword in lowered for keyword in MASALA_KEYWORDS) and lowered not in MASALA_EXCEPTIONS:
        return 0.05, "kilograms"
    return float(quantity), _infer_unit(item_name)


def _nutrition_factor(ingredient: dict[str, Any]) -> float:
    if ingredient["unit"] == "pieces":
        return ingredient["quantity"]
    return ingredient["quantity"] * 10


def _merge_or_add_ingredient(dish: dict[str, Any], ingredient: str, quantity: float, unit: str) -> None:
    """Merge duplicate ingredients by summing quantity so nutrition is not undercounted."""
    for existing in dish["ingredients"]:
        if existing["name"].lower() == ingredient.lower() and existing["unit"] == unit:
            existing["quantity"] = round(existing["quantity"] + quantity, 6)
            return

    dish["ingredients"].append(
        {
            "name": ingredient,
            "quantity": quantity,
            "unit": unit,
        }
    )


def parse_dish(file_path: str) -> list[dict[str, Any]]:
    """
    Read a CSV file and extract dish name, persons, and structured ingredients.

    Expected repeated block format:
    Item | quantity | Dish | Number of persons
    """
    with open(file_path, "r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))

    if not rows:
        return []

    max_cols = max(len(row) for row in rows)
    active_blocks: dict[int, dict[str, Any]] = {}
    dishes_by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for row in rows:
        padded = row + [""] * (max_cols - len(row))

        for col_idx, cell in enumerate(padded):
            if not _is_dish_header(cell):
                continue
            if col_idx + 1 >= max_cols or not _is_persons_header(padded[col_idx + 1]):
                continue

            active_blocks[col_idx] = {
                "ingredient_col": max(col_idx - 2, 0),
                "quantity_col": max(col_idx - 1, 0),
                "dish_name": "",
                "persons": "",
            }

        for col_idx, block in active_blocks.items():
            if col_idx + 1 >= max_cols:
                continue

            dish_name = _normalize(padded[col_idx])
            persons = _normalize(padded[col_idx + 1])

            if dish_name and not _is_dish_header(dish_name):
                block["dish_name"] = dish_name
                block["persons"] = persons

            if not block["dish_name"]:
                continue

            ingredient = _normalize(padded[block["ingredient_col"]])
            quantity = _normalize(padded[block["quantity_col"]])

            if _should_skip_item(ingredient) or not quantity or _is_end_marker(ingredient):
                continue

            key = (block["dish_name"], block["persons"])
            dish = dishes_by_key.setdefault(
                key,
                {
                    "dish_name": block["dish_name"],
                    "persons": int(float(block["persons"])) if block["persons"] else 0,
                    "ingredients": [],
                    "supports_rotis": False,
                },
            )

            if ingredient.lower() in ATTA_ITEM_NAMES:
                # Atta is intentionally excluded from fixed dish nutrition;
                # users can add roti count separately on the Analyze page.
                dish["supports_rotis"] = True
                continue

            normalized_quantity, unit = _normalize_quantity_and_unit(ingredient, quantity)
            _merge_or_add_ingredient(dish, ingredient, normalized_quantity, unit)

    result = []
    for (dish_name, persons), dish in dishes_by_key.items():
        if (dish_name.lower(), persons) in REMOVED_DISH_RECORDS:
            continue
        result.append(dish)

    return result


def per_person(dish: dict[str, Any]) -> dict[str, Any]:
    persons = dish["persons"]
    if not persons:
        return dish

    for ingredient in dish["ingredients"]:
        ingredient["per_person_qty"] = round(ingredient["quantity"] / persons, 6)

    return dish


def add_nutrition(
    dish: dict[str, Any], nutrition_db: dict[str, dict[str, float]] | None = None
) -> dict[str, Any]:
    """
    Add nutrition to each ingredient and total dish nutrition.

    Assumption:
    nutrition_db values are per 100 grams for kilograms and per 100 ml for litres.
    """
    db = nutrition_db or DEFAULT_NUTRITION_DB
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    missing_nutrition_items: list[str] = []

    for ingredient in dish["ingredients"]:
        name_key = ingredient["name"].lower()
        nutrition = db.get(name_key)
        if not nutrition:
            ingredient["nutrition"] = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
            missing_nutrition_items.append(ingredient["name"])
            continue

        amount_per_100 = _nutrition_factor(ingredient)
        ingredient_totals = {
            "calories": round(nutrition["calories"] * amount_per_100, 2),
            "protein": round(nutrition["protein"] * amount_per_100, 2),
            "carbs": round(nutrition["carbs"] * amount_per_100, 2),
            "fat": round(nutrition["fat"] * amount_per_100, 2),
        }
        ingredient["nutrition"] = ingredient_totals

        for key in totals:
            totals[key] += ingredient_totals[key]

    dish["nutrition_totals"] = {key: round(value, 2) for key, value in totals.items()}
    if missing_nutrition_items:
        dish["missing_nutrition_items"] = sorted(set(missing_nutrition_items))
    elif "missing_nutrition_items" in dish:
        del dish["missing_nutrition_items"]

    if dish.get("persons"):
        persons = dish["persons"]
        dish["nutrition_per_person"] = {
            key: round(value / persons, 2) for key, value in dish["nutrition_totals"].items()
        }

    return dish


def parse_all_dishes_with_nutrition(
    file_path: str, nutrition_db: dict[str, dict[str, float]] | None = None
) -> list[dict[str, Any]]:
    dishes = parse_dish(file_path)
    return [add_nutrition(per_person(dish), nutrition_db) for dish in dishes]


if __name__ == "__main__":
    sample_file = Path("dishes.csv")
    if sample_file.exists():
        print(json.dumps(parse_dish(str(sample_file)), indent=2))
