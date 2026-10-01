import io
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from logger import log_execution_time

def generate_macro_donut_chart(macros: dict) -> io.BytesIO:
    values = [macros.get("protein", 1), macros.get("carbs", 1), macros.get("fat", 1)]
    fig = px.pie(names=["Protein", "Carbs", "Fat"], values=values, hole=0.5, color_discrete_sequence=['#0D9488', '#0284C7', '#F59E0B'])
    fig.update_layout(title="Macro Distribution", width=400, height=280, showlegend=True, paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#333333'))
    img_bytes = io.BytesIO()
    fig.write_image(img_bytes, format='png', scale=2)
    img_bytes.seek(0)
    return img_bytes

def generate_target_vs_actual_chart(actual: dict, targets: dict) -> io.BytesIO:
    categories = ['Protein', 'Carbs', 'Fat']
    actual_vals = [actual.get('protein', 0), actual.get('carbs', 0), actual.get('fat', 0)]
    target_vals = [targets.get('protein_target_g', 0), targets.get('carb_target_g', 0), targets.get('fat_target_g', 0)]
    fig = go.Figure(data=[
        go.Bar(name='Actual', x=categories, y=actual_vals, marker_color='#0D9488'),
        go.Bar(name='Target', x=categories, y=target_vals, marker_color='#94A3B8')
    ])
    fig.update_layout(title="Intake vs Target", width=400, height=280, barmode='group', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#333333'))
    img_bytes = io.BytesIO()
    fig.write_image(img_bytes, format='png', scale=2)
    img_bytes.seek(0)
    return img_bytes

@log_execution_time
def build_pdf_report(user_profile: dict, nutrition_data: dict, ai_analysis: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], textColor=colors.HexColor('#0D9488'), spaceAfter=10)
    
    story = [Paragraph(f"Executive Nutrition Report: {user_profile.get('name', 'User')}", styles['Heading1']), Spacer(1, 10)]
    
    story.append(Paragraph("AI Executive Summary", h2))
    story.append(Paragraph(ai_analysis.get("executive_summary", "No data available."), styles['Normal']))
    story.append(Spacer(1, 20))
    
    pie = Image(generate_macro_donut_chart(nutrition_data), width=250, height=175)
    bar = Image(generate_target_vs_actual_chart(nutrition_data, user_profile), width=250, height=175)
    story.append(Table([[pie, bar]]))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("Action Plan", h2))
    for action in ai_analysis.get("action_plan", []):
        story.append(Paragraph(f"• {action}", styles['Normal']))
        
    if ai_analysis.get("health_warnings"):
        story.append(Spacer(1, 15))
        story.append(Paragraph("Warnings to Watch", h2))
        for warning in ai_analysis.get("health_warnings", []):
             story.append(Paragraph(f"⚠️ {warning}", styles['Normal']))
             
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
