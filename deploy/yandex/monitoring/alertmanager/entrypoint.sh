#!/bin/sh
# Назначение: безопасно подставить секреты в шаблон Alertmanager перед запуском.
# Секрет webhook обязателен: пустое значение открыло бы внутренний endpoint.
set -eu

if [ -z "${ALERTMANAGER_WEBHOOK_TOKEN:-}" ]; then
  echo "ERROR: ALERTMANAGER_WEBHOOK_TOKEN не задан" >&2
  exit 1
fi

# sed не печатает значения; итоговый файл остаётся внутри контейнера.
sed -e "s|\${SMTP_AUTH_PASSWORD}|${SMTP_AUTH_PASSWORD:-}|g" \
    -e "s|\${ALERTMANAGER_WEBHOOK_TOKEN}|${ALERTMANAGER_WEBHOOK_TOKEN}|g" \
    < /etc/alertmanager/alertmanager.yml.tmpl \
    > /etc/alertmanager/alertmanager.yml
exec /bin/alertmanager "$@"
