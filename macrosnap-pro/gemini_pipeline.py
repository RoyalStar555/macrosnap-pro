import io
import json
import os
import logging
from typing import Optional
from PIL import Image
from pydantic import BaseModel
from google import genai
from google.genai import types

from logger import log_execution_time

MAX_RETRIES = 1

class MealMacros(BaseModel):
    is_food: bool
    food_name: str
    total_calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence_score: float

def _get_fallback_chain():
    """Returns the list of Gemini models to try in order."""
    return ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

def _optimize_image(image_bytes: bytes) -> Image.Image:
    """Optimizes image size for high-speed vision pipeline."""
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((1024, 1024))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

@log_execution_time
def process_meal_fast(image_bytes: bytes) -> Optional[MealMacros]:
    """
    High-speed vision pipeline: preprocess -> Gemini generate_content -> validated Pydantic model.
    """
    try:
        # Initialize client directly with a 60-second timeout (picks up GEMINI_API_KEY automatically)
        client = genai.Client(http_options={'timeout': 60.0})
    except Exception as e:
        logging.error(f"[ERROR] Failed to initialize Gemini Client: {e}")
        return None

    try:
        pil_image = _optimize_image(image_bytes)
    except Exception as e:
        logging.error(f"[ERROR] Image optimization failed: {e}")
        return None

    prompt = (
        "You are an expert dietician. Analyze this meal image and respond ONLY with a JSON object containing:\n"
        "- 'is_food': boolean (false if not food/drink)\n"
        "- 'food_name': string (name of food or 'Unknown')\n"
        "- 'total_calories': integer\n"
        "- 'protein_g': float\n"
        "- 'carbs_g': float\n"
        "- 'fat_g': float\n"
        "- 'confidence_score': float (0.0 to 1.0)\n\n"
        "If not food, set 'is_food' to false and 0 for numeric fields."
    )

    models_to_try = _get_fallback_chain()
    last_error = None

    for model_name in models_to_try:
        logging.info(f"[INFO] Attempting meal analysis with model: {model_name}")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[pil_image, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                
                if response and response.text:
                    clean_text = response.text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_text)
                    return MealMacros(**data)

            except Exception as e:
                last_error = e
                logging.warning(f"[WARNING] Model {model_name} attempt {attempt} failed: {e}")

    logging.error(f"[ERROR] All models in fallback chain failed. Last error: {last_error}")
    return None

@log_execution_time
def generate_weekly_deep_dive(logs: list, user: dict) -> dict:
    """
    Generates a weekly health and nutrition deep dive report using Gemini.
    """
    try:
        client = genai.Client(http_options={'timeout': 60.0})
        
        prompt = (
            "You are an expert clinical dietician. Analyze the user profile and their recent meal logs, "
            "and respond ONLY with a JSON object containing:\n"
            "- 'executive_summary': string (overview of their weekly trends)\n"
            "- 'health_warnings': list of strings (potential nutritional gaps or excessive intake warnings)\n"
            "- 'action_plan': list of strings (actionable steps for next week)\n\n"
            f"User Profile: {user}\n"
            f"Meal Logs: {logs}"
        )
        
        models_to_try = _get_fallback_chain()
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                if response and response.text:
                    clean_text = response.text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean_text)
            except Exception as e:
                logging.warning(f"[WARNING] Weekly deep dive with {model_name} failed: {e}")

        # Safe fallback dictionary if models fail
        return {
            "executive_summary": "You've been consistent with logging! Keep tracking your daily macros to hit your targets.",
            "health_warnings": ["Make sure you are drinking enough water and getting adequate fiber."],
            "action_plan": ["Log every meal consistently", "Aim for a slight increase in lean protein"]
        }

    except Exception as e:
        logging.error(f"[ERROR] generate_weekly_deep_dive failed: {e}")
        return {
            "executive_summary": "Could not generate report due to a technical error.",
            "health_warnings": [],
            "action_plan": ["Please try again later."]
        }
