#!/usr/bin/env bash
# Сборка JAMS: React-клиент + Maven-пакет. Самый долгий шаг.
set -uo pipefail
export JAVA_HOME=/opt/jdk26
export PATH=/opt/jdk26/bin:$PATH
export NODE_OPTIONS=--openssl-legacy-provider
SRC=/opt/jams-src

echo "=== 0. структура исходников ==="
ls "$SRC"

echo "=== 0b. Maven 3.9 (системный 3.6.3 стар для JDK 26) ==="
if [ ! -x /opt/maven/bin/mvn ]; then
  curl -fsSL --retry 3 -o /tmp/mvn.tar.gz "https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz" \
    && mkdir -p /opt/maven && tar -xzf /tmp/mvn.tar.gz -C /opt/maven --strip-components=1 && rm -f /tmp/mvn.tar.gz \
    || echo "Maven 3.9 не скачался — остаюсь на системном"
fi
MVN=/opt/maven/bin/mvn; [ -x "$MVN" ] || MVN=$(command -v mvn)
export PATH="$(dirname $MVN):$PATH"
"$MVN" -version 2>&1 | head -2

echo "=== 1. сборка React-клиента ==="
if [ -d "$SRC/jams-react-client" ]; then
  cd "$SRC/jams-react-client"
  npm ci --legacy-peer-deps 2>&1 | tail -6
  npm run build 2>&1 | tail -12
  WEB="$SRC/jams-server/src/main/resources/webapp"
  mkdir -p "$WEB"
  if [ -d build ]; then cp -r build/* "$WEB"/; elif [ -d dist ]; then cp -r dist/* "$WEB"/; else echo "НЕ НАЙДЕН каталог сборки фронта"; fi
  ls "$WEB" | head -5
else
  echo "нет каталога jams-react-client"; ls "$SRC"
fi

echo "=== 2. Maven package (может идти долго) ==="
cd "$SRC"
"$MVN" clean package -DskipTests 2>&1 | tail -30

echo "=== 3. результат ==="
find "$SRC" -maxdepth 4 \( -name "*.jar" -o -name "*.war" \) 2>/dev/null | head -12
echo JAMS_BUILD_DONE
