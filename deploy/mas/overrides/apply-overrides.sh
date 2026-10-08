#!/usr/bin/env bash
# Применяет русские/упрощённые оверрайды шаблонов MAS: копия шаблонов/переводов из образа + правки.
set -euo pipefail
IMG=msp-mas
D=/opt/mas
rm -rf /tmp/mas-overrides-tpl /tmp/mas-overrides-tr
docker cp "$IMG":/usr/local/share/mas-cli/templates /tmp/mas-overrides-tpl
docker cp "$IMG":/usr/local/share/mas-cli/translations /tmp/mas-overrides-tr
mkdir -p "$D/templates" "$D/translations"
cp -r /tmp/mas-overrides-tpl/. "$D/templates/"
cp -r /tmp/mas-overrides-tr/. "$D/translations/"
python3 - <<'PY'
p = '/opt/mas/templates/base.html'
s = open(p, encoding='utf-8').read()
s = s.replace('{% set _ = translator(lang) %}', '{% set _ = translator("ru") %}')
s = s.replace('<html lang="{{ lang }}">', '<html lang="ru">')
s = s.replace('{% block title %}{{ _("app.name") }}{% endblock title %}', '{% block title %}MSPShield{% endblock title %}')
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('base.html updated')
PY
cp "$(dirname "$0")/consent.html" "$D/templates/pages/consent.html"
cp "$(dirname "$0")/index.html" "$D/templates/pages/index.html"
echo "готово. Пересоздайте контейнер: cd /opt/mas && docker compose up -d mas"
