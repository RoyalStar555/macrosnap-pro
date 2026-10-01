FROM python:3.11-slim

# Install system dependencies for Plotly, Kaleido, ReportLab, and PIL
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose ports for Streamlit and FastAPI
EXPOSE 8501
EXPOSE 8000

# Script to run both servers (Streamlit in background, Uvicorn in foreground)
RUN echo '#!/bin/bash\nstreamlit run app.py --server.port=8501 --server.address=0.0.0.0 & uvicorn whatsapp_bot:app --host 0.0.0.0 --port 8000' > /app/start.sh
RUN chmod +x /app/start.sh

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["/app/start.sh"]
