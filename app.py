from __future__ import annotations

from datetime import datetime
import math
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


def _get_current_username() -> str | None:
    """Get username from session, or None if not logged in."""
    return session.get("username")


def _get_current_user_data() -> dict | None:
    """Get current user's data dictionary, or None if not logged in."""
    username = _get_current_username()
    if username:
        return fitness_analysis._get_or_create_user_data(username)
    return None


def _require_login():
    """Redirect to login if not authenticated."""
    if not _get_current_username():
        return redirect(url_for("login"))
    return None


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


@app.after_request
def _auto_save_user_data(response):
    """Persist the current user's data to disk after every mutating request."""
    if request.method == "POST":
        username = _get_current_username()
        if username and username in fitness_analysis.all_user_data:
            try:
                fitness_analysis._save_user_data(username)
            except Exception:
                pass  # Never let a save failure break the response
    return response


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


def _rebuild_daily_nutrition(user_data: dict) -> None:
    grouped: dict[str, dict] = {}
    for meal in user_data["meal_log"]:
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

    user_data["nutrition_log"] = nutrition_log
    user_data["calories_log"] = calories_log


def _get_user_nutrition_db(user_data: dict) -> dict[str, dict[str, float]]:
    nutrition_db = {
        key.lower(): {
            "calories": float(value.get("calories", 0)),
            "protein": float(value.get("protein", 0)),
            "carbs": float(value.get("carbs", 0)),
            "fat": float(value.get("fat", 0)),
        }
        for key, value in fitness_analysis.DEFAULT_NUTRITION_DB.items()
    }

    for key, value in user_data.get("custom_nutrition_db", {}).items():
        normalized_key = str(key).strip().lower()
        if not normalized_key:
            continue
        nutrition_db[normalized_key] = {
            "calories": float(value.get("calories", 0)),
            "protein": float(value.get("protein", 0)),
            "carbs": float(value.get("carbs", 0)),
            "fat": float(value.get("fat", 0)),
        }

    return nutrition_db


def _get_dishes_with_nutrition(user_data: dict, file_paths: list[str] | None = None) -> list[dict]:
    dishes = []
    seen_keys = set()
    nutrition_db = _get_user_nutrition_db(user_data)

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
                    fitness_analysis.calculate_nutrition(dish_copy, nutrition_db)

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

    for custom_dish in user_data.get("custom_dishes", []):
        try:
            dish_copy = {
                "dish_name": custom_dish["dish_name"],
                "persons": int(custom_dish.get("persons") or 1),
                "ingredients": [dict(item) for item in custom_dish.get("ingredients", [])],
                "supports_rotis": bool(custom_dish.get("supports_rotis", False)),
            }
            fitness_analysis.calculate_per_person(dish_copy)
            fitness_analysis.calculate_nutrition(dish_copy, nutrition_db)

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


def _roti_nutrition(
    rotis: int,
    nutrition_db: dict[str, dict[str, float]] | None = None,
) -> dict[str, float]:
    atta_nutrition = (nutrition_db or fitness_analysis.DEFAULT_NUTRITION_DB).get(
        "atta", fitness_analysis.DEFAULT_NUTRITION_DB.get("atta", {})
    )
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
    nutrition_db: dict[str, dict[str, float]] | None = None,
) -> dict:
    nutrition = dish.get("nutrition_per_person", {})
    atta_nutrition = (nutrition_db or fitness_analysis.DEFAULT_NUTRITION_DB).get(
        "atta", fitness_analysis.DEFAULT_NUTRITION_DB.get("atta", {})
    )
    grams_factor = ((rotis if dish.get("supports_rotis") else 0) * ATTA_GRAMS_PER_ROTI) / 100
    roti_nutrition = {
        "calories": round(atta_nutrition.get("calories", 0) * grams_factor, 2),
        "protein": round(atta_nutrition.get("protein", 0) * grams_factor, 2),
        "carbs": round(atta_nutrition.get("carbs", 0) * grams_factor, 2),
        "fat": round(atta_nutrition.get("fat", 0) * grams_factor, 2),
    }
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


