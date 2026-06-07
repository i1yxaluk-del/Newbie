#!/bin/sh
sed -e "s|\${SMTP_AUTH_PASSWORD}|${SMTP_AUTH_PASSWORD}|g" \
    -e "s|\${ALERTMANAGER_WEBHOOK_TOKEN}|${ALERTMANAGER_WEBHOOK_TOKEN}|g" \
    < /etc/alertmanager/alertmanager.yml.tmpl \
    > /etc/alertmanager/alertmanager.yml
exec /bin/alertmanager "$@"
