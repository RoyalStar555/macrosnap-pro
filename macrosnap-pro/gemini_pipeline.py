from logger import log_execution_time
# (Include any other necessary imports like json, genai, types, Optional, MealMacros, etc.)

@log_execution_time
def process_meal_fast(image_bytes: bytes) -> Optional[MealMacros]:
    """
    High-speed vision pipeline: preprocess -> Gemini generate_content -> validated Pydantic model.
    """
    try:
        # Get the default client, but explicitly recreate it with a 60-second timeout
        base_client = _get_client()
        client = genai.Client(
            api_key=base_client.api_key, 
            http_options={'timeout': 60.0}
        )
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
