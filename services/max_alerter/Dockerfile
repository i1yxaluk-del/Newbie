# MAX userbot webhook. Авторизация запускается вручную ВНУТРИ контейнера:
# docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/max_alerter/
VOLUME ["/session", "/data"]
ENV MAX_PHONE="" MAX_SESSION_DIR="/session" MAX_SESSION_NAME="max.db" \
    WEBHOOK_TOKEN="" MAX_CHAT_ID="" TG_BOT_TOKEN="" TG_CHAT_ID="" \
    FAILED_LOG="/data/failed_alerts.log" HOST="0.0.0.0" PORT="9095"
EXPOSE 9095
CMD ["python", "-m", "uvicorn", "max_alerter.webhook:app", "--host", "0.0.0.0", "--port", "9095", "--log-level", "info"]
