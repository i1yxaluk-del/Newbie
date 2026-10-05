#!/usr/bin/env bash
# Подготовка JAMS: JDK 26 + Maven + исходники. Долгий шаг — запускать в фоне.
set -uo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "=== 1. базовые пакеты ==="
apt-get install -y maven git curl unzip >/dev/null 2>&1 || echo "warn apt"
mvn -version 2>/dev/null | head -1 || echo "maven не установлен"

echo "=== 2. JDK 26 (Temurin) -> /opt/jdk26 ==="
if [ -x /opt/jdk26/bin/java ]; then
  echo "уже установлен: $(/opt/jdk26/bin/java -version 2>&1 | head -1)"
else
  ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && A=x64 || A=aarch64
  URL="https://api.adoptium.net/v3/binary/latest/26/ga/linux/${A}/jdk/hotspot/normal/eclipse"
  echo "качаю: $URL"
  if curl -fsSL --retry 3 -o /tmp/jdk26.tar.gz "$URL"; then
    mkdir -p /opt/jdk26
    tar -xzf /tmp/jdk26.tar.gz -C /opt/jdk26 --strip-components=1
    rm -f /tmp/jdk26.tar.gz
    /opt/jdk26/bin/java -version 2>&1 | head -2
  else
    echo "Adoptium недоступен, пробую apt openjdk-26-jdk"
    apt-get install -y openjdk-26-jdk 2>&1 | tail -2 || echo "JDK26 APT FAILED"
    [ -d /usr/lib/jvm/java-26-openjdk-amd64 ] && ln -sfn /usr/lib/jvm/java-26-openjdk-amd64 /opt/jdk26
  fi
fi

echo "=== 3. исходники JAMS ==="
if [ -d /opt/jams-src/.git ]; then
  echo "исходники уже есть"
else
  rm -rf /opt/jams-src
  git clone --depth 1 https://git.jami.net/savoirfairelinux/jami-jams.git /opt/jams-src 2>&1 | tail -3 || echo "CLONE FAILED"
fi
[ -d /opt/jams-src ] && du -sh /opt/jams-src 2>/dev/null
ls /opt/jams-src 2>/dev/null | head -10

echo "=== 4. версии ==="
node --version 2>/dev/null || echo "node нет"
npm --version 2>/dev/null || echo "npm нет"
echo JAMS_PREP_DONE
