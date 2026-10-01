import streamlit as st

def apply_custom_theme():
    """
    Global theme (background, text color, primary color) is handled by
    .streamlit/config.toml — do NOT override .stApp or base text here,
    otherwise widget labels and inputs become invisible.
    """
    css = """
    <style>
    .glass-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px; 
        padding: 24px; 
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .metric-box {
        text-align: center; 
        padding: 16px;
        background: rgba(15, 23, 42, 0.6);
        border-radius: 12px; 
        border-left: 4px solid #38bdf8;
        transition: transform 0.2s ease;
    }
    .metric-box:hover { 
        transform: translateY(-2px); 
    }
    .metric-title { 
        font-size: 0.85rem; 
        color: #94a3b8; 
        text-transform: uppercase; 
        letter-spacing: 0.05em; 
    }
    .metric-value { 
        font-size: 2rem; 
        font-weight: 700; 
        color: #38bdf8; 
        margin: 8px 0; 
    }
    .metric-subtext { 
        font-size: 0.75rem; 
        color: #64748b; 
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def render_metric_card(label: str, value: str, subtext: str = ""):
    html = f"""
    <div class="metric-box">
        <div class="metric-title">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-subtext">{subtext}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
