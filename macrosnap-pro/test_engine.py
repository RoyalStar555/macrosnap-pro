import pytest
from tdee import calculate_biometrics
from pdf_generator import generate_macro_donut_chart, build_pdf_report

def test_calculate_biometrics_male_weight_loss():
    result = calculate_biometrics(age=25, gender="Male", height_cm=180.0, weight_kg=80.0, activity="Moderately Active", goal="Weight Loss")
    assert "tdee" in result
    assert result["calorie_target"] == result["tdee"] - 500
    assert result["protein_target_g"] > 0

def test_calculate_biometrics_female_maintenance():
    result = calculate_biometrics(age=30, gender="Female", height_cm=165.0, weight_kg=60.0, activity="Sedentary", goal="Maintenance")
    assert result["calorie_target"] == result["tdee"]

def test_chart_generation_returns_bytes():
    macros = {"protein": 30, "carbs": 40, "fat": 20}
    chart_stream = generate_macro_donut_chart(macros)
    assert chart_stream.getbuffer().nbytes > 0

def test_pdf_builder_outputs_pdf_signature():
    user = {"name": "Test User", "protein_target_g": 150, "carb_target_g": 200, "fat_target_g": 60}
    macros = {"protein": 140, "carbs": 180, "fat": 50}
    ai_analysis = {"executive_summary": "Test summary", "health_warnings": [], "action_plan": ["Action 1"]}
    pdf_bytes = build_pdf_report(user, macros, ai_analysis)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")
