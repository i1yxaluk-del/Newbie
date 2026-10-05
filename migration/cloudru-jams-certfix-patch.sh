#!/usr/bin/env bash
# Патч JAMS: SearchDirectoryServlet падает с NPE, если у пользователя нет сертификата
# (так случилось с mspadmin, созданным установщиком до фикса signingAlgorithm).
# Из-за этого страница /users пуста. Добавляем null-check и пересобираем jams-server.
set -uo pipefail

echo "=== 1. как запускается JAMS и где jar ==="
systemctl cat jams 2>/dev/null | grep -E "ExecStart|WorkingDirectory|Environment"
ls -la /opt/jams/*.jar 2>/dev/null

echo
echo "=== 2. как сервлет получает query ==="
F=/opt/jams-src/jams-server/src/main/java/net/jami/jams/server/servlets/api/auth/directory/SearchDirectoryServlet.java
grep -nE "queryString|getParameter|getReader|protected void do" "$F" | head -12

echo
echo "=== 3. патч (добавляем проверку сертификата) ==="
python3 - <<'PY'
p = "/opt/jams-src/jams-server/src/main/java/net/jami/jams/server/servlets/api/auth/directory/SearchDirectoryServlet.java"
s = open(p, encoding="utf-8").read()
if "user.getCertificate() != null" in s:
    print("  уже пропатчено")
else:
    old = "            if (user != null) {"
    new = "            if (user != null && user.getCertificate() != null) {"
    if old in s:
        open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
        print("  патч применён")
    else:
        print("  ЯКОРЬ НЕ НАЙДЕН — патч не применён")
PY
grep -n "user != null" "$F" | head -3

echo
echo "=== 4. сборка jams-server в фоне ==="
export JAVA_HOME=/opt/jdk26
export PATH="/opt/jdk26/bin:$PATH"
java -version 2>&1 | head -1
cd /opt/jams-src
nohup mvn -pl jams-server -am package -DskipTests > /tmp/jams-build.log 2>&1 &
echo "  PID сборки: $!"
echo "  лог: /tmp/jams-build.log"
echo BUILD_STARTED
