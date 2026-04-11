import csv
import json
from pathlib import Path


INPUT_FILE = Path("dishes.csv")
OUTPUT_JSON = Path("extracted_dishes_corrected.json")
OUTPUT_CSV = Path("extracted_dishes_corrected.csv")

EXCLUDED_INGREDIENTS = {
    "atta",
    "bulab mess",
    "gas cylinder",
    "gas lpg",
    "knor",
    "mandi",
    "milk",
    "rent",
    "saban",
    "saban bartan",
    "saban hand",
    "saraf bonas",
    "saraf bunas",
    "store",
    "sugar",
    "tea",
    "tissue",
    "wood",
}

LIQUID_INGREDIENTS = {
    "oil",
    "sirka",
    "ketchup",
    "soya sauce",
}

MASALA_KEYWORDS = ("masala",)
MASALA_EXCEPTIONS = {"garm masala"}
REMOVED_DISH_RECORDS = {("chicken karhai", "54")}


def normalize(value: str) -> str:
    return " ".join((value or "").replace("\ufeff", "").split()).strip()


def is_header_cell(value: str) -> bool:
    lowered = normalize(value).lower()
    return lowered in {"item", "quantity", "dish", "dish ", "number of persons", "number of persons "}


def is_end_marker(value: str) -> bool:
    lowered = normalize(value).lower()
    return lowered in {"", "total"}


def infer_unit(ingredient: str) -> str:
    return "litres" if ingredient.lower() in LIQUID_INGREDIENTS else "kilograms"


def normalize_quantity_and_unit(ingredient: str, quantity: str) -> tuple[str, str]:
    lowered = ingredient.lower()
    if any(keyword in lowered for keyword in MASALA_KEYWORDS) and lowered not in MASALA_EXCEPTIONS:
        return "0.05", "kilograms"
    return quantity, infer_unit(ingredient)


def append_ingredient(bucket: list[dict], ingredient: str, quantity: str) -> None:
    cleaned = normalize(ingredient)
    cleaned_quantity = normalize(quantity)
    if not cleaned:
        return
    if is_header_cell(cleaned) or is_end_marker(cleaned):
        return
    if cleaned.lower() in EXCLUDED_INGREDIENTS:
        return
    if not cleaned_quantity:
        return
    normalized_quantity, unit = normalize_quantity_and_unit(cleaned, cleaned_quantity)
    for item in bucket:
        if item["ingredient"].lower() == cleaned.lower():
            return
    bucket.append(
        {
            "ingredient": cleaned,
            "quantity": normalized_quantity,
            "unit": unit,
        }
    )


def extract_dishes(rows: list[list[str]]) -> list[dict]:
    if not rows:
        return []

    max_cols = max(len(row) for row in rows)
    dishes: list[dict] = []
    active_blocks: dict[int, dict] = {}

    for row in rows:
        padded = row + [""] * (max_cols - len(row))

        for col_idx, cell in enumerate(padded):
            cell_value = normalize(cell)
            if cell_value.lower() != "dish":
                continue

            if col_idx + 1 >= max_cols:
                continue

            persons_header = normalize(padded[col_idx + 1]).lower()
            if persons_header != "number of persons":
                continue

            ingredient_col = max(col_idx - 2, 0)
            quantity_col = max(col_idx - 1, 0)
            active_blocks[col_idx] = {
                "dish_name": "",
                "persons": "",
                "ingredient_col": ingredient_col,
                "quantity_col": quantity_col,
                "ingredients": [],
            }

        for col_idx, block in list(active_blocks.items()):
            if col_idx + 1 >= max_cols:
                continue

            dish_name = normalize(padded[col_idx])
            persons = normalize(padded[col_idx + 1])

            if dish_name and not is_header_cell(dish_name):
                if block["dish_name"] != dish_name or block["persons"] != persons:
                    if block["dish_name"] and block["ingredients"]:
                        dishes.append(
                            {
                                "dish_name": block["dish_name"],
                                "persons": block["persons"],
                                "ingredients": block["ingredients"][:],
                            }
                        )
                        block["ingredients"].clear()

                    block["dish_name"] = dish_name
                    block["persons"] = persons

            if not block["dish_name"]:
                continue

            ingredient = normalize(padded[block["ingredient_col"]])
            quantity = normalize(padded[block["quantity_col"]])

            if ingredient.lower() == block["dish_name"].lower():
                continue

            if ingredient.lower() == "item":
                continue

            if ingredient.lower() == "total":
                if block["ingredients"]:
                    dishes.append(
                        {
                            "dish_name": block["dish_name"],
                            "persons": block["persons"],
                            "ingredients": block["ingredients"][:],
                        }
                    )
                block["dish_name"] = ""
                block["persons"] = ""
                block["ingredients"].clear()
                continue

            if ingredient and (quantity or not is_end_marker(ingredient)):
                append_ingredient(block["ingredients"], ingredient, quantity)

    for block in active_blocks.values():
        if block["dish_name"] and block["ingredients"]:
            dishes.append(
                {
                    "dish_name": block["dish_name"],
                    "persons": block["persons"],
                    "ingredients": block["ingredients"][:],
                }
            )

    unique: list[dict] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for dish in dishes:
        if (dish["dish_name"].lower(), dish["persons"]) in REMOVED_DISH_RECORDS:
            continue
        key = (
            dish["dish_name"],
            dish["persons"],
            tuple(
                (item["ingredient"], item["quantity"], item["unit"])
                for item in dish["ingredients"]
            ),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(dish)

    return unique


def write_outputs(dishes: list[dict]) -> None:
    OUTPUT_JSON.write_text(json.dumps(dishes, indent=2), encoding="utf-8")

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["dish_name", "persons", "ingredients"])
        for dish in dishes:
            writer.writerow(
                [
                    dish["dish_name"],
                    dish["persons"],
                    ", ".join(
                        f"{item['ingredient']} ({item['quantity']} {item['unit']})"
                        for item in dish["ingredients"]
                    ),
                ]
            )


def main() -> None:
    with INPUT_FILE.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))

    dishes = extract_dishes(rows)
    write_outputs(dishes)

    print(f"Extracted {len(dishes)} dishes from {INPUT_FILE}")
    for dish in dishes:
        print(f"- {dish['dish_name']} ({dish['persons']} persons)")


if __name__ == "__main__":
    main()
