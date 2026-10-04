import streamlit as st
from PIL import Image
import io
import plotly.express as px
import pandas as pd

from ui_styles import apply_custom_theme, render_metric_card
from tdee import calculate_biometrics
from db import get_user_by_whatsapp, create_user_profile, get_daily_logs, log_meal_db
from gemini_pipeline import process_meal_fast, generate_weekly_deep_dive
from pdf_generator import build_pdf_report
import logger

# Page configuration
st.set_page_config(
    page_title="MacroSnap Pro",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_custom_theme()

st.title("🥗 MacroSnap Pro")
st.caption("AI-Powered Vision & Daily Macro Tracker")

# Sidebar - User Identity
st.sidebar.header("User Identification")
whatsapp_num = st.sidebar.text_input("WhatsApp Phone Number", value="+1234567890")

if whatsapp_num:
    user = get_user_by_whatsapp(whatsapp_num)
    if not user:
        st.sidebar.info("User not found. Creating a default profile...")
        user = create_user_profile(
            whatsapp_number=whatsapp_num,
            age=30,
            gender="male",
            weight_kg=75.0,
            height_cm=175.0,
            activity_level="moderate",
            goal="maintain"
        )

# Main Navigation Tabs
tab1, tab2, tab3 = st.tabs(["📸 AI Vision Logger", "📊 Daily Dashboard", "📄 Weekly Report"])

# ── TAB 1: AI Vision Logger ──────────────────────────────────────────────────
with tab1:
    st.header("Upload Meal Photo")
    uploaded_file = st.file_uploader("Choose a meal image...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        image = Image.open(io.BytesIO(image_bytes))
        st.image(image, caption="Uploaded Meal", width=400)

        if st.button("Analyze with AI 🚀"):
            with st.spinner("Analyzing image with Gemini Vision..."):
                meal = process_meal_fast(image_bytes)

            # ── STRICT NULL-CHECK GUARDRAILS ──
            if meal is None:
                st.error("⚠️ AI Vision analysis failed or timed out. Please check your Gemini API key and app logs.")
            elif not meal.is_food:
                st.warning("⚠️ No food detected in the uploaded image. Please upload a clear photo of a meal.")
            else:
                st.success(f"Identified: **{meal.food_name}**")
                
                # Metrics Row
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Calories", f"{meal.total_calories} kcal")
                col2.metric("Protein", f"{meal.protein_g} g")
                col3.metric("Carbs", f"{meal.carbs_g} g")
                col4.metric("Fat", f"{meal.fat_g} g")

                # Macro Pie Chart
                macro_data = pd.DataFrame({
                    "Nutrient": ["Protein", "Carbs", "Fat"],
                    "Grams": [meal.protein_g, meal.carbs_g, meal.fat_g]
                })
                fig = px.pie(macro_data, values="Grams", names="Nutrient", title="Macro Split", hole=0.4)
                st.plotly_chart(fig, width="stretch")

                # Save to Database
                if user:
                    log_meal_db(
                        user_id=user["id"],
                        food_name=meal.food_name,
                        calories=meal.total_calories,
                        protein_g=meal.protein_g,
                        carbs_g=meal.carbs_g,
                        fat_g=meal.fat_g
                    )
                    st.balloons()
                    st.success("Meal logged to database successfully!")

# ── TAB 2: Daily Dashboard ───────────────────────────────────────────────────
with tab2:
    st.header("Daily Summary")
    if user:
        logs = get_daily_logs(user["id"])
        if logs:
            df = pd.DataFrame(logs)
            st.dataframe(df, width="stretch")
            
            total_cals = sum(item["calories"] for item in logs)
            total_protein = sum(item["protein_g"] for item in logs)
            total_carbs = sum(item["carbs_g"] for item in logs)
            total_fat = sum(item["fat_g"] for item in logs)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Calories", f"{total_cals} kcal")
            m2.metric("Total Protein", f"{total_protein} g")
            m3.metric("Total Carbs", f"{total_carbs} g")
            m4.metric("Total Fat", f"{total_fat} g")
        else:
            st.info("No meals logged for today yet.")

# ── TAB 3: Weekly Report ─────────────────────────────────────────────────────
with tab3:
    st.header("AI Deep Dive Report")
    if st.button("Generate Deep Dive 📈"):
        if user:
            logs = get_daily_logs(user["id"])
            with st.spinner("Generating insights..."):
                report = generate_weekly_deep_dive(logs, user)
                
                st.subheader("Executive Summary")
                st.write(report.get("executive_summary", "N/A"))

                st.subheader("Health Warnings")
                for warning in report.get("health_warnings", []):
                    st.warning(warning)

                st.subheader("Action Plan")
                for action in report.get("action_plan", []):
                    st.write(f"- {action}")
