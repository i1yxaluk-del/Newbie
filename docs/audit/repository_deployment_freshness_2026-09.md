# Ревизия deployment-информации — 29.09.2026

Сравнены миграционные и deploy-коммиты `ead78a4`, `c6d3c3f`, `a6483be`, `2ba6541`, `cffbbf9`, `6e40c8d`, `1fb81d8`, `2e06f9c`, `89249e4` и текущее состояние `58209a9`.

Закреплено: loopback для backend; MAX userbot с явным `--authorize`; Postbox `:465`, API-key ID и DKIM CNAME; оба Stalwart volume и запрет bootstrap mode; внешний TCP/TLS gate до DNS; закрытие public SSH после AWG; clean-room restore как доказательство backup.

Исправлены Caddy, env-примеры, mail/DKIM, Stalwart, secrets, SMTP runbook, книга, Bronze SOP и Terraform cloud-init. Добавлен CI validator против возврата старых предположений.

Live-инфраструктура всё ещё требует внешнего скана, тестового MAX/email, clean-room restore с RTO/RPO и проверки SG/UFW: репозиторий не может доказать эти факты сам.
