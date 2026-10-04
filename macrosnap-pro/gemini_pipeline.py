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

def _get_client() -> genai.Client:
    """
    Initializes and returns the Gemini client securely with diagnostic checks.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        logging.error("[CRITICAL] GEMINI_API_KEY or GOOGLE_API_KEY environment variable is MISSING from the runtime environment!")
        raise ValueError("Missing GEMINI_API_KEY environment variable.")
    
    # Log safe diagnostic info (prefix and length) to confirm key is loaded correctly
    logging.info(f"[INFO] Gemini API Key loaded successfully. Prefix: {api_key[:4]}... Length: {len(api_key)}")
    
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=120000)
    )

def _get_fallback_chain():
    """Returns the ordered list of high-performance Gemini models to try in sequence."""
    return ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

def _optimize_image(image_bytes: bytes) -> bytes:
    """
    Downscales image resolution to a maximum bounding box of 512x512 pixels 
    and compresses to JPEG format at 80% quality to eliminate write timeouts.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((512, 512))
        if img.mode != "RGB":
            img = img.convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=80)
        return buffer.getvalue()
    except Exception as e:
        logging.error(f"[ERROR] Image preprocessing and compression failed: {e}")
        raise

@log_execution_time
def process_meal_fast(image_bytes: bytes) -> Optional[MealMacros]:
    """
    High-speed multi-modal vision pipeline: preprocesses image -> initializes authenticated Gemini client -> 
    invokes content generation with fallback models -> parses and validates response via Pydantic model.
    """
    try:
        client = _get_client()
    except Exception as e:
        logging.error(f"[ERROR] Failed to initialize authenticated Gemini Client for vision pipeline: {e}")
        return None

    try:
        optimized_image_bytes = _optimize_image(image_bytes)
    except Exception as e:
        logging.error(f"[ERROR] Image optimization pipeline failed: {e}")
        return None

    image_part = types.Part.from_bytes(
        data=optimized_image_bytes,
        mime_type="image/jpeg",
    )

    prompt = (
        "You are an expert clinical dietician and computer vision nutritionist. Analyze this meal image thoroughly and respond ONLY with a valid JSON object containing:\n"
        "- 'is_food': boolean (false if the image does not depict food or beverages)\n"
        "- 'food_name': string (descriptive name of the dish or 'Unknown' if unrecognizable)\n"
        "- 'total_calories': integer (estimated total kilocalories)\n"
        "- 'protein_g': float (grams of protein)\n"
        "- 'carbs_g': float (grams of carbohydrates)\n"
        "- 'fat_g': float (grams of fat)\n"
        "- 'confidence_score': float (confidence rating from 0.0 to 1.0)\n\n"
        "If the image is not food, set 'is_food' to false and all numeric macro fields to 0."
    )

    models_to_try = _get_fallback_chain()
    last_error = None

    for model_name in models_to_try:
        logging.info(f"[INFO] Attempting meal vision analysis using model: {model_name}")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[image_part, prompt],
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
                logging.warning(f"[WARNING] Model {model_name} attempt {attempt} failed [{type(e).__name__}]: {e}")

    logging.error(f"[ERROR] All models in the fallback chain failed for process_meal_fast. Last error: {last_error}")
    return None

@log_execution_time
def generate_weekly_deep_dive(logs: list, user: dict) -> dict:
    """
    Generates a comprehensive weekly health, nutrition, and trend deep dive report 
    by analyzing the user profile and historical meal logs through Gemini.
    """
    try:
        client = _get_client()
    except Exception as e:
        logging.error(f"[ERROR] Failed to initialize authenticated Gemini Client for weekly deep dive: {e}")
        return {
            "executive_summary": "Could not generate report due to authentication configuration errors.",
            "health_warnings": ["Check environment secrets and API keys."],
            "action_plan": ["Please verify system configurations and try again later."]
        }
        
    prompt = (
        "You are an expert clinical dietician and health coach. Analyze the user profile and their recent weekly meal logs, "
        "and respond ONLY with a JSON object containing:\n"
        "- 'executive_summary': string (comprehensive overview of their weekly nutritional trends and caloric adherence)\n"
        "- 'health_warnings': list of strings (potential nutritional gaps, micronutrient deficiencies, or excessive intake warnings)\n"
        "- 'action_plan': list of strings (actionable, evidence-based steps for the upcoming week)\n\n"
        f"User Profile: {json.dumps(user, default=str)}\n"
        f"Meal Logs: {json.dumps(logs, default=str)}"
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
            logging.warning(f"[WARNING] Weekly deep dive report generation with model {model_name} failed: {e}")

    return {
        "executive_summary": "You've demonstrated consistent engagement with logging your meals! Continue tracking your daily macros diligently to hit your target metrics.",
        "health_warnings": ["Ensure adequate hydration throughout the day and sufficient dietary fiber intake."],
        "action_plan": [
            "Log every meal consistently without omissions",
            "Aim for a slight, sustainable increase in lean protein sources across meals"
        ]
    }
