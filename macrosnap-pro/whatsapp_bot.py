import os
import logging
import requests
from fastapi import FastAPI, Form, Response, Request
from twilio.twiml.messaging_response import MessagingResponse
from db import get_user_by_whatsapp, get_supabase_client
from gemini_pipeline import process_meal_fast

logger = logging.getLogger("MacroSnap")

app = FastAPI(title="MacroSnap WhatsApp Webhook")


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    MediaUrl0: str = Form(None),
    NumMedia: str = Form("0"),
):
    """Webhook triggered by Twilio when user sends a WhatsApp message/photo."""
    resp = MessagingResponse()

    clean_number = From.replace("whatsapp:", "").strip()
    logger.info(f"Incoming WhatsApp from {clean_number}")

    user = get_user_by_whatsapp(clean_number)
    if not user:
        resp.message("⚠️ Unregistered number. Please sign up on the MacroSnap Pro dashboard first.")
        return Response(content=str(resp), media_type="application/xml")

    if int(NumMedia) == 0 or not MediaUrl0:
        resp.message("📸 Please send a photo of your meal to automatically log macros.")
        return Response(content=str(resp), media_type="application/xml")

    try:
        twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        twilio_auth = os.environ.get("TWILIO_AUTH_TOKEN")

        image_response = requests.get(
            MediaUrl0,
            auth=(twilio_sid, twilio_auth) if twilio_sid else None,
            timeout=30,
        )
        if image_response.status_code != 200:
            raise Exception(f"Failed to fetch image from Twilio (HTTP {image_response.status_code}).")

        image_bytes = image_response.content
        macros = process_meal_fast(image_bytes)

        if not macros or not macros.is_food:
            resp.message("🚫 That doesn't look like food or analysis timed out. Please send a clear photo of a meal.")
            return Response(content=str(resp), media_type="application/xml")

        db = get_supabase_client()
        meal_record = {
            "user_id": user["id"],
            "food_name": macros.food_name,
            "calories": macros.total_calories,
            "protein_g": macros.protein_g,
            "carbs_g": macros.carbs_g,
            "fat_g": macros.fat_g,
        }
        db.table("meal_logs").insert(meal_record).execute()

        reply_msg = (
            f"✅ *Logged: {macros.food_name}*\n\n"
            f"🔥 *Calories:* {macros.total_calories} kcal\n"
            f"🥩 *Protein:* {macros.protein_g}g\n"
            f"🍞 *Carbs:* {macros.carbs_g}g\n"
            f"🥑 *Fats:* {macros.fat_g}g\n\n"
            f"Dashboard updated!"
        )
        resp.message(reply_msg)

    except Exception as e:
        logger.error(f"WhatsApp processing error: {str(e)}")
        resp.message("❌ Error processing image. Please try again.")

    return Response(content=str(resp), media_type="application/xml")
