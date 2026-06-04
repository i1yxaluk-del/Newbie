# services/max_alerter/Dockerfile
# Авторизация выполняется СНАРУЖИ контейнера (python auth.py),
# сессия монтируется как volume /session.

FROM python:3.12-slim

# Системные зависимости для asyncio/TCP (минимум)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Зависимости отдельным слоем — кешируются при изменении кода
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходники пакета
COPY . /app/max_alerter/

# Директории для сессии и логов недоставленных алертов
VOLUME ["/session", "/data"]

# Переменные окружения (переопределяются в docker-compose)
ENV MAX_PHONE=""
ENV MAX_SESSION_DIR="/session"
ENV MAX_SESSION_NAME="max.db"
ENV WEBHOOK_TOKEN=""
ENV MAX_CHAT_ID=""
ENV TG_BOT_TOKEN=""
ENV TG_CHAT_ID=""
ENV FAILED_LOG="/data/failed_alerts.log"
ENV HOST="0.0.0.0"
ENV PORT="9095"

EXPOSE 9095

# Запуск webhook-сервера
CMD ["python", "-m", "uvicorn", "max_alerter.webhook:app", \
 "--host", "0.0.0.0", "--port", "9095", "--log-level", "info"]
