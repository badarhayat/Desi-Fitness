from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from flask import Flask, g, redirect, render_template, request, session, url_for

import fitness_analysis


matplotlib.use("Agg")

app = Flask(__name__)
app.secret_key = "desi-fitness-localization-key"
DEFAULT_DISH_FILES = ["dishes.csv", "dishes_2.csv"]
ATTA_GRAMS_PER_ROTI = 110
DAILY_TARGETS = {
    "calories": 2000,
    "protein": 60,
    "carbs": 250,
    "fat": 65,
}
LANGUAGE_OPTIONS = {
    "roman": "Roman Urdu",
    "urdu": "اردو",
}

DISH_NAME_URDU_MAP = {
    "aaloo": "آلو",
    "aaloo qeema": "آلو قیمہ",
    "aloo qeema": "آلو قیمہ",
    "aaloo chicken qeema": "آلو چکن قیمہ",
    "aaloo chicken qorma": "آلو چکن قورمہ",
    "aaloo paratha": "آلو پراٹھا",
    "chanay anda": "چنے انڈا",
    "chicken biryani": "چکن بریانی",
    "chai": "چائے",
    "chinese pulao": "چائنیز پلاؤ",
    "chicken karhai": "چکن کڑاہی",
    "chicken karahi": "چکن کڑاہی",
    "chicken qema": "چکن قیمہ",
    "chicken qeema": "چکن قیمہ",
    "chicken roast with chips": "چکن روسٹ چپس کے ساتھ",
    "chicken jalfarezi": "چکن جلفریزی",
    "chicken daleem": "چکن دلیم",
    "daal chawal": "دال چاول",
    "daal": "دال",
    "chanay": "چنے",
    "sindhi biryani": "سندھی بریانی",
    "chicken qema": "چکن قیمہ",
    "rice": "چاول",
}

DISH_WORD_URDU_MAP = {
    "aaloo": "آلو",
    "aloo": "آلو",
    "anda": "انڈا",
    "biryani": "بریانی",
    "chawal": "چاول",
    "chanay": "چنے",
    "chana": "چنا",
    "chicken": "چکن",
    "chips": "چپس",
    "chinese": "چائنیز",
    "daal": "دال",
    "daleem": "دلیم",
    "haleem": "حلیم",
    "jalfarezi": "جلفریزی",
    "karhai": "کڑاہی",
    "karahi": "کڑاہی",
    "paratha": "پراٹھا",
    "pulao": "پلاؤ",
    "qeema": "قیمہ",
    "qema": "قیمہ",
    "qorma": "قورمہ",
    "korma": "قورمہ",
    "rice": "چاول",
    "roast": "روسٹ",
    "sindhi": "سندھی",
    "tea": "چائے",
    "with": "کے ساتھ",
}


for key in ("meal_log", "nutrition_log"):
    if key not in fitness_analysis.user_data:
        fitness_analysis.user_data[key] = []

if "custom_dishes" not in fitness_analysis.user_data:
    fitness_analysis.user_data["custom_dishes"] = []

if "profile" not in fitness_analysis.user_data:
    fitness_analysis.user_data["profile"] = {
        "name": "",
        "height_cm": None,
        "height_feet": None,
        "height_inches": None,
        "is_registered": False,
    }


def _today() -> str:
    return datetime.now().date().isoformat()


def _get_current_language() -> str:
    lang = request.args.get("lang", "").strip().lower()
    if lang in LANGUAGE_OPTIONS:
        session["lang"] = lang
        return lang
    stored = session.get("lang", "roman")
    return stored if stored in LANGUAGE_OPTIONS else "roman"


def _split_bilingual(text: str, lang: str) -> str:
    if not isinstance(text, str):
        return text
    if " / " not in text:
        return text
    left, right = text.split(" / ", 1)
    return right if lang == "urdu" else left


