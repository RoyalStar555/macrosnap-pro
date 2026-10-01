import os
import base64
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

MAX_RETRIES = 2
RETRY_WAIT_CAP = 25
REQUEST_TIMEOUT = 60.0  # seconds — applied at BOTH client and request level


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
    """Pull primary model name from Streamlit secrets, env var, or default."""
    try:
        return st.secrets.get("GEMINI_MODEL", os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"))
    except FileNotFoundError:
        return os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")


def _get_gemini_key() -> str:
    try:
        return st.secrets["GEMINI_API_KEY"]
    except FileNotFoundError:
        return os.environ.get("GEMINI_API_KEY")


def _get_client() -> genai.Client:
    """Create a Gemini client with a global HTTP timeout."""
    return genai.Client(
        api_key=_get_gemini_key(),
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT),
    )


# ── Retry & Fallback helpers ─────────────────────────────────────────────────

def _parse_retry_delay(error_message: str) -> float:
    """Extract retry delay from a 429 error message, capped at RETRY_WAIT_CAP."""
    match = re.search(r"retry in ([\d.]+)s", str(error_message), re.IGNORECASE)
    delay = float(match.group(1)) if match else 15.0
    return min(delay, RETRY_WAIT_CAP)


def _is_retryable(error_str: str) -> bool:
    """Check if the error is a transient rate-limit or availability issue."""
    return any(kw in error_str for kw in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "timed out", "timeout"])


def _get_fallback_chain() -> list[str]:
    """Generates an ordered, deduplicated fallback model chain."""
    primary = _get_model_name()
    candidates = [primary, "gemini-3.7-flash", "gemini-3.5-flash"]
    seen = set()
    return [m for m in candidates if not (m in seen or seen.add(m))]


# ── Image preprocessing ─────────────────────────────────────────────────────

def _optimize_image(image_bytes: bytes) -> str:
    """Fix EXIF rotation, resize to 768px max, compress to JPEG, return base64."""
    img = Image.open(io.BytesIO(image_bytes))

    # CRITICAL: Fix mobile phone rotation bugs from EXIF orientation metadata
    img = ImageOps.exif_transpose(img)

    # Convert palette / RGBA to RGB for JPEG compatibility
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    # 768px sweet-spot: retains texture detail for the AI, keeps payload < 90KB
    img.thumbnail((768, 768), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=80)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# ── Public API ───────────────────────────────────────────────────────────────

@log_execution_time
def process_meal_fast(image_bytes: bytes) -> Optional[MealMacros]:
    """
    High-speed vision pipeline: preprocess -> Gemini Interactions API -> validated Pydantic model.
    Uses automatic fallback model chain to gracefully bypass server capacity overloads.
    """
    client = _get_client()
    image_b64 = _optimize_image(image_bytes)

    prompt = (
        "Analyze this food image. If it does not contain food, set 'is_food' to false and return 0s for all numeric fields. "
        "If it is food, estimate portion sizes based on standard dinner plates and common serving sizes. "
        "IMPORTANT: Ensure total_calories roughly equals (protein_g * 4) + (carbs_g * 4) + (fat_g * 9). "
        "Respond strictly in accordance with the requested schema."
    )

    models_to_try = _get_fallback_chain()
    last_error = None

    for model_name in models_to_try:
        logger.info(f"[INFO] Attempting meal analysis with model: {model_name}")
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                interaction = client.interactions.create(
                    model=model_name,
                    input=[
                        {"type": "text", "text": prompt},
                        {"type": "image", "data": image_b64, "mime_type": "image/jpeg"},
                    ],
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": MealMacros.model_json_schema(),
                    },
                    timeout=REQUEST_TIMEOUT,
                )
                
                response_text = interaction.output_text
                if response_text:
                    data = json.loads(response_text)
                    return MealMacros(**data)

            except ServerError as se:
                last_error = se
                logger.warning(
                    f"[WARNING] Model {model_name} threw server error ({se.code}): {se.message}. "
                    "Switching to next fallback model..."
                )
                break  # Break out of attempt loop to try next model in fallback chain
            except Exception as e:
                last_error = e
                error_str = str(e)
                if _is_retryable(error_str) and attempt <= MAX_RETRIES:
                    wait = _parse_retry_delay(error_str)
                    logger.warning(f"[WARNING] Model {model_name} transient error (attempt {attempt}/{MAX_RETRIES}). Waiting {wait:.0f}s...")
                    time.sleep(wait)
                else:
                    logger.warning(f"[WARNING] Model {model_name} encountered error: {e}. Switching to next fallback model...")
                    break  # Move to next model in fallback chain

    logger.error(f"[ERROR] All models in fallback chain failed. Last error: {last_error}")
    return None


@log_execution_time
def generate_weekly_deep_dive(daily_logs: list, user_profile: dict) -> dict:
    """Generates an executive summary and health action plan via Interactions API."""
    client = _get_client()

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
            interaction = client.interactions.create(
                model=model_name,
                input=[
                    {"type": "text", "text": prompt},
                ],
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                },
                timeout=REQUEST_TIMEOUT,
            )
            return json.loads(interaction.output_text)
        except ServerError as se:
            last_error = se
            logger.warning(f"[WARNING] Deep dive model {model_name} ServerError: {se.message}. Switching fallback...")
            continue
        except Exception as e:
            last_error = e
            logger.warning(f"[WARNING] Deep dive model {model_name} error: {e}. Switching fallback...")
            continue

    logger.error(f"[ERROR] All models failed deep dive. Last error: {last_error}")
    return {
        "executive_summary": "Unable to generate summary due to temporary AI service overload.",
        "health_warnings": ["AI analysis temporarily unavailable."],
        "action_plan": ["Continue tracking your daily macros and check back later."],
    }