def _upsert_weight(user_data: dict, date: str, weight: float, entry_id: int | None = None) -> dict:
    if entry_id is None:
        entry = {"id": _next_id(user_data["weight_log"]), "date": date, "weight": weight}
        user_data["weight_log"].append(entry)
        return entry

    entry = _find_entry(user_data["weight_log"], entry_id)
    if entry is None:
        entry = {"id": entry_id}
        user_data["weight_log"].append(entry)
    entry.update({"date": date, "weight": weight})
    return entry


def _upsert_exercise(user_data: dict, date: str, exercise_type: str, reps: int, entry_id: int | None = None) -> dict:
    calories_lost = fitness_analysis.calculate_exercise_calories(exercise_type, reps)
    log = user_data.setdefault("exercise_log", [])
    if entry_id is None:
        entry = {"id": _next_id(log), "date": date, "type": exercise_type, "reps": reps, "calories_lost": calories_lost}
        log.append(entry)
        return entry
    entry = _find_entry(log, entry_id)
    if entry is None:
        entry = {"id": entry_id}
        log.append(entry)
    entry.update({"date": date, "type": exercise_type, "reps": reps, "calories_lost": calories_lost})
    return entry


def _upsert_steps(user_data: dict, date: str, steps: int, entry_id: int | None = None) -> dict:
    calories_lost = fitness_analysis.calculate_calories_burned(steps)
    if entry_id is None:
        entry = {
            "id": _next_id(user_data["steps_log"]),
            "date": date,
            "steps": steps,
            "calories_lost": calories_lost,
        }
        user_data["steps_log"].append(entry)
        return entry

    entry = _find_entry(user_data["steps_log"], entry_id)
    if entry is None:
        entry = {"id": entry_id}
        user_data["steps_log"].append(entry)
    entry.update({"date": date, "steps": steps, "calories_lost": calories_lost})
    return entry


