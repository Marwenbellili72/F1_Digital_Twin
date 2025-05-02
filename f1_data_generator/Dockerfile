FROM python:3.10.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONPATH=/home/appuser/.local/bin:$PYTHONPATH \
    PATH=/home/appuser/.local/bin:$PATH \
    RUNNING_IN_DOCKER=true

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home appuser

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appgroup ./app /app/app


ENV ORION_URL="http://orion:1026"
ENV SCHEDULE_INTERVAL_SECONDS=10
ENV LOG_LEVEL="INFO"
ENV SESSION_KEY=12345
ENV GENERATOR_YEAR=2023
ENV GENERATOR_GP="Monza"
ENV GENERATOR_SESSION="R"
ENV FASTF1_CACHE_PATH="/tmp/fastf1_cache" 

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]