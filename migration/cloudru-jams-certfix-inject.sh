#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# НАЗНАЧЕНИЕ (для junior): внедряет патч SearchDirectoryServlet в рабочий fat-jar JAMS.
# КОГДА ЗАПУСКАТЬ:         после cloudru-jams-certfix-patch.sh (тот правит ИСХОДНИК и собирает класс)
#                          и только если обычная сборка дала тонкий jar без зависимостей.
# КАК ЗАПУСКАТЬ:           sudo bash cloudru-jams-certfix-inject.sh
# ПРОВЕРКА УСПЕХА:         queryString=* -> HTTP 200 и ВСЕ профили (а не 500).
# ОТКАТ:                   cp /opt/jams/jams-server.jar.bak2.* /opt/jams/jams-server.jar && systemctl restart jams
# ═══════════════════════════════════════════════════════════════════
#
# Зачем: SearchDirectoryServlet (наполняет страницу /users) падал с
# NullPointerException на user.getCertificate().getSerialNumber(), если у пользователя нет
# сертификата. Такой пользователь — mspadmin: его создал установщик JAMS ДО того, как мы
# починили signingAlgorithm, поэтому сертификат ему не подписался. Из-за падения сервлета
# страница /users оставалась пустой.
#
# Патч — одна добавка в условие: `user != null && user.getCertificate() != null`.
# Применяем класс из /opt/jams-src/jams-server/target/classes прямо в fat-jar
# (обычный `mvn package` для jams-server даёт ТОНКИЙ jar, он не заменяет рабочий).
set -uo pipefail
export PATH="/opt/jdk26/bin:$PATH"

CLS=net/jami/jams/server/servlets/api/auth/directory/SearchDirectoryServlet.class
SRC=/opt/jams-src/jams-server/target/classes
JAR=/opt/jams/jams-server.jar

echo "=== 1. патченный класс ==="
ls -la "$SRC/$CLS" || { echo "  НЕТ класса — сначала cloudru-jams-certfix-patch.sh"; exit 2; }

echo
echo "=== 2. бэкап fat-jar ==="
cp "$JAR" "$JAR.bak2.$(date +%s)"
ls -la "$JAR"*

echo
echo "=== 3. обновление класса в jar ==="
cd "$SRC"
jar uf "$JAR" "$CLS" && echo "  обновлено, размер: $(stat -c%s "$JAR")"
chown jams:jams "$JAR"

echo
echo "=== 4. перезапуск ==="
systemctl restart jams
sleep 50
echo -n "  jams: "; systemctl is-active jams
echo -n "  /api/info: "; curl -s -m 10 http://127.0.0.1:8081/api/info; echo

echo
echo "=== 5. проверка поиска (то, что грузит /users) ==="
ENV=/opt/jami-services/.env
JUSER=$(grep '^JAMS_ADMIN_USER=' "$ENV" | cut -d= -f2-)
JPASS=$(grep '^JAMS_ADMIN_PASSWORD=' "$ENV" | cut -d= -f2-)
TOKEN=$(curl -s -m 20 -X POST http://127.0.0.1:8081/api/login -H 'Content-Type: application/json' \
  -d "{\"username\":\"$JUSER\",\"password\":\"$JPASS\"}" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
AUTH="Authorization: Bearer $TOKEN"
printf "  queryString=* -> "
curl -s -o /tmp/sr.json -w "HTTP %{http_code} " -m 15 \
  "http://127.0.0.1:8081/api/auth/directory/search?queryString=*" -H "$AUTH"
python3 - <<'PY'
import json
try:
    d = json.load(open("/tmp/sr.json"))
    print("профилей: %d -> %s" % (len(d.get("profiles", [])), [p.get("username") for p in d.get("profiles", [])]))
except Exception:
    print("(не JSON)", open("/tmp/sr.json").read()[:150])
PY
echo DONE
