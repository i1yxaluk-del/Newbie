# matrix-alerter: Alertmanager webhook → Matrix (Element X) личные чаты alert.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/matrix_alerter/
ENV WEBHOOK_TOKEN="" MATRIX_HS="https://m.msp-claude.online" \
    MATRIX_LOGIN_URL="https://bastion.msp-claude.online" \
    MATRIX_ALERT_USER="alert" MATRIX_ALERT_PASSWORD="" MATRIX_ALERT_ROOMS="" \
    ALLOW_INSECURE_WEBHOOK="false"
EXPOSE 9096
CMD ["python", "-m", "uvicorn", "matrix_alerter.alerter:app", "--host", "0.0.0.0", "--port", "9096", "--log-level", "info"]
