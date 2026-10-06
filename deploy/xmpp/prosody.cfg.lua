-- ═══════════════════════════════════════════════════════════════════
-- Prosody (XMPP) для MSPShield — автономный сервер, федерация выключена
-- ═══════════════════════════════════════════════════════════════════
-- Домен:       x.msp-claude.online   (JID вида user@x.msp-claude.online)
-- Конференции: con.msp-claude.online
-- Клиенты:     x.msp-claude.online:5222 (STARTTLS)
--
-- Принципы:
--   * третьих лиц нет: s2s (федерация) выключена полностью;
--   * публичная регистрация выключена — учётки создаёт администратор;
--   * звонки — через наш coturn (XEP-0215, mod_turn_external);
--   * медиа — HTTP Upload с лимитом 100 МБ и автоудалением через 7 дней;
--   * push — XEP-0357 через ntfy (UnifiedPush), без сервисов Google.
-- ═══════════════════════════════════════════════════════════════════

admins = { "admin@x.msp-claude.online" }

-- Работаем на переднем плане (нужно для Docker)
daemonize = false

-- ── Модули ────────────────────────────────────────────────────────
modules_enabled = {
    -- базовое
    "roster"; "saslauth"; "tls"; "disco"; "ping"; "time"; "uptime"; "version";
    "private"; "blocklist"; "vcard4"; "vcard_legacy"; "pep";
    -- сообщения и история
    "mam";            -- архив переписки (нужен для нескольких устройств)
    "carbons";        -- копии сообщений на все устройства
    "smacks";         -- докачка потока при обрыве связи (мобильные)
    "csi";            -- экономия батареи на мобильных
    "lastactivity";
    -- медиа и звонки
    "http_upload";    -- файлы и голосовые
    "turn_external";  -- выдаём клиентам наш TURN (XEP-0215)
    "invites";          -- XEP-0401: приглашения (ссылки/QR, автоконфигурация клиентов)
    "invites_adhoc";    -- ad-hoc команды для управления приглашениями
    "invites_register"; -- регистрация только по инвайт-токену
    "invites_api";      -- REST API приглашений (для портала)
    -- прочее
    "websocket";      -- веб-клиенты (через Caddy)
    "cloud_notify";   -- push (XEP-0357, UnifiedPush)
    "announce";
    -- ВАЖНО: muc/muc_mam здесь НЕ подключаем — они живут только на компоненте
}

modules_disabled = {
    "offline";   -- офлайн-сообщения на сервере не храним
    "register";  -- публичная регистрация запрещена
    "s2s";       -- федерация выключена
}

-- ── Безопасность ──────────────────────────────────────────────────
allow_registration = false
c2s_require_encryption = true
authentication = "internal_hashed"

-- ── Федерация ВЫКЛЮЧЕНА ───────────────────────────────────────────
s2s_ports = {}          -- входящие s2s не слушаем
s2s_secure_auth = true

-- ── Сертификаты (копируются из Caddy скриптом deploy.sh) ──────────
certificates = "certs"
https_ports = {}        -- HTTPS отдаёт Caddy

-- ── HTTP (upload + websocket) ─────────────────────────────────────
http_ports = { 5280 }
http_interfaces = { "*" }
http_max_content_size = 110 * 1024 * 1024

-- ── TURN для звонков (наш coturn, секрет подставляет deploy.sh) ───
turn_external_host = "turn.msp-claude.online"
turn_external_port = 3478
turn_external_transport = "udp"
turn_external_ttl = 86400
turn_external_secret = "__TURN_SECRET__"

-- ── Основной виртуальный хост ─────────────────────────────────────
VirtualHost "x.msp-claude.online"
    http_host = "x.msp-claude.online"
    http_external_url = "https://x.msp-claude.online/"
    http_upload_file_size_limit = 100 * 1024 * 1024
    http_upload_expire_after = 60 * 60 * 24 * 7
    disco_items = {
        { "con.msp-claude.online", "MSPShield — конференции" },
    }

-- ── Конференции ───────────────────────────────────────────────────
Component "con.msp-claude.online" "muc"
    name = "MSPShield — конференции"
    modules_enabled = { "muc_mam"; "vcard" }
    restrict_room_creation = "local"
    max_history_messages = 50

-- ── Логи ──────────────────────────────────────────────────────────
log = {
    info = "/var/log/prosody/prosody.log";
    error = "/var/log/prosody/prosody.err";
}
data_path = "/var/lib/prosody"
