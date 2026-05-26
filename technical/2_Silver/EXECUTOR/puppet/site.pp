# ═══════════════════════════════════════════════════════════════════
# site.pp — Главный манифест Puppet
# Файл: /etc/puppetlabs/code/environments/production/manifests/site.pp
#
# ДЛЯ JUNIOR:
#   site.pp — это "входная точка" Puppet.
#   Когда агент подключается к серверу, Puppet смотрит сюда
#   чтобы понять какие классы (настройки) применить к этому узлу.
#
#   Ключевые понятия:
#   - node default    — применяется ко ВСЕМ узлам
#   - node "имя"      — применяется к конкретному узлу (по certname)
#   - node /^regex$/  — применяется к узлам по регулярному выражению
#   - include class   — применить класс (набор ресурсов)
#   - class { 'name': param => value } — применить с параметрами
#
#   КАК РАБОТАЕТ PUPPET:
#   1. Агент подключается к серверу каждые 30 мин
#   2. Сервер компилирует каталог (catalog) на основе site.pp
#   3. Агент сравнивает каталог с текущим состоянием
#   4. Если есть отличия (drift) — применяет изменения
#   5. Если кто-то вручную изменил файл — Puppet вернёт обратно
#
#   ПОСЛЕ ИЗМЕНЕНИЯ site.pp:
#   - Не нужно ничего перезагружать
#   - Агенты подхватят изменения при следующем run (30 мин)
#   - Или вручную: puppet agent --test
# ═══════════════════════════════════════════════════════════════════

# ── Глобальные настройки ───────────────────────────────────────────
# Применяются ко всем узлам перед классами
File { backup => '.puppet-bak' }

# ════════════════════════════════════════════════════════════════════
# ДЕФОЛТНЫЙ УЗЕЛ — применяется ко всем Linux-серверам клиентов
# ════════════════════════════════════════════════════════════════════
node default {

  # ── Bronze: базовая настройка ─────────────────────────────────
  class { 'base_linux':
    timezone             => 'Europe/Moscow',
    disable_root_ssh     => true,
    disable_password_auth => true,
  }

  # ── Bronze: hardening ─────────────────────────────────────────
  class { 'hardening':
    enable_sysctl  => true,
    disable_usb    => false,    # true для Astra Linux / гос. сектор
    enable_auditd  => false,    # true для Gold
  }

  # ── Bronze: защита агентов мониторинга ───────────────────────
  class { 'monitoring_agents':
    manage_node_exporter => true,
    manage_restic_timer  => true,
    manage_wireguard     => true,
    manage_promtail      => false,   # Silver: изменить на true
    manage_wazuh_agent   => false,   # Gold: изменить на true
    awg_interface        => 'awg0',
  }
}

# ════════════════════════════════════════════════════════════════════
# СПЕЦИФИЧНЫЕ СЕРВЕРЫ (по certname)
# Раскомментировать и настроить под конкретного клиента
# ════════════════════════════════════════════════════════════════════

# # Silver-клиент: пример
# node /^.*\.client-example\.internal$/ {
#   include base_linux
#   include hardening
#   class { 'monitoring_agents':
#     manage_promtail => true,   # Silver
#   }
# }

# # Gold-клиент: Astra Linux + полный hardening
# node /^astra-.*\.client-gold\.internal$/ {
#   class { 'base_linux': }
#   class { 'hardening':
#     disable_usb   => true,     # Запрет USB
#     enable_auditd => true,     # Аудит событий
#   }
#   class { 'monitoring_agents':
#     manage_promtail    => true,
#     manage_wazuh_agent => true,
#   }
# }

# # Веб-сервер: специфичные настройки Nginx
# node /^web-\d+\..+$/ {
#   include base_linux
#   include hardening
#   include monitoring_agents
#   # Дополнительный класс для веб-серверов:
#   # include nginx_hardening
# }