def _build_graph_rows(user_data: dict) -> list[dict]:
    dates = set()
    for key in ("weight_log", "steps_log", "calories_log"):
        for entry in user_data[key]:
            dates.add(entry["date"])

    rows = []
    for date in sorted(dates):
        weight = next(
            (entry["weight"] for entry in user_data["weight_log"] if entry["date"] == date),
            None,
        )
        steps = next(
            (entry["steps"] for entry in user_data["steps_log"] if entry["date"] == date),
            None,
        )
        burned = next(
            (
                entry["calories_lost"]
                for entry in user_data["steps_log"]
                if entry["date"] == date
            ),
            None,
        )
        consumed = next(
            (
                entry["calories"]
                for entry in user_data["calories_log"]
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


def _calculate_daily_net_calories(user_data: dict, date: str) -> tuple[float, float, float]:
    """Return (net, consumed, burned) calories for a given date."""
    consumed_entry = next(
        (entry for entry in user_data.get("nutrition_log", []) if entry.get("date") == date),
        None,
    )
    consumed = float(consumed_entry.get("calories", 0.0)) if consumed_entry else 0.0
    burned_steps = sum(
        float(entry.get("calories_lost", 0.0))
        for entry in user_data.get("steps_log", [])
        if entry.get("date") == date
    )
    burned_exercise = sum(
        float(entry.get("calories_lost", 0.0))
        for entry in user_data.get("exercise_log", [])
        if entry.get("date") == date
    )
    burned = burned_steps + burned_exercise
    return round(consumed - burned, 2), round(consumed, 2), round(burned, 2)


def _save_net_vs_target_pie(
    username: str,
    net_calories: float,
    target_calories: float,
    file_stem: str,
) -> str:
    """Generate a pie chart image and return its static URL."""
    safe_target = target_calories if target_calories > 0 else DAILY_TARGETS["calories"]
    within_target = max(0.0, min(net_calories, safe_target))
    remaining = max(0.0, safe_target - within_target)
    over_target = max(0.0, net_calories - safe_target)

    values: list[float] = []
    labels: list[str] = []
    colors: list[str] = []
    if within_target > 0:
        values.append(within_target)
        labels.append("Net")
        colors.append("#22c55e")
    if remaining > 0:
        values.append(remaining)
        labels.append("Remaining")
        colors.append("#334155")
    if over_target > 0:
        values.append(over_target)
        labels.append("Over")
        colors.append("#f97316")
    if not values:
        values = [1.0]
        labels = ["No data"]
        colors = ["#64748b"]

    safe_user = "".join(ch if ch.isalnum() else "_" for ch in (username or "user"))
    static_dir = Path(app.root_path) / "static"
    static_dir.mkdir(exist_ok=True)
    out_path = static_dir / f"{file_stem}_{safe_user}.png"

    fig, ax = plt.subplots(figsize=(4.8, 4.8))
    ax.pie(
        values,
        labels=labels,
        autopct="%1.0f%%",
        startangle=90,
        colors=colors,
        textprops={"color": "white", "fontsize": 10},
    )
    ax.axis("equal")
    ax.set_title("Net Calories vs Target", color="white")
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")
    fig.tight_layout()
    fig.savefig(out_path, transparent=False)
    plt.close(fig)
    return url_for("static", filename=out_path.name)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page for existing users."""
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        
        if not username:
            error = "Username is required."
        elif username not in fitness_analysis.all_user_data:
            error = "Username not found. Please register first."
        else:
            session["username"] = username
            return redirect(url_for("home"))
    
    return render_template("login.html", error=error)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    """Logout the current user."""
    session.pop("username", None)
    return redirect(url_for("login"))


@app.route("/")
def home():
    login_check = _require_login()
    if login_check:
        return login_check
    
    user_data = _get_current_user_data()
    username = _get_current_username() or "user"
    today = _today()
    profile = user_data.get("profile", {})
    calories_target = profile.get("daily_calories_target") or DAILY_TARGETS["calories"]
    net_calories_today, calories_eaten, calories_burned_today = _calculate_daily_net_calories(
        user_data, today
    )
    calories_percent_raw = round((calories_eaten / calories_target) * 100, 2) if calories_target else 0.0
    calories_percent = min(100.0, calories_percent_raw)
    calories_over_percent = round(max(0.0, calories_percent_raw - 100.0), 2)
    net_target_percent = round((net_calories_today / calories_target) * 100, 2) if calories_target else 0.0
    net_delta = round(net_calories_today - calories_target, 2)
    net_status = "over" if net_delta > 0 else "under" if net_delta < 0 else "on_target"
    walk_steps_needed = 0
    walk_minutes_needed = 0
    if net_delta > 0:
        # Approximation based on 0.04 kcal per step and ~100 steps/min normal walk.
        walk_steps_needed = math.ceil(net_delta / 0.04)
        walk_minutes_needed = max(1, math.ceil(walk_steps_needed / 100))
    net_vs_target_pie_url = _save_net_vs_target_pie(
        username,
        max(0.0, net_calories_today),
        float(calories_target),
        "home_net_vs_target_pie",
    )

    latest_weight = None
    if user_data["weight_log"]:
        latest_weight_entry = max(
            user_data["weight_log"],
            key=lambda item: (item.get("date", ""), item.get("id", 0)),
        )
        latest_weight = latest_weight_entry.get("weight")

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
        calories_burned_today=calories_burned_today,
        net_calories_today=net_calories_today,
        calories_target=calories_target,
        calories_percent=calories_percent,
        calories_percent_raw=calories_percent_raw,
        calories_over_percent=calories_over_percent,
        net_target_percent=net_target_percent,
        net_vs_target_pie_url=net_vs_target_pie_url,
        net_delta=net_delta,
        net_status=net_status,
        walk_steps_needed=walk_steps_needed,
        walk_minutes_needed=walk_minutes_needed,
        latest_weight=latest_weight,
        profile=profile,
        bmi=bmi,
        bmi_category=bmi_category,
        bmi_note=bmi_note,
        ideal_weight_range=ideal_weight_range,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    current_username = _get_current_username()
    is_edit_mode = current_username is not None
    current_user_data = _get_current_user_data() if is_edit_mode else None
    current_profile = current_user_data.get("profile", {}) if current_user_data else {}

    error = None
    form_name = current_profile.get("name", "")
    form_username = current_username or ""
    form_height_feet = current_profile.get("height_feet")
    form_height_inches = current_profile.get("height_inches")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = current_username or request.form.get("username", "").strip().lower()
        height_feet_raw = request.form.get("height_feet", "").strip()
        height_inches_raw = request.form.get("height_inches", "").strip()

        form_name = name
        form_username = username
        form_height_feet = height_feet_raw
        form_height_inches = height_inches_raw

        # Validation
        if not name:
            error = "Name is required."
        elif not is_edit_mode and not username:
            error = "Username is required."
        elif not height_feet_raw or not height_inches_raw:
            error = "Height in feet and inches is required."
        elif not is_edit_mode and username in fitness_analysis.all_user_data:
            error = "Username already taken. Choose another."
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

                user_data = fitness_analysis._get_or_create_user_data(username)
                user_data["profile"].update(
                    {
                        "name": name,
                        "height_cm": height_cm,
                        "height_feet": height_feet,
                        "height_inches": height_inches,
                        "is_registered": True,
                    }
                )

                session["username"] = username
                return redirect(url_for("home"))

    return render_template(
        "register.html",
        error=error,
        form_name=form_name,
        form_username=form_username,
        form_height_feet=form_height_feet,
        form_height_inches=form_height_inches,
        is_edit_mode=is_edit_mode,
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
    login_check = _require_login()
    if login_check:
        return login_check
    
    user_data = _get_current_user_data()
    error = None
    notice = request.args.get("notice", "").strip()
    editing_dish_name = request.args.get("edit_dish", "").strip()
    editing_dish = None

    if editing_dish_name:
        editing_dish = next(
            (
                dish
                for dish in user_data.get("custom_dishes", [])
                if dish.get("dish_name", "").lower() == editing_dish_name.lower()
            ),
            None,
        )

    if request.method == "POST":
        action = request.form.get("action", "save_dish").strip()

        if action == "delete_dish":
            dish_name_to_delete = request.form.get("dish_name_to_delete", "").strip()
            if dish_name_to_delete:
                existing = user_data.setdefault("custom_dishes", [])
                existing[:] = [
                    dish
                    for dish in existing
                    if dish.get("dish_name", "").lower() != dish_name_to_delete.lower()
                ]
                return redirect(
                    url_for("custom_dish", notice=f"Deleted dish '{dish_name_to_delete}'.")
                )
            return redirect(url_for("custom_dish"))

        if action == "delete_nutrition":
            item_name = request.form.get("item_name", "").strip().lower()
            if item_name:
                custom_db = user_data.setdefault("custom_nutrition_db", {})
                custom_db.pop(item_name, None)
                return redirect(url_for("custom_dish", notice=f"Deleted nutrition for '{item_name}'."))
            return redirect(url_for("custom_dish"))

        if action == "save_nutrition_item":
            item_name = request.form.get("nutrition_item_name", "").strip().lower()
            calories_text = request.form.get("calories", "").strip()
            protein_text = request.form.get("protein", "").strip()
            carbs_text = request.form.get("carbs", "").strip()
            fat_text = request.form.get("fat", "").strip()
            # For standalone adds, accept a unit so we store in the correct internal format.
            ni_unit = request.form.get("nutrition_unit", "per_100").strip().lower()

            if not item_name:
                error = "Nutrition item name is required."
            else:
                try:
                    calories_value = float(calories_text)
                    protein_value = float(protein_text)
                    carbs_value = float(carbs_text)
                    fat_value = float(fat_text)
                    if any(
                        value < 0
                        for value in (calories_value, protein_value, carbs_value, fat_value)
                    ):
                        raise ValueError
                except ValueError:
                    error = (
                        f"Enter valid non-negative nutrition values for ingredient '{item_name}'."
                    )
                else:
                    # per_100 (default) → no conversion; per_kg/per_litre → ÷10; per_piece → ×1
                    storage_factor = 0.1 if ni_unit in {"per_kg", "per_litre"} else 1.0
                    custom_db = user_data.setdefault("custom_nutrition_db", {})
                    custom_db[item_name] = {
                        "calories": round(calories_value * storage_factor, 4),
                        "protein": round(protein_value * storage_factor, 4),
                        "carbs": round(carbs_value * storage_factor, 4),
                        "fat": round(fat_value * storage_factor, 4),
                    }
                    return redirect(url_for("custom_dish", notice=f"Saved nutrition for '{item_name}'."))

        if action != "save_dish":
            return redirect(url_for("custom_dish"))

        dish_name = request.form.get("dish_name", "").strip()
        original_dish_name = request.form.get("original_dish_name", "").strip()
        persons_raw = request.form.get("persons", "1").strip()
        supports_rotis = request.form.get("supports_rotis") == "on"
        ingredient_names = request.form.getlist("ingredient_name")
        ingredient_quantities = request.form.getlist("ingredient_quantity")
        ingredient_units = request.form.getlist("ingredient_unit")
        ingredient_calories = request.form.getlist("ingredient_calories")
        ingredient_protein = request.form.getlist("ingredient_protein")
        ingredient_carbs = request.form.getlist("ingredient_carbs")
        ingredient_fat = request.form.getlist("ingredient_fat")

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
        nutrition_updates: dict[str, dict[str, float]] = {}
        if error is None:
            for name_raw, qty_raw, unit_raw, cal_raw, protein_raw, carbs_raw, fat_raw in zip(
                ingredient_names,
                ingredient_quantities,
                ingredient_units,
                ingredient_calories,
                ingredient_protein,
                ingredient_carbs,
                ingredient_fat,
            ):
                name = name_raw.strip()
                qty_text = qty_raw.strip()
                unit = unit_raw.strip().lower()
                calories_text = cal_raw.strip()
                protein_text = protein_raw.strip()
                carbs_text = carbs_raw.strip()
                fat_text = fat_raw.strip()

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

                has_any_nutrition = any(
                    text for text in (calories_text, protein_text, carbs_text, fat_text)
                )
                if has_any_nutrition and not all(
                    text for text in (calories_text, protein_text, carbs_text, fat_text)
                ):
                    error = (
                        f"Provide all nutrition fields (calories/protein/carbs/fat) for ingredient '{name}', "
                        "or leave all of them blank."
                    )
                    break

                if has_any_nutrition:
                    try:
                        calories_value = float(calories_text)
                        protein_value = float(protein_text)
                        carbs_value = float(carbs_text)
                        fat_value = float(fat_text)
                        if any(
                            value < 0
                            for value in (calories_value, protein_value, carbs_value, fat_value)
                        ):
                            raise ValueError
                    except ValueError:
                        error = f"Enter valid non-negative nutrition values for ingredient '{name}'."
                        break

                    # User enters per-kg or per-litre; internal DB stores per-100g/100ml.
                    # For pieces the entered value is already per-piece, no conversion needed.
                    storage_factor = 1.0 if unit == "pieces" else 0.1
                    nutrition_updates[name.lower()] = {
                        "calories": round(calories_value * storage_factor, 4),
                        "protein": round(protein_value * storage_factor, 4),
                        "carbs": round(carbs_value * storage_factor, 4),
                        "fat": round(fat_value * storage_factor, 4),
                    }

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
            existing = user_data.setdefault("custom_dishes", [])
            names_to_replace = {dish_name.lower()}
            if original_dish_name:
                names_to_replace.add(original_dish_name.lower())
            existing[:] = [
                dish
                for dish in existing
                if dish.get("dish_name", "").lower() not in names_to_replace
            ]
            existing.append(
                {
                    "dish_name": dish_name,
                    "persons": persons,
                    "ingredients": parsed_ingredients,
                    "supports_rotis": supports_rotis,
                }
            )

            if nutrition_updates:
                custom_db = user_data.setdefault("custom_nutrition_db", {})
                custom_db.update(nutrition_updates)

            if original_dish_name:
                return redirect(url_for("custom_dish", notice=f"Updated dish '{dish_name}'."))

            return redirect(url_for("analyze", dish_name=dish_name))

    return render_template(
        "custom_dish.html",
        error=error,
        notice=notice,
        editing_dish=editing_dish,
        custom_dishes=sorted(
            user_data.get("custom_dishes", []),
            key=lambda item: item.get("dish_name", "").lower(),
        ),
        custom_nutrition_items=sorted(
            [
                {
                    "name": key,
                    "calories": float(value.get("calories", 0)),
                    "protein": float(value.get("protein", 0)),
                    "carbs": float(value.get("carbs", 0)),
                    "fat": float(value.get("fat", 0)),
                }
                for key, value in user_data.get("custom_nutrition_db", {}).items()
            ],
            key=lambda item: item["name"],
        ),
    )


@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    login_check = _require_login()
    if login_check:
        return login_check
    
    user_data = _get_current_user_data()
    nutrition_db = _get_user_nutrition_db(user_data)
    dishes = _get_dishes_with_nutrition(user_data)
    dish_options = [
        {
            "value": dish["dish_name"],
            "label": dish["display_name"],
            "supports_rotis": bool(dish.get("supports_rotis", False)),
        }
        for dish in dishes
    ]
    form_source = request.form if request.method == "POST" else request.args
    selected_dish_name = form_source.get("dish_name", "")
    current_preview_dish_name = form_source.get("current_preview_dish_name", "")
    meal_date = form_source.get("meal_date", "").strip() or _today()
    selected_dish = next((dish for dish in dishes if dish["dish_name"] == selected_dish_name), None)
    preview_dish = None
    selected_rotis = form_source.get("rotis", "0").strip() or "0"
    editing_meal = None
    error = None
    nutrition_item_saved = request.args.get("nutrition_item_saved", "").strip()

    if request.method == "GET" and request.args.get("preview", "") == "1" and selected_dish is not None:
        preview_dish = selected_dish

    if request.method == "POST":
        action = request.form.get("action", "preview")
        try:
            if action == "delete":
                _delete_entry(user_data["meal_log"], int(request.form["meal_id"]))
                _rebuild_daily_nutrition(user_data)
                return redirect(url_for("analyze"))

            if action == "edit":
                editing_meal = _find_entry(
                    user_data["meal_log"], int(request.form["meal_id"])
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
                    nutrition_db=nutrition_db,
                )
                if meal_id:
                    entry = _find_entry(user_data["meal_log"], int(meal_id))
                    if entry is None:
                        user_data["meal_log"].append(payload)
                    else:
                        entry.update(payload)
                else:
                    payload["id"] = _next_id(user_data["meal_log"])
                    user_data["meal_log"].append(payload)
                _rebuild_daily_nutrition(user_data)
                return redirect(url_for("analyze", meal_date=meal_date))
        except Exception as exc:
            error = str(exc)

    logged_for_date = next(
        (entry for entry in user_data["nutrition_log"] if entry["date"] == meal_date),
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
        roti_nutrition_per_piece=_roti_nutrition(1, nutrition_db),
        meal_date=meal_date,
        logged_for_date=logged_for_date,
        logged_dishes_display=logged_dishes_display,
        meal_log=sorted(user_data["meal_log"], key=lambda item: (item["date"], item["id"])),
        editing_meal=editing_meal,
        error=error,
        nutrition_item_saved=nutrition_item_saved,
    )


@app.route("/nutrition-item", methods=["POST"])
def nutrition_item():
    login_check = _require_login()
    if login_check:
        return login_check

    user_data = _get_current_user_data()
    item_name = request.form.get("item_name", "").strip().lower()
    dish_name = request.form.get("dish_name", "").strip()
    meal_date = request.form.get("meal_date", "").strip() or _today()

    if not item_name:
        return redirect(url_for("analyze", dish_name=dish_name, meal_date=meal_date, preview="1"))

    unit = request.form.get("unit", "kilograms").strip().lower()
    if unit not in {"kilograms", "litres", "pieces"}:
        unit = "kilograms"

    try:
        calories = float(request.form.get("calories", "").strip())
        protein = float(request.form.get("protein", "").strip())
        carbs = float(request.form.get("carbs", "").strip())
        fat = float(request.form.get("fat", "").strip())
        if any(value < 0 for value in (calories, protein, carbs, fat)):
            raise ValueError
    except ValueError:
        return redirect(url_for("analyze", dish_name=dish_name, meal_date=meal_date, preview="1"))

    # Convert from per-kg/litre to internal per-100g/100ml; pieces stay as-is.
    storage_factor = 1.0 if unit == "pieces" else 0.1
    custom_db = user_data.setdefault("custom_nutrition_db", {})
    custom_db[item_name] = {
        "calories": round(calories * storage_factor, 4),
        "protein": round(protein * storage_factor, 4),
        "carbs": round(carbs * storage_factor, 4),
        "fat": round(fat * storage_factor, 4),
    }

    return redirect(
        url_for(
            "analyze",
            dish_name=dish_name,
            meal_date=meal_date,
            preview="1",
            nutrition_item_saved=item_name,
        )
    )


@app.route("/track", methods=["GET", "POST"])
def track():
    login_check = _require_login()
    if login_check:
        return login_check
    
    user_data = _get_current_user_data()
    result = None
    editing_weight = None
    editing_steps = None
    editing_exercise = None

    if request.method == "POST":
        action = request.form.get("action", "add")

        if action == "delete_weight":
            _delete_entry(user_data["weight_log"], int(request.form["weight_id"]))
            return redirect(url_for("track"))

        if action == "delete_steps":
            _delete_entry(user_data["steps_log"], int(request.form["steps_id"]))
            return redirect(url_for("track"))

        if action == "delete_exercise":
            _delete_entry(user_data.setdefault("exercise_log", []), int(request.form["exercise_id"]))
            return redirect(url_for("track"))

        if action == "edit_weight":
            editing_weight = _find_entry(
                user_data["weight_log"], int(request.form["weight_id"])
            )

        if action == "edit_steps":
            editing_steps = _find_entry(
                user_data["steps_log"], int(request.form["steps_id"])
            )

        if action == "edit_exercise":
            editing_exercise = _find_entry(
                user_data.setdefault("exercise_log", []), int(request.form["exercise_id"])
            )

        if action == "save_weight":
            date = request.form.get("weight_date", _today()).strip() or _today()
            weight = request.form.get("weight", "").strip()
            if weight:
                entry_id = request.form.get("weight_id", "").strip()
                result = _upsert_weight(user_data, date, float(weight), int(entry_id) if entry_id else None)
                return redirect(url_for("track"))

        if action == "save_steps":
            date = request.form.get("steps_date", _today()).strip() or _today()
            steps = request.form.get("steps", "").strip()
            if steps:
                entry_id = request.form.get("steps_id", "").strip()
                result = _upsert_steps(user_data, date, int(steps), int(entry_id) if entry_id else None)
                return redirect(url_for("track"))

        if action == "save_exercise":
            date = request.form.get("exercise_date", _today()).strip() or _today()
            ex_type = request.form.get("exercise_type", "pushups").strip()
            reps_raw = request.form.get("reps", "").strip()
            if reps_raw and ex_type in fitness_analysis.CALORIES_PER_REP:
                entry_id = request.form.get("exercise_id", "").strip()
                _upsert_exercise(user_data, date, ex_type, int(reps_raw), int(entry_id) if entry_id else None)
                return redirect(url_for("track"))

        if action == "save_height":
            height_feet_raw = request.form.get("height_feet", "").strip()
            height_inches_raw = request.form.get("height_inches", "").strip()
            try:
                height_feet = int(height_feet_raw)
                height_inches = int(height_inches_raw)
                if 1 <= height_feet <= 9 and 0 <= height_inches <= 11:
                    height_cm = round(((height_feet * 12) + height_inches) * 2.54, 1)
                    user_data.setdefault("profile", {}).update({
                        "height_cm": height_cm,
                        "height_feet": height_feet,
                        "height_inches": height_inches,
                    })
            except (ValueError, TypeError):
                pass
            return redirect(url_for("track") + "#height-form")

    profile = user_data.get("profile", {})
    latest_weight = None
    if user_data["weight_log"]:
        latest_weight_entry = max(
            user_data["weight_log"],
            key=lambda item: (item.get("date", ""), item.get("id", 0)),
        )
        latest_weight = latest_weight_entry.get("weight")

    bmi = None
    bmi_category = None
    bmi_note = None
    ideal_weight_range = None
    height_cm = profile.get("height_cm") if profile else None
    if latest_weight is not None and height_cm:
        height_m = float(height_cm) / 100
        if height_m > 0:
            bmi = round(float(latest_weight) / (height_m * height_m), 2)
            ideal_low = round(18.5 * (height_m * height_m), 1)
            ideal_high = round(24.9 * (height_m * height_m), 1)
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
        "track.html",
        result=result,
        today=_today(),
        weight_log=sorted(user_data["weight_log"], key=lambda item: (item["date"], item["id"])),
        steps_log=sorted(user_data["steps_log"], key=lambda item: (item["date"], item["id"])),
        exercise_log=sorted(user_data.get("exercise_log", []), key=lambda item: (item["date"], item["id"])),
        editing_weight=editing_weight,
        editing_steps=editing_steps,
        editing_exercise=editing_exercise,
        profile=profile,
        latest_weight=latest_weight,
        bmi=bmi,
        bmi_category=bmi_category,
        bmi_note=bmi_note,
        ideal_weight_range=ideal_weight_range,
    )


@app.route("/fasting", methods=["GET", "POST"])
def fasting():
    login_check = _require_login()
    if login_check:
        return login_check
    
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


@app.route("/graph", methods=["GET", "POST"])
def graph():
    login_check = _require_login()
    if login_check:
        return login_check
    
    user_data = _get_current_user_data()
    profile = user_data.setdefault("profile", {})

    if request.method == "POST":
        raw_target = request.form.get("daily_calories_target", "").strip()
        if raw_target:
            try:
                parsed_target = int(raw_target)
                if 500 <= parsed_target <= 10000:
                    profile["daily_calories_target"] = parsed_target
            except ValueError:
                pass
        else:
            profile["daily_calories_target"] = None
        return redirect(url_for("graph", saved="1"))

    current_target = profile.get("daily_calories_target") or DAILY_TARGETS["calories"]
    graph_data = _build_graph_rows(user_data)
    graph_url = None

    if graph_data:
        static_dir = Path(app.root_path) / "static"
        static_dir.mkdir(exist_ok=True)
        graph_path = static_dir / "progress_graph.png"

        dates = [row["date"] for row in graph_data]
        weights = [row["weight"] if row["weight"] is not None else float("nan") for row in graph_data]
        net_calories = [
            row["net_calories"] if row["net_calories"] is not None else float("nan")
            for row in graph_data
        ]

        fig, ax1 = plt.subplots(figsize=(11, 5.6), dpi=140)
        ax1.plot(
            dates,
            weights,
            color="#2563eb",
            marker="o",
            linewidth=2.2,
            markersize=5,
            label="Weight (kg)",
        )
        ax1.set_xlabel("Date", color="#0f172a")
        ax1.set_ylabel("Weight (kg)", color="#2563eb")
        ax1.tick_params(axis="y", labelcolor="#2563eb")
        ax1.tick_params(axis="x", rotation=35, labelsize=8)
        ax1.grid(axis="y", linestyle="--", alpha=0.28)

        ax2 = ax1.twinx()
        ax2.plot(
            dates,
            net_calories,
            color="#16a34a",
            marker="^",
            linestyle="-",
            linewidth=2.2,
            markersize=5,
            label="Net Calories",
        )
        ax2.set_ylabel("Net Calories", color="#16a34a")
        ax2.tick_params(axis="y", labelcolor="#16a34a")

        lines_1, labels_1 = ax1.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper left")
        plt.title("Weight and Net Calories Over Time", fontsize=12, fontweight="bold")
        fig.tight_layout()
        fig.savefig(graph_path, dpi=160, bbox_inches="tight")
        plt.close(fig)
        graph_url = url_for("static", filename="progress_graph.png")

    return render_template(
        "graph.html",
        graph_data=graph_data,
        graph_url=graph_url,
        current_target=current_target,
        target_saved=request.args.get("saved") == "1",
    )


if __name__ == "__main__":
    app.run(debug=True)
