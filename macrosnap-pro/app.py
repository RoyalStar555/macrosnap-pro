import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from ui_styles import apply_custom_theme, render_metric_card
from tdee import calculate_biometrics
from db import get_user_by_whatsapp, create_user_profile, get_daily_logs, get_supabase_client
from gemini_pipeline import process_meal_fast, generate_weekly_deep_dive
from pdf_generator import build_pdf_report
import logger

# Page config
st.set_page_config(page_title="MacroSnap Pro", page_icon="🥗", layout="wide")
apply_custom_theme()

# Session state initialization
if "user" not in st.session_state:
    st.session_state.user = None

# ── Sidebar: Login ──────────────────────────────────────────────────────────
st.sidebar.title("🥗 MacroSnap Pro")
st.sidebar.markdown("---")
phone = st.sidebar.text_input("WhatsApp Number (Include Country Code, e.g., +1234):")

if st.sidebar.button("Login", use_container_width=True):
    if not phone.strip():
        st.sidebar.warning("Please enter a valid phone number.")
    else:
        with st.spinner("Authenticating..."):
            user = get_user_by_whatsapp(phone.strip())
            if user:
                st.session_state.user = user
                st.sidebar.success(f"Welcome back, {user.get('name', 'User')}!")
            else:
                st.sidebar.error("Profile not found. Please setup a profile.")

t1, t2, t3, t4 = st.tabs(["👤 Profile Setup", "📸 AI Vision Logger", "📊 Daily Dashboard", "📄 PDF Hub"])

# ── Tab 1: Profile Setup ────────────────────────────────────────────────────
with t1:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Create or Update Profile")

    curr = st.session_state.user or {}

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full Name", value=curr.get("name", ""))
        age = st.number_input("Age", min_value=10, max_value=120, value=int(curr.get("age", 25)))
        gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=0)
        height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=float(curr.get("height_cm", 170.0)))

    with col2:
        weight = st.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=float(curr.get("weight_kg", 70.0)))
        act = st.selectbox(
            "Activity Level",
            ["Sedentary", "Lightly Active", "Moderately Active", "Very Active"],
            index=0,
        )
        goal = st.selectbox(
            "Goal",
            ["Weight Loss", "Maintenance", "Muscle Gain"],
            index=0,
        )
        whatsapp_input = st.text_input("WhatsApp Number (+1234...)", value=curr.get("whatsapp_number", phone))

    if st.button("Save & Generate Targets", type="primary", use_container_width=True):
        if not name or not whatsapp_input:
            st.error("Please fill out all required fields.")
        else:
            with st.spinner("Calculating biometrics and saving profile..."):
                # Signature: calculate_biometrics(age, gender, height_cm, weight_kg, activity, goal)
                biometrics = calculate_biometrics(age, gender, height, weight, act, goal)

                profile_data = {
                    "whatsapp_number": whatsapp_input.strip(),
                    "name": name,
                    "full_name": name,
                    "age": int(age),
                    "gender": gender,
                    "height_cm": float(height),
                    "weight_kg": float(weight),
                    "activity_level": act,
                    "goal": goal,
                    "tdee": biometrics["tdee"],
                    "calorie_target": biometrics["calorie_target"],
                    "protein_target_g": biometrics["protein_target_g"],
                    "carb_target_g": biometrics["carb_target_g"],
                    "fat_target_g": biometrics["fat_target_g"],
                }

                saved_user = create_user_profile(profile_data)
                if saved_user:
                    st.session_state.user = saved_user
                    st.success("Profile saved successfully!")
                else:
                    st.error("Failed to save profile to database.")
    st.markdown("</div>", unsafe_allow_html=True)

