def calculate_biometrics(age: int, gender: str, height_cm: float, weight_kg: float, activity: str, goal: str) -> dict:
    """Calculates Total Daily Energy Expenditure using the Mifflin-St Jeor equation."""
    s = 5 if gender.lower() == "male" else -161
    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + s

    multipliers = {
        "Sedentary": 1.2,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725
    }
    tdee = bmr * multipliers.get(activity, 1.2)

    if goal == "Weight Loss":
        calorie_target = tdee - 500
    elif goal == "Muscle Gain":
        calorie_target = tdee + 300
    else:
        calorie_target = tdee

    return {
        "tdee": round(tdee, 1),
        "calorie_target": round(calorie_target, 1),
        "protein_target_g": round((calorie_target * 0.30) / 4, 1),
        "carb_target_g": round((calorie_target * 0.40) / 4, 1),
        "fat_target_g": round((calorie_target * 0.30) / 9, 1)
    }