def _dish_label(name: str, lang: str) -> str:
    if lang != "urdu":
        return name

    normalized = (name or "").strip().lower()
    if not normalized:
        return name

    exact = DISH_NAME_URDU_MAP.get(normalized)
    if exact:
        return exact

    parts = normalized.replace("-", " ").split()
    translated = [DISH_WORD_URDU_MAP.get(part, part) for part in parts]
    if any(part in DISH_WORD_URDU_MAP for part in parts):
        return " ".join(translated)

    return name


@app.before_request
def _set_request_language() -> None:
    g.current_lang = _get_current_language()


@app.context_processor
def _language_context() -> dict:
    current_lang = getattr(g, "current_lang", "roman")

    def t(text: str) -> str:
        return _split_bilingual(text, current_lang)

    def dish_label(name: str) -> str:
        return _dish_label(name, current_lang)

    return {
        "current_lang": current_lang,
        "language_options": LANGUAGE_OPTIONS,
        "t": t,
        "dish_label": dish_label,
    }


def _next_id(log: list[dict]) -> int:
    return max((item.get("id", 0) for item in log), default=0) + 1


def _find_entry(log: list[dict], entry_id: int) -> dict | None:
    for item in log:
        if item.get("id") == entry_id:
            return item
    return None


def _delete_entry(log: list[dict], entry_id: int) -> None:
    log[:] = [item for item in log if item.get("id") != entry_id]


def _rebuild_daily_nutrition() -> None:
    grouped: dict[str, dict] = {}
    for meal in fitness_analysis.user_data["meal_log"]:
        date = meal["date"]
        if date not in grouped:
            grouped[date] = {
                "date": date,
                "calories": 0.0,
                "protein": 0.0,
                "carbs": 0.0,
                "fat": 0.0,
                "dishes": [],
            }
        grouped[date]["calories"] += meal["calories"]
        grouped[date]["protein"] += meal["protein"]
        grouped[date]["carbs"] += meal["carbs"]
        grouped[date]["fat"] += meal["fat"]
        grouped[date]["dishes"].append(meal["dish_name"])

    nutrition_log = []
    calories_log = []
    for date in sorted(grouped):
        summary = grouped[date]
        deficit = {
            "calories": round(DAILY_TARGETS["calories"] - summary["calories"], 2),
            "protein": round(DAILY_TARGETS["protein"] - summary["protein"], 2),
            "carbs": round(DAILY_TARGETS["carbs"] - summary["carbs"], 2),
            "fat": round(DAILY_TARGETS["fat"] - summary["fat"], 2),
        }
        nutrition_log.append(
            {
                "date": date,
                "calories": round(summary["calories"], 2),
                "protein": round(summary["protein"], 2),
                "carbs": round(summary["carbs"], 2),
                "fat": round(summary["fat"], 2),
                "dishes": summary["dishes"],
                "deficit": deficit,
                "targets": DAILY_TARGETS,
            }
        )
        calories_log.append({"date": date, "calories": round(summary["calories"], 2)})

    fitness_analysis.user_data["nutrition_log"] = nutrition_log
    fitness_analysis.user_data["calories_log"] = calories_log


