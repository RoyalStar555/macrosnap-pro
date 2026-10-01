# 🥗 MacroSnap Pro

MacroSnap Pro is a high-performance dietary tracking and nutritional intelligence application powered by advanced multimodal AI vision, biometric calculations, and automated reporting.

---

## 🚀 Key Features

* **AI Vision Meal Logging**: Instantly analyze meal photos using Google's Gemini models to extract food names, calories, protein, carbohydrates, and fats with high nutritional accuracy.
* **Resilient Model Fallback Chain**: Features automatic graceful degradation (`gemini-3.8-flash` $\rightarrow$ `gemini-3.7-flash` $\rightarrow$ `gemini-3.5-flash`) to bypass provider-side capacity overloads and 503 errors seamlessly.
* **Dual-Layer Timeout Management**: Equipped with client-level `http_options` and request-level timeouts to prevent socket hangs and infinite retry loops.
* **Biometric & TDEE Calculations**: Automatically computes Total Daily Energy Expenditure (TDEE) and custom macro targets based on user age, gender, height, weight, activity level, and fitness goals.
* **Interactive Daily Dashboard**: Track daily intake metrics with real-time aggregations, interactive Plotly charts, and Supabase-backed persistent storage.
* **Automated Weekly PDF Reports**: Compiles weekly nutritional summaries and AI deep dives into downloadable PDF reports complete with static charts.
* **WhatsApp Bot Integration**: Self-contained webhook integration for logging meals directly via WhatsApp messages.

---

## 🛠️ Tech Stack

* **Frontend & UI**: [Streamlit](https://streamlit.io/) with custom scoped glassmorphism CSS styling and native dark mode support.
* **AI & Vision Pipeline**: Google GenAI SDK (`google-genai`), Pydantic schemas, and EXIF/LANCZOS image optimization.
* **Database & Backend**: Supabase (PostgreSQL), FastAPI (for WhatsApp webhooks).
* **Data Visualization & Reporting**: Plotly, Kaleido, and ReportLab.

---

## ⚙️ Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/RoyalStar555/macrosnap-pro.git](https://github.com/RoyalStar555/macrosnap-pro.git)
   cd macrosnap-pro
