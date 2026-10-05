#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# НАЗНАЧЕНИЕ (для junior): Показывает логи Stalwart (в контейнере они пишутся в файл, а не в stdout).
# КОГДА ЗАПУСКАТЬ:         На ВМ, когда нужна диагностика почты.
# КАК ЗАПУСКАТЬ:           sudo bash cloudru-stalwart-logs.sh
# ПРОВЕРКА УСПЕХА:         Видны строки delivery.delivered / delivery.attempt-start.
# ОТКАТ:                   Ничего не меняет — только чтение.
# ═══════════════════════════════════════════════════════════════════
echo "=== /var/log в контейнере Stalwart ==="
sudo docker exec msp-stalwart-1 ls -la /var/log/ 2>&1 | head -25
echo "=== /var/log/stalwart ==="
sudo docker exec msp-stalwart-1 ls -la /var/log/stalwart/ 2>&1 | head -25
echo "=== tail логов ==="
sudo docker exec msp-stalwart-1 sh -c 'tail -n 60 /var/log/stalwart/* 2>&1' | tail -60
echo "=== есть ли запись о доставке нашего письма ==="
sudo docker exec msp-stalwart-1 sh -c 'grep -riE "port25|check-auth|delivered|delivery|bounce" /var/log/stalwart/ 2>/dev/null | tail -20'
echo DONE
