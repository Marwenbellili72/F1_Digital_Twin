FROM python:3.9-slim

WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libfreetype6-dev \
    pkg-config \
    fontconfig \
    libpng-dev \
    libjpeg-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
COPY f1_tracker.py /app/
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/fastf1_cache_streamlit
EXPOSE 8501
CMD ["streamlit", "run", "f1_tracker.py", "--server.port=8501", "--server.address=0.0.0.0"]