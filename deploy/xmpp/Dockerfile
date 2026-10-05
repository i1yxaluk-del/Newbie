# ═══════════════════════════════════════════════════════════════════
# Актуальный Prosody для MSPShield
# ═══════════════════════════════════════════════════════════════════
# Почему свой образ: официальный prosody/prosody на Docker Hub заброшен на версии
# 0.11.9 (2021 год) — в нём НЕТ http_upload, mam, smacks, cloud_notify, из-за чего
# не работают ни файлы/голосовые, ни архив переписки, ни push.
#
# Здесь ставим Prosody из официального репозитория prosody.im (актуальная ветка)
# и добавляем community-модуль turn_external (XEP-0215 — выдача клиентам нашего TURN).
# ═══════════════════════════════════════════════════════════════════
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl ca-certificates gnupg \
      lua5.4 lua-sec lua-event lua-expat lua-filesystem lua-socket lua-dbi-sqlite3 lua-unbound \
      libidn11-dev libssl-dev ssl-cert \
 && mkdir -p /etc/apt/keyrings \
 && curl -fsSL https://prosody.im/files/prosody-debian-packages.key -o /etc/apt/keyrings/prosody.key \
 && chmod 644 /etc/apt/keyrings/prosody.key \
 && echo "deb [signed-by=/etc/apt/keyrings/prosody.key] https://packages.prosody.im/debian bookworm main" \
      > /etc/apt/sources.list.d/prosody.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends prosody \
 && apt-get install -y --no-install-recommends prosody-modules || true \
 && rm -rf /var/lib/apt/lists/*
# prosody-modules нужен для http_upload (в новых версиях он вынесен из ядра)
# если пакет недоступен — модуль подтянем из community-репозитория ниже
RUN if [ ! -e /usr/lib/prosody/modules/mod_http_upload.lua ] && \
       [ ! -d /usr/lib/prosody/modules/share/lua/5.4/mod_http_upload ]; then \
      mkdir -p /usr/lib/prosody/modules/share/lua/5.4/mod_http_upload && \
      curl -fsSL https://raw.githubusercontent.com/prosody-modules/prosody-modules/master/mod_http_upload/mod_http_upload.lua \
        -o /usr/lib/prosody/modules/share/lua/5.4/mod_http_upload/mod_http_upload.lua \
      && curl -fsSL https://raw.githubusercontent.com/prosody-modules/prosody-modules/master/mod_http_upload/http_upload.lib.lua \
        -o /usr/lib/prosody/modules/share/lua/5.4/mod_http_upload/http_upload.lib.lua || true; \
    fi

# Community-модуль для TURN (в базовую поставку не входит)
RUN curl -fsSL \
      https://raw.githubusercontent.com/prosody-modules/prosody-modules/master/mod_turn_external/mod_turn_external.lua \
      -o /usr/lib/prosody/modules/mod_turn_external.lua \
 || echo "предупреждение: mod_turn_external не скачался (TURN можно задать в клиенте вручную)"

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5222 5280
ENTRYPOINT ["/entrypoint.sh"]
