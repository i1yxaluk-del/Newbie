# ═══════════════════════════════════════════════════════════════════
# modules/monitoring_agents/manifests/init.pp
# Puppet модуль: защита агентов мониторинга
#
# ГЛАВНАЯ ЗАДАЧА: агенты мониторинга и бэкапов не должны быть
# отключены или удалены. Puppet проверяет каждые 30 минут.
#
# Почему это важно:
#   Если кто-то случайно остановит node_exporter → Prometheus
#   перестанет собирать метрики → мы не узнаем о проблемах.
#   Если кто-то отключит restic timer → бэкапы не делаются.
# ═══════════════════════════════════════════════════════════════════

class monitoring_agents (

  # ── Флаги для каждого агента ──────────────────────────────────────
  Boolean $manage_node_exporter   = true,    # Всегда для Bronze+
  Boolean $manage_restic_timer    = true,    # Всегда для Bronze+
  Boolean $manage_wireguard       = true,    # Всегда для Bronze+
  Boolean $manage_promtail        = false,   # Silver+
  Boolean $manage_wazuh_agent     = false,   # Gold только

  # ── Имя WireGuard интерфейса ─────────────────────────────────────
  String $wg_interface = 'wg0-msp',

) {

  # ════════════════════════════════════════════════════════════════
  # node_exporter — должен быть running + enabled
  # ════════════════════════════════════════════════════════════════
  if $manage_node_exporter {
    service { 'node_exporter':
      ensure => running,
      enable => true,
    }

    # Бинарник должен существовать и быть исполняемым
    file { '/usr/local/bin/node_exporter':
      ensure => file,
      owner  => root,
      group  => root,
      mode   => '0755',
    }

    # Директория textfile_collector должна быть доступна для записи
    file { '/var/lib/node_exporter/textfile_collector':
      ensure => directory,
      owner  => node_exporter,
      group  => node_exporter,
      mode   => '0755',
    }
  }

  # ════════════════════════════════════════════════════════════════
  # restic backup timer — должен быть активен
  # ════════════════════════════════════════════════════════════════
  if $manage_restic_timer {
    service { 'restic-backup.timer':
      ensure => running,
      enable => true,
    }

    # Скрипт бэкапа должен существовать
    file { '/opt/restic-scripts/backup.sh':
      ensure => file,
      owner  => root,
      group  => root,
      mode   => '0755',
    }

    # Файл конфигурации должен быть защищён (только root)
    file { '/etc/restic/env.sh':
      ensure => file,
      owner  => root,
      group  => root,
      mode   => '0600',
    }
  }

  # ════════════════════════════════════════════════════════════════
  # WireGuard VPN — туннель должен быть включён
  # ════════════════════════════════════════════════════════════════
  if $manage_wireguard {
    service { "wg-quick@${wg_interface}":
      ensure => running,
      enable => true,
    }

    # Конфиг должен быть защищён (содержит приватный ключ)
    file { "/etc/wireguard/${wg_interface}.conf":
      ensure => file,
      owner  => root,
      group  => root,
      mode   => '0600',
    }
  }

  # ════════════════════════════════════════════════════════════════
  # Promtail (Silver+) — должен работать
  # ════════════════════════════════════════════════════════════════
  if $manage_promtail {
    service { 'promtail':
      ensure => running,
      enable => true,
    }

    file { '/usr/local/bin/promtail':
      ensure => file,
      owner  => root,
      group  => root,
      mode   => '0755',
    }

    file { '/etc/promtail/config.yml':
      ensure => file,
      owner  => root,
      group  => root,
      mode   => '0644',
    }
  }

  # ════════════════════════════════════════════════════════════════
  # Wazuh Agent (Gold) — должен работать
  # ════════════════════════════════════════════════════════════════
  if $manage_wazuh_agent {
    service { 'wazuh-agent':
      ensure => running,
      enable => true,
    }
  }

  # ════════════════════════════════════════════════════════════════
  # UFW — файрвол должен быть включён
  # Базовые правила (порты мониторинга из VPN)
  # ════════════════════════════════════════════════════════════════
  service { 'ufw':
    ensure => running,
    enable => true,
  }
}