# ── Tab 2: AI Vision Logger ────────────────────────────────────────────────
with t2:
    st.subheader("Snap & Log")
    st.markdown("Upload a photo of your meal to automatically extract macros.")

    uploaded_file = st.file_uploader("Upload Meal Photo", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Meal", use_container_width=True)

        if st.button("Analyze with AI 🚀", use_container_width=True, type="primary"):
            if not st.session_state.user:
                st.error("Please log in or set up a profile before logging meals.")
            else:
                with st.status("Processing meal...", expanded=True) as status:
                    try:
                        st.write("🗜️ Optimizing image payload...")
                        image_bytes = uploaded_file.getvalue()

                        st.write("🧠 Analyzing macros with Gemini Flash...")
                        macros = process_meal_fast(image_bytes)

                        if not macros.is_food:
                            status.update(label="Analysis Failed", state="error", expanded=True)
                            st.error("No food detected in this image. Please upload a clear photo of a meal.")
                        else:
                            st.write("💾 Saving log to database...")
                            supabase = get_supabase_client()

                            meal_entry = {
                                "user_id": st.session_state.user["id"],
                                "food_name": macros.food_name,
                                "calories": macros.total_calories,
                                "protein_g": macros.protein_g,
                                "carbs_g": macros.carbs_g,
                                "fat_g": macros.fat_g,
                            }

                            supabase.table("meal_logs").insert(meal_entry).execute()
                            status.update(label="Analysis Complete!", state="complete", expanded=False)

                            st.success(f"**Logged:** {macros.food_name}")

                            fig = go.Figure(data=[go.Pie(
                                labels=["Protein", "Carbs", "Fat"],
                                values=[macros.protein_g, macros.carbs_g, macros.fat_g],
                                hole=0.6,
                                marker_colors=["#ef4444", "#3b82f6", "#eab308"],
                                textinfo="label+percent",
                            )])
                            fig.update_layout(
                                height=200,
                                margin=dict(t=0, b=0, l=0, r=0),
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                showlegend=False,
                                font=dict(color="#f8fafc"),
                            )

                            c1, c2 = st.columns([1, 2])
                            with c1:
                                st.plotly_chart(fig, use_container_width=True)
                            with c2:
                                m1, m2, m3, m4 = st.columns(4)
                                m1.metric("Calories", f"{macros.total_calories} kcal")
                                m2.metric("Protein", f"{macros.protein_g}g")
                                m3.metric("Carbs", f"{macros.carbs_g}g")
                                m4.metric("Fat", f"{macros.fat_g}g")

                            st.balloons()

                    except Exception as e:
                        status.update(label="Analysis Failed", state="error", expanded=True)
                        st.error(f"Error: {str(e)}")

# ── Tab 3: Daily Dashboard ──────────────────────────────────────────────────
with t3:
    st.subheader("Daily Macro Tracking")
    if not st.session_state.user:
        st.info("Log in from the sidebar to view your daily metrics.")
    else:
        logs = get_daily_logs(st.session_state.user["id"])
        if not logs:
            st.warning("No meal logs recorded for today yet.")
        else:
            df = pd.DataFrame(logs)

            total_cal = df["calories"].sum()
            total_pro = df["protein_g"].sum()
            total_carbs = df["carbs_g"].sum()
            total_fat = df["fat_g"].sum()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Calories", f"{total_cal:.0f} kcal")
            m2.metric("Total Protein", f"{total_pro:.1f}g")
            m3.metric("Total Carbs", f"{total_carbs:.1f}g")
            m4.metric("Total Fat", f"{total_fat:.1f}g")

            st.dataframe(
                df[["food_name", "calories", "protein_g", "carbs_g", "fat_g"]],
                use_container_width=True,
            )

# ── Tab 4: PDF Hub ──────────────────────────────────────────────────────────
with t4:
    st.subheader("Intelligence Reports")
    if not st.session_state.user:
        st.info("Log in from the sidebar to generate reports.")
    else:
        if st.button("Generate Weekly PDF Report", type="primary", use_container_width=True):
            with st.spinner("Compiling PDF report..."):
                logs = get_daily_logs(st.session_state.user["id"])

                if not logs:
                    st.warning("You need at least one meal log today to generate a report.")
                else:
                    df = pd.DataFrame(logs)
                    macros_dict = {
                        "protein": df["protein_g"].sum(),
                        "carbs": df["carbs_g"].sum(),
                        "fat": df["fat_g"].sum(),
                    }

                    deep_dive = generate_weekly_deep_dive(logs, st.session_state.user)

                    # Signature: build_pdf_report(user_profile, nutrition_data, ai_analysis)
                    pdf_bytes = build_pdf_report(st.session_state.user, macros_dict, deep_dive)

                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_bytes,
                        file_name="MacroSnap_Weekly_Report.pdf",
                        mime="application/pdf",
                    )