def _get_dishes_with_nutrition(file_paths: list[str] | None = None) -> list[dict]:
    dishes = []
    seen_keys = set()

    for file_path in (file_paths or DEFAULT_DISH_FILES):
        raw_path = Path(file_path)
        resolved_path = raw_path if raw_path.is_absolute() else (Path(app.root_path) / raw_path)

        if not resolved_path.exists():
            continue

        try:
            for dish in fitness_analysis.parse_dish(str(resolved_path)):
                try:
                    dish_copy = {
                        "dish_name": dish["dish_name"],
                        "persons": dish["persons"],
                        "ingredients": [dict(item) for item in dish["ingredients"]],
                        "supports_rotis": bool(dish.get("supports_rotis", False)),
                    }
                    fitness_analysis.calculate_per_person(dish_copy)
                    fitness_analysis.calculate_nutrition(dish_copy)

                    key = (dish_copy["dish_name"], dish_copy["persons"])
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    dishes.append(dish_copy)
                except Exception as e:
                    print(f"Error processing dish {dish.get('dish_name', 'unknown')}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        except Exception as e:
            print(f"Error parsing file {resolved_path}: {e}")
            import traceback
            traceback.print_exc()
            continue

    for custom_dish in fitness_analysis.user_data.get("custom_dishes", []):
        try:
            dish_copy = {
                "dish_name": custom_dish["dish_name"],
                "persons": int(custom_dish.get("persons") or 1),
                "ingredients": [dict(item) for item in custom_dish.get("ingredients", [])],
                "supports_rotis": bool(custom_dish.get("supports_rotis", False)),
            }
            fitness_analysis.calculate_per_person(dish_copy)
            fitness_analysis.calculate_nutrition(dish_copy)

            key = (dish_copy["dish_name"], dish_copy["persons"])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            dishes.append(dish_copy)
        except Exception as e:
            print(f"Error processing custom dish {custom_dish.get('dish_name', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
            continue

    dishes.sort(key=lambda item: item["dish_name"].lower())
    lang = getattr(g, "current_lang", "roman")
    for dish in dishes:
        dish["display_name"] = _dish_label(dish["dish_name"], lang)

    print(f"DEBUG: Loaded {len(dishes)} dishes: {[d['dish_name'] for d in dishes]}")
    return dishes


def _roti_nutrition(rotis: int) -> dict[str, float]:
    atta_nutrition = fitness_analysis.DEFAULT_NUTRITION_DB.get("atta", {})
    grams_factor = (rotis * ATTA_GRAMS_PER_ROTI) / 100
    return {
        "calories": round(atta_nutrition.get("calories", 0) * grams_factor, 2),
        "protein": round(atta_nutrition.get("protein", 0) * grams_factor, 2),
        "carbs": round(atta_nutrition.get("carbs", 0) * grams_factor, 2),
        "fat": round(atta_nutrition.get("fat", 0) * grams_factor, 2),
    }


def _meal_payload(
    dish: dict,
    date: str,
    rotis: int = 0,
    entry_id: int | None = None,
) -> dict:
    nutrition = dish.get("nutrition_per_person", {})
    roti_nutrition = _roti_nutrition(rotis) if dish.get("supports_rotis") else _roti_nutrition(0)
    payload = {
        "date": date,
        "dish_name": dish["dish_name"],
        "rotis": rotis if dish.get("supports_rotis") else 0,
        "calories": round(nutrition.get("calories", 0) + roti_nutrition["calories"], 2),
        "protein": round(nutrition.get("protein", 0) + roti_nutrition["protein"], 2),
        "carbs": round(nutrition.get("carbs", 0) + roti_nutrition["carbs"], 2),
        "fat": round(nutrition.get("fat", 0) + roti_nutrition["fat"], 2),
    }
    if entry_id is not None:
        payload["id"] = entry_id
    return payload


def _upsert_weight(date: str, weight: float, entry_id: int | None = None) -> dict:
    if entry_id is None:
        entry = {"id": _next_id(fitness_analysis.user_data["weight_log"]), "date": date, "weight": weight}
        fitness_analysis.user_data["weight_log"].append(entry)
        return entry

    entry = _find_entry(fitness_analysis.user_data["weight_log"], entry_id)
    if entry is None:
        entry = {"id": entry_id}
        fitness_analysis.user_data["weight_log"].append(entry)
    entry.update({"date": date, "weight": weight})
    return entry


def _upsert_steps(date: str, steps: int, entry_id: int | None = None) -> dict:
    calories_lost = fitness_analysis.calculate_calories_burned(steps)
    if entry_id is None:
        entry = {
            "id": _next_id(fitness_analysis.user_data["steps_log"]),
            "date": date,
            "steps": steps,
            "calories_lost": calories_lost,
        }
        fitness_analysis.user_data["steps_log"].append(entry)
        return entry

    entry = _find_entry(fitness_analysis.user_data["steps_log"], entry_id)
    if entry is None:
        entry = {"id": entry_id}
        fitness_analysis.user_data["steps_log"].append(entry)
    entry.update({"date": date, "steps": steps, "calories_lost": calories_lost})
    return entry


def _build_graph_rows() -> list[dict]:
    dates = set()
    for key in ("weight_log", "steps_log", "calories_log"):
        for entry in fitness_analysis.user_data[key]:
            dates.add(entry["date"])

    rows = []
    for date in sorted(dates):
        weight = next(
            (entry["weight"] for entry in fitness_analysis.user_data["weight_log"] if entry["date"] == date),
            None,
        )
        steps = next(
            (entry["steps"] for entry in fitness_analysis.user_data["steps_log"] if entry["date"] == date),
            None,
        )
        burned = next(
            (
                entry["calories_lost"]
                for entry in fitness_analysis.user_data["steps_log"]
                if entry["date"] == date
            ),
            None,
        )
        consumed = next(
            (
                entry["calories"]
                for entry in fitness_analysis.user_data["calories_log"]
                if entry["date"] == date
            ),
            None,
        )
        net = None if consumed is None else round(consumed - (burned or 0), 2)
        rows.append(
            {
                "date": date,
                "weight": weight,
                "steps": steps,
                "calories_consumed": consumed,
                "calories_burned": burned,
                "net_calories": net,
            }
        )
    return rows


@app.route("/")
def home():
    today = _today()
    today_nutrition = next(
        (entry for entry in fitness_analysis.user_data["nutrition_log"] if entry["date"] == today),
        None,
    )
    calories_eaten = round(today_nutrition["calories"], 2) if today_nutrition else 0.0
    calories_target = DAILY_TARGETS["calories"]
    calories_percent = round(min(100.0, (calories_eaten / calories_target) * 100), 2) if calories_target else 0.0

    latest_weight = None
    if fitness_analysis.user_data["weight_log"]:
        latest_weight_entry = max(
            fitness_analysis.user_data["weight_log"],
            key=lambda item: (item.get("date", ""), item.get("id", 0)),
        )
        latest_weight = latest_weight_entry.get("weight")

    profile = fitness_analysis.user_data.get("profile", {})

    bmi = None
    bmi_category = None
    bmi_note = None
    ideal_weight_range = None

    height_cm = profile.get("height_cm") if profile else None
    if latest_weight is not None and height_cm:
        height_m = float(height_cm) / 100
        if height_m > 0:
            bmi = round(float(latest_weight) / (height_m * height_m), 2)
            normal_low = 18.5
            normal_high = 24.9

            ideal_low = round(normal_low * (height_m * height_m), 1)
            ideal_high = round(normal_high * (height_m * height_m), 1)
            ideal_weight_range = f"{ideal_low} kg - {ideal_high} kg"

            if bmi < 18.5:
                bmi_category = "Underweight"
                bmi_note = "Below the standard healthy BMI range (18.5-24.9)."
            elif bmi <= 24.9:
                bmi_category = "Normal"
                bmi_note = "Within the standard healthy BMI range (18.5-24.9)."
            elif bmi <= 29.9:
                bmi_category = "Overweight"
                bmi_note = "Above the standard healthy BMI range (18.5-24.9)."
            else:
                bmi_category = "Obese"
                bmi_note = "Well above the standard healthy BMI range (18.5-24.9)."

    return render_template(
        "index.html",
        today=today,
        calories_eaten=calories_eaten,
        calories_target=calories_target,
        calories_percent=calories_percent,
        latest_weight=latest_weight,
        profile=profile,
        bmi=bmi,
        bmi_category=bmi_category,
        bmi_note=bmi_note,
        ideal_weight_range=ideal_weight_range,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    profile = fitness_analysis.user_data.setdefault(
        "profile",
        {
            "name": "",
            "height_cm": None,
            "height_feet": None,
            "height_inches": None,
            "is_registered": False,
        },
    )
    error = None

    form_name = profile.get("name", "")
    form_height_feet = profile.get("height_feet")
    form_height_inches = profile.get("height_inches")

    if (form_height_feet is None or form_height_inches is None) and profile.get("height_cm"):
        total_inches = round(float(profile["height_cm"]) / 2.54)
        form_height_feet = total_inches // 12
        form_height_inches = total_inches % 12

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        height_feet_raw = request.form.get("height_feet", "").strip()
        height_inches_raw = request.form.get("height_inches", "").strip()

        form_name = name
        form_height_feet = height_feet_raw
        form_height_inches = height_inches_raw

        if not name:
            error = "Name is required."
        else:
            try:
                height_feet = int(height_feet_raw)
                height_inches = int(height_inches_raw)
                if height_feet < 1 or height_feet > 9:
                    raise ValueError
                if height_inches < 0 or height_inches > 11:
                    raise ValueError
            except ValueError:
                error = "Enter a valid height in feet and inches (inches 0-11)."
            else:
                total_inches = (height_feet * 12) + height_inches
                height_cm = round(total_inches * 2.54, 1)
                profile.update(
                    {
                        "name": name,
                        "height_cm": height_cm,
                        "height_feet": height_feet,
                        "height_inches": height_inches,
                        "is_registered": True,
                    }
                )
                return redirect(url_for("home"))

    return render_template(
        "register.html",
        profile=profile,
        error=error,
        form_name=form_name,
        form_height_feet=form_height_feet,
        form_height_inches=form_height_inches,
    )


@app.route("/set-language", methods=["POST"])
def set_language():
    language = request.form.get("language", "roman").strip().lower()
    if language in LANGUAGE_OPTIONS:
        session["lang"] = language

    next_url = request.form.get("next", "").strip()
    if next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for("home"))


@app.route("/custom-dish", methods=["GET", "POST"])
def custom_dish():
    error = None

    if request.method == "POST":
        dish_name = request.form.get("dish_name", "").strip()
        persons_raw = request.form.get("persons", "1").strip()
        supports_rotis = request.form.get("supports_rotis") == "on"
        ingredient_names = request.form.getlist("ingredient_name")
        ingredient_quantities = request.form.getlist("ingredient_quantity")
        ingredient_units = request.form.getlist("ingredient_unit")

        if not dish_name:
            error = "Dish name is required."
        else:
            try:
                persons = int(persons_raw)
                if persons < 1:
                    raise ValueError
            except ValueError:
                error = "Servings must be a positive whole number."
                persons = 1

        parsed_ingredients = []
        if error is None:
            for name_raw, qty_raw, unit_raw in zip(
                ingredient_names,
                ingredient_quantities,
                ingredient_units,
            ):
                name = name_raw.strip()
                qty_text = qty_raw.strip()
                unit = unit_raw.strip().lower()

                if not name and not qty_text:
                    continue

                if not name:
                    error = "Each ingredient row needs an item name."
                    break
                try:
                    quantity = float(qty_text)
                    if quantity <= 0:
                        raise ValueError
                except ValueError:
                    error = f"Enter a valid quantity for ingredient '{name}'."
                    break

                if unit not in {"kilograms", "litres", "pieces"}:
                    error = f"Choose a valid unit for ingredient '{name}'."
                    break

                parsed_ingredients.append(
                    {
                        "name": name,
                        "quantity": round(quantity, 6),
                        "unit": unit,
                    }
                )

            if not parsed_ingredients and error is None:
                error = "Add at least one ingredient."

        if error is None:
            existing = fitness_analysis.user_data.setdefault("custom_dishes", [])
            existing[:] = [dish for dish in existing if dish.get("dish_name", "").lower() != dish_name.lower()]
            existing.append(
                {
                    "dish_name": dish_name,
                    "persons": persons,
                    "ingredients": parsed_ingredients,
                    "supports_rotis": supports_rotis,
                }
            )
            return redirect(url_for("analyze", dish_name=dish_name))

    return render_template(
        "custom_dish.html",
        error=error,
        custom_dishes=sorted(
            fitness_analysis.user_data.get("custom_dishes", []),
            key=lambda item: item.get("dish_name", "").lower(),
        ),
    )


@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    dishes = _get_dishes_with_nutrition()
    dish_options = [{"value": dish["dish_name"], "label": dish["display_name"]} for dish in dishes]
    form_source = request.form if request.method == "POST" else request.args
    selected_dish_name = form_source.get("dish_name", "")
    current_preview_dish_name = form_source.get("current_preview_dish_name", "")
    meal_date = form_source.get("meal_date", "").strip() or _today()
    selected_dish = next((dish for dish in dishes if dish["dish_name"] == selected_dish_name), None)
    preview_dish = None
    selected_rotis = form_source.get("rotis", "0").strip() or "0"
    editing_meal = None
    error = None

    if request.method == "POST":
        action = request.form.get("action", "preview")
        try:
            if action == "delete":
                _delete_entry(fitness_analysis.user_data["meal_log"], int(request.form["meal_id"]))
                _rebuild_daily_nutrition()
                return redirect(url_for("analyze"))

            if action == "edit":
                editing_meal = _find_entry(
                    fitness_analysis.user_data["meal_log"], int(request.form["meal_id"])
                )
                if editing_meal:
                    selected_dish_name = editing_meal["dish_name"]
                    meal_date = editing_meal["date"]
                    selected_rotis = str(editing_meal.get("rotis", 0))
                    selected_dish = next(
                        (dish for dish in dishes if dish["dish_name"] == selected_dish_name), None
                    )
                    preview_dish = selected_dish

            if action == "preview":
                if selected_dish is not None and current_preview_dish_name == selected_dish_name:
                    preview_dish = None
                else:
                    preview_dish = selected_dish

            if action in {"add", "save"} and selected_dish is not None:
                meal_id = request.form.get("meal_id", "").strip()
                rotis_raw = request.form.get("rotis", "0").strip() or "0"
                rotis = max(0, int(rotis_raw))
                selected_rotis = str(rotis)
                payload = _meal_payload(
                    selected_dish,
                    meal_date,
                    rotis=rotis,
                    entry_id=int(meal_id) if meal_id else None,
                )
                if meal_id:
                    entry = _find_entry(fitness_analysis.user_data["meal_log"], int(meal_id))
                    if entry is None:
                        fitness_analysis.user_data["meal_log"].append(payload)
                    else:
                        entry.update(payload)
                else:
                    payload["id"] = _next_id(fitness_analysis.user_data["meal_log"])
                    fitness_analysis.user_data["meal_log"].append(payload)
                _rebuild_daily_nutrition()
                return redirect(url_for("analyze", meal_date=meal_date))
        except Exception as exc:
            error = str(exc)

    logged_for_date = next(
        (entry for entry in fitness_analysis.user_data["nutrition_log"] if entry["date"] == meal_date),
        None,
    )
    logged_dishes_display = []
    if logged_for_date:
        logged_dishes_display = [
            _dish_label(dish_name, getattr(g, "current_lang", "roman"))
            for dish_name in logged_for_date.get("dishes", [])
        ]

    return render_template(
        "analyze.html",
        dish_options=dish_options,
        selected_dish_name=selected_dish_name,
        selected_dish=selected_dish,
        preview_dish=preview_dish,
        current_preview_dish_name=preview_dish["dish_name"] if preview_dish else "",
        selected_rotis=selected_rotis,
        roti_nutrition_per_piece=_roti_nutrition(1),
        meal_date=meal_date,
        logged_for_date=logged_for_date,
        logged_dishes_display=logged_dishes_display,
        meal_log=sorted(fitness_analysis.user_data["meal_log"], key=lambda item: (item["date"], item["id"])),
        editing_meal=editing_meal,
        error=error,
    )


@app.route("/track", methods=["GET", "POST"])
def track():
    result = None
    editing_weight = None
    editing_steps = None

    if request.method == "POST":
        action = request.form.get("action", "add")

        if action == "delete_weight":
            _delete_entry(fitness_analysis.user_data["weight_log"], int(request.form["weight_id"]))
            return redirect(url_for("track"))

        if action == "delete_steps":
            _delete_entry(fitness_analysis.user_data["steps_log"], int(request.form["steps_id"]))
            return redirect(url_for("track"))

        if action == "edit_weight":
            editing_weight = _find_entry(
                fitness_analysis.user_data["weight_log"], int(request.form["weight_id"])
            )

        if action == "edit_steps":
            editing_steps = _find_entry(
                fitness_analysis.user_data["steps_log"], int(request.form["steps_id"])
            )

        if action == "save_weight":
            date = request.form.get("weight_date", _today()).strip() or _today()
            weight = request.form.get("weight", "").strip()
            if weight:
                entry_id = request.form.get("weight_id", "").strip()
                result = _upsert_weight(date, float(weight), int(entry_id) if entry_id else None)
                return redirect(url_for("track"))

        if action == "save_steps":
            date = request.form.get("steps_date", _today()).strip() or _today()
            steps = request.form.get("steps", "").strip()
            if steps:
                entry_id = request.form.get("steps_id", "").strip()
                result = _upsert_steps(date, int(steps), int(entry_id) if entry_id else None)
                return redirect(url_for("track"))

    return render_template(
        "track.html",
        result=result,
        today=_today(),
        weight_log=sorted(fitness_analysis.user_data["weight_log"], key=lambda item: (item["date"], item["id"])),
        steps_log=sorted(fitness_analysis.user_data["steps_log"], key=lambda item: (item["date"], item["id"])),
        editing_weight=editing_weight,
        editing_steps=editing_steps,
    )


@app.route("/fasting", methods=["GET", "POST"])
def fasting():
    duration_options = [16, 18, 20, 48]

    if request.method == "POST":
        action = request.form.get("action")
        if action == "start":
            selected_hours_raw = request.form.get("duration_hours", "16").strip()
            try:
                selected_hours = int(selected_hours_raw)
            except ValueError:
                selected_hours = 16

            if selected_hours not in duration_options:
                selected_hours = 16

            fitness_analysis.start_fast(selected_hours)
        elif action == "stop":
            fitness_analysis.end_fast()

    history = fitness_analysis.fasting_data["history"]
    last_duration = history[-1]["duration_hours"] if history else None
    progress = fitness_analysis.get_fasting_progress()
    current_target_hours = fitness_analysis.fasting_data["current_fast"].get("target_hours") or 16

    return render_template(
        "fasting.html",
        fasting_data=fitness_analysis.fasting_data,
        fasting_duration=fitness_analysis.get_fasting_duration(),
        last_duration=last_duration,
        duration_options=duration_options,
        current_target_hours=current_target_hours,
        remaining_seconds=progress["remaining_seconds"],
        target_seconds=progress["target_seconds"],
        completion_percent=progress["completion_percent"],
    )


@app.route("/graph")
def graph():
    graph_data = _build_graph_rows()
    graph_url = None

    if graph_data:
        static_dir = Path(app.root_path) / "static"
        static_dir.mkdir(exist_ok=True)
        graph_path = static_dir / "progress_graph.png"

        dates = [row["date"] for row in graph_data]
        weights = [row["weight"] for row in graph_data]
        net_calories = [row["net_calories"] for row in graph_data]

        fig, ax1 = plt.subplots(figsize=(10, 5))
        ax1.plot(dates, weights, color="blue", marker="o")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Weight (kg)", color="blue")
        ax1.tick_params(axis="y", labelcolor="blue")

        ax2 = ax1.twinx()
        ax2.plot(dates, net_calories, color="green", marker="^", linestyle="--")
        ax2.set_ylabel("Net Calories", color="green")
        ax2.tick_params(axis="y", labelcolor="green")

        plt.title("Weight and Net Calories Over Time")
        fig.tight_layout()
        fig.savefig(graph_path)
        plt.close(fig)
        graph_url = url_for("static", filename="progress_graph.png")

    return render_template("graph.html", graph_data=graph_data, graph_url=graph_url)


if __name__ == "__main__":
    app.run(debug=True)
