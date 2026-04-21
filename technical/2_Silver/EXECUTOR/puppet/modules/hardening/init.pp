# ═══════════════════════════════════════════════════════════════════
# modules/hardening/manifests/init.pp
# Puppet модуль: hardening Linux-серверов
#
# Что контролирует:
#   - sysctl параметры безопасности ядра
#   - auditd (если Gold)
#   - USB-накопители (если требуется)
#   - Logrotate
# ═══════════════════════════════════════════════════════════════════

class hardening (

  Boolean $enable_auditd    = false,   # true для Gold
  Boolean $disable_usb      = false,   # true для Astra Linux / гос. сектора
  Boolean $enable_sysctl    = true,
  Integer $max_log_size_mb  = 100,

) {

  # ════════════════════════════════════════════════════════════════
  # 1. SYSCTL — параметры безопасности ядра
  # Puppet следит: если кто-то изменит через sysctl -w → вернёт
  # ════════════════════════════════════════════════════════════════
  if $enable_sysctl {

    $sysctl_params = {
      # ── Сеть ──────────────────────────────────────────────────
      # Запрет ICMP-редиректов (защита от MITM-атак)
      'net.ipv4.conf.all.accept_redirects'     => 0,
      'net.ipv4.conf.default.accept_redirects' => 0,
      'net.ipv4.conf.all.send_redirects'       => 0,
      'net.ipv4.conf.default.send_redirects'   => 0,

      # Защита от IP-спуфинга (проверка маршрутов)
      'net.ipv4.conf.all.rp_filter'            => 1,
      'net.ipv4.conf.default.rp_filter'        => 1,

      # Запрет source-routed пакетов
      'net.ipv4.conf.all.accept_source_route'  => 0,

      # Логировать "марсианские" пакеты (несуществующие источники)
      'net.ipv4.conf.all.log_martians'         => 1,

      # IPv6 редиректы
      'net.ipv6.conf.all.accept_redirects'     => 0,
      'net.ipv6.conf.default.accept_redirects' => 0,

      # SYN-flood защита
      'net.ipv4.tcp_syncookies'                => 1,
      'net.ipv4.tcp_max_syn_backlog'           => 2048,
      'net.ipv4.tcp_synack_retries'            => 2,
      'net.ipv4.tcp_syn_retries'               => 5,

      # ── Ядро ──────────────────────────────────────────────────
      # Рандомизация адресного пространства (ASLR)
      'kernel.randomize_va_space'              => 2,

      # Запрет чтения адресов ядра (защита от KASLR обхода)
      'kernel.kptr_restrict'                   => 2,

      # Запрет чтения dmesg не-root
      'kernel.dmesg_restrict'                  => 1,

      # Core dump только при явном разрешении
      'fs.suid_dumpable'                       => 0,

      # ── Производительность (заодно) ───────────────────────────
      'vm.swappiness'                          => 10,
      'vm.dirty_ratio'                         => 15,
      'vm.dirty_background_ratio'              => 5,
    }

    # Создать файл с параметрами (персистентно через reboot)
    $sysctl_content = $sysctl_params.map |$k, $v| { "${k} = ${v}" }.join("\n")

    file { '/etc/sysctl.d/99-msp-hardening.conf':
      ensure  => file,
      owner   => root,
      group   => root,
      mode    => '0644',
      content => "# MSPShield hardening sysctl\n# Managed by Puppet — не редактировать вручную\n\n${sysctl_content}\n",
      notify  => Exec['sysctl-reload'],
    }

    exec { 'sysctl-reload':
      command     => '/sbin/sysctl --system',
      refreshonly => true,
      path        => ['/sbin', '/usr/sbin', '/bin'],
    }
  }

  # ════════════════════════════════════════════════════════════════
  # 2. AUDITD (Gold) — аудит системных вызовов
  # ════════════════════════════════════════════════════════════════
  if $enable_auditd {
    package { 'auditd':
      ensure => present,
    }

    # Базовые правила аудита
    file { '/etc/audit/rules.d/99-msp-audit.rules':
      ensure  => file,
      owner   => root,
      group   => root,
      mode    => '0600',
      content => @("RULES"),
# MSPShield Audit Rules
# Managed by Puppet

# Вход/выход пользователей
-w /var/log/faillog -p wa -k logins
-w /var/log/lastlog -p wa -k logins
-w /var/run/utmp -p wa -k session

# Sudo
-w /bin/su -p x -k priv_esc
-w /usr/bin/sudo -p x -k priv_esc
-w /etc/sudoers -p wa -k sudo_changes

# Критичные конфиги
-w /etc/passwd -p wa -k user_changes
-w /etc/shadow -p wa -k user_changes
-w /etc/group -p wa -k group_changes
-w /etc/ssh/sshd_config -p wa -k sshd_config

# Cron
-w /etc/cron.d/ -p wa -k cron
-w /etc/cron.daily/ -p wa -k cron
-w /etc/crontab -p wa -k cron

# Сетевые настройки
-w /etc/hosts -p wa -k network_changes
-w /etc/sysctl.conf -p wa -k sysctl
| RULES
      require => Package['auditd'],
      notify  => Service['auditd'],
    }

    service { 'auditd':
      ensure  => running,
      enable  => true,
      require => Package['auditd'],
    }
  }

  # ════════════════════════════════════════════════════════════════
  # 3. ЗАПРЕТ USB-НАКОПИТЕЛЕЙ (для Astra Linux, гос. сектор)
  # ════════════════════════════════════════════════════════════════
  if $disable_usb {
    file { '/etc/modprobe.d/msp-disable-usb-storage.conf':
      ensure  => file,
      owner   => root,
      group   => root,
      mode    => '0644',
      content => "# Managed by Puppet — Запрет USB-накопителей\ninstall usb-storage /bin/false\n",
    }

    exec { 'rmmod-usb-storage':
      command => '/sbin/rmmod usb_storage',
      onlyif  => '/sbin/lsmod | grep -q usb_storage',
      path    => ['/sbin', '/usr/sbin'],
    }
  }

  # ════════════════════════════════════════════════════════════════
  # 4. LOGROTATE — ограничение размера логов
  # ════════════════════════════════════════════════════════════════
  file { '/etc/logrotate.d/msp':
    ensure  => file,
    owner   => root,
    group   => root,
    mode    => '0644',
    content => @("LOGROTATE"),
/var/log/msp*.log {
    size ${max_log_size_mb}M
    rotate 5
    compress
    missingok
    notifempty
    copytruncate
}
| LOGROTATE
  }

  # ════════════════════════════════════════════════════════════════
  # 5. LIMITS — лимиты процессов
  # ════════════════════════════════════════════════════════════════
  file { '/etc/security/limits.d/99-msp.conf':
    ensure  => file,
    owner   => root,
    group   => root,
    mode    => '0644',
    content => @("LIMITS"),
# MSPShield — Managed by Puppet
# Увеличенные лимиты для стабильности сервисов
*    soft nofile 65535
*    hard nofile 65535
root soft nofile 65535
root hard nofile 65535
| LIMITS
  }
}
