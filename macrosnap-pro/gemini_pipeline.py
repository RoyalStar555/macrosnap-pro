import os
import io
import json
import time
import re
import logging
from typing import Optional
from PIL import Image, ImageOps
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from pydantic import BaseModel, Field
import streamlit as st
from logger import log_execution_time

logger = logging.getLogger("MacroSnap")

MAX_RETRIES = 1
REQUEST_TIMEOUT = 20.0  # 20-second timeout per model call to avoid hanging UI


# ── Pydantic schema with is_food guardrail & backward compatibility ────────

class MealMacros(BaseModel):
    is_food: bool = Field(default=True, description="True if the image contains food, False otherwise.")
    food_name: str = Field(description="Name of the identified food or meal.")
    total_calories: int = Field(description="Estimated total calories in kcal.")
    protein_g: float = Field(description="Estimated protein in grams.")
    carbs_g: float = Field(description="Estimated carbohydrates in grams.")
    fat_g: float = Field(description="Estimated fat in grams.")
    confidence_score: Optional[float] = Field(default=1.0, description="Confidence score between 0.0 and 1.0.")

    @property
    def calories(self) -> int:
        return self.total_calories


# ── Config helpers ───────────────────────────────────────────────────────────

def _get_model_name() -> str:
    """Pull primary model name from Streamlit secrets, env var, or valid default."""
    try:
        return st.secrets.get("GEMINI_MODEL", os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))
    except Exception:
        return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def _get_gemini_key() -> str:
    """Safely fetch API key across Streamlit Cloud and local environments."""
    key = None
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass
    return key or os.environ.get("GEMINI_API_KEY", "")


def _get_client() -> genai.Client:
    """Create a Gemini client with a global HTTP timeout."""
    key = _get_gemini_key()
    if not key:
        raise ValueError("GEMINI_API_KEY is not set in secrets or environment variables.")
    return genai.Client(
        api_key=key,
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT),
    )


def _get_fallback_chain() -> list[str]:
    """Generates an ordered, valid fallback model chain."""
    primary = _get_model_name()
    candidates = [primary, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    seen = set()
    return [m for m in candidates if not (m in seen or seen.add(m))]


# ── Image preprocessing ─────────────────────────────────────────────────────

def _optimize_image(image_bytes: bytes) -> Image.Image:
    """Fix EXIF rotation, resize to 768px max, return PIL Image object."""
    img = Image.open(io.BytesIO(image_bytes))

    # Fix mobile photo orientation metadata
    img = ImageOps.exif_transpose(img)

    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    img.thumbnail((768, 768), Image.Resampling.LANCZOS)
    return img


# ── Public API ───────────────────────────────────────────────────────────────

@log_execution_time
def process_meal_fast(image_bytes: bytes) -> Optional[MealMacros]:
    """
    High-speed vision pipeline: preprocess -> Gemini generate_content -> validated Pydantic model.
    """
    try:
        client = _get_client()
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize Gemini Client: {e}")
        return None

    try:
        pil_image = _optimize_image(image_bytes)
    except Exception as e:
        logger.error(f"[ERROR] Image optimization failed: {e}")
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
        logger.info(f"[INFO] Attempting meal analysis with model: {model_name}")
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
                logger.warning(f"[WARNING] Model {model_name} attempt {attempt} failed: {e}")

    logger.error(f"[ERROR] All models in fallback chain failed. Last error: {last_error}")
    return None


@log_execution_time
def generate_weekly_deep_dive(daily_logs: list, user_profile: dict) -> dict:
    """Generates an executive summary and health action plan."""
    try:
        client = _get_client()
    except Exception as e:
        logger.error(f"[ERROR] Client init failed for deep dive: {e}")
        return {
            "executive_summary": "Unable to initialize AI service.",
            "health_warnings": ["Check GEMINI_API_KEY configuration."],
            "action_plan": ["Verify your API keys in Streamlit Secrets."],
        }

    prompt = (
        "You are an elite dietician. Analyze the client profile vs today's meal logs. "
        "Respond ONLY in valid JSON.\n"
        f"PROFILE: {json.dumps(user_profile)}\n"
        f"LOGS: {json.dumps(daily_logs)}\n"
        'Required schema: '
        '{"executive_summary": "2 sentence summary", "health_warnings": ["warning 1"], '
        '"action_plan": ["action 1", "action 2", "action 3"]}'
    )

    models_to_try = _get_fallback_chain()
    last_error = None

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
            last_error = e
            logger.warning(f"[WARNING] Deep dive model {model_name} error: {e}")
            continue

    logger.error(f"[ERROR] All models failed deep dive. Last error: {last_error}")
    return {
        "executive_summary": "Unable to generate summary due to temporary AI service overload.",
        "health_warnings": ["AI analysis temporarily unavailable."],
        "action_plan": ["Continue tracking your daily macros and check back later."],
    }
