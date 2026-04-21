# ═══════════════════════════════════════════════════════════════════
# modules/base_linux/manifests/init.pp
# Puppet модуль: базовая настройка ВСЕХ Linux-серверов
#
# Применяется: ко всем узлам через site.pp (node default)
# Проверка каждые 30 мин → откат если кто-то изменил вручную
# ═══════════════════════════════════════════════════════════════════

class base_linux (

  # ── Временна́я зона ──────────────────────────────────────────────
  String $timezone = 'Europe/Moscow',

  # ── DNS-серверы (Yandex DNS — РФ) ────────────────────────────────
  Array[String] $dns_servers = ['77.88.8.8', '77.88.8.1'],

  # ── NTP-серверы ──────────────────────────────────────────────────
  Array[String] $ntp_servers = [
    '0.ru.pool.ntp.org',
    '1.ru.pool.ntp.org',
    '2.ru.pool.ntp.org',
  ],

  # ── SSH Hardening ─────────────────────────────────────────────────
  Boolean $disable_root_ssh        = true,
  Boolean $disable_password_auth   = true,
  Integer $ssh_max_auth_tries      = 3,
  Integer $ssh_login_grace_time    = 30,

  # ── Базовые пакеты ───────────────────────────────────────────────
  Array[String] $base_packages = [
    'chrony',
    'curl',
    'wget',
    'git',
    'htop',
    'iotop',
    'jq',
    'ufw',
    'fail2ban',
    'ca-certificates',
    'unattended-upgrades',
  ],

) {

  # ════════════════════════════════════════════════════════════════
  # 1. ВРЕМЕННА́Я ЗОНА
  # ════════════════════════════════════════════════════════════════
  exec { 'set-timezone':
    command => "/usr/bin/timedatectl set-timezone ${timezone}",
    onlyif  => "/bin/bash -c 'test \"$(timedatectl show --property=Timezone --value)\" != \"${timezone}\"'",
    path    => ['/usr/bin', '/bin'],
  }

  # ════════════════════════════════════════════════════════════════
  # 2. БАЗОВЫЕ ПАКЕТЫ
  # ════════════════════════════════════════════════════════════════
  package { $base_packages:
    ensure => present,
  }

  # ════════════════════════════════════════════════════════════════
  # 3. NTP (chrony)
  # Если кто-то остановит — Puppet перезапустит через 30 мин
  # ════════════════════════════════════════════════════════════════
  service { 'chrony':
    ensure  => running,
    enable  => true,
    require => Package['chrony'],
  }

  # ════════════════════════════════════════════════════════════════
  # 4. SSH HARDENING
  # Эти параметры не должны меняться. Puppet следит за ними.
  # ════════════════════════════════════════════════════════════════

  if $disable_root_ssh {
    file_line { 'ssh-no-root-login':
      path               => '/etc/ssh/sshd_config',
      line               => 'PermitRootLogin no',
      match              => '^#?PermitRootLogin',
      append_on_no_match => true,
      notify             => Service['sshd'],
    }
  }

  if $disable_password_auth {
    file_line { 'ssh-no-password-auth':
      path               => '/etc/ssh/sshd_config',
      line               => 'PasswordAuthentication no',
      match              => '^#?PasswordAuthentication',
      append_on_no_match => true,
      notify             => Service['sshd'],
    }
  }

  file_line { 'ssh-max-auth-tries':
    path               => '/etc/ssh/sshd_config',
    line               => "MaxAuthTries ${ssh_max_auth_tries}",
    match              => '^#?MaxAuthTries',
    append_on_no_match => true,
    notify             => Service['sshd'],
  }

  file_line { 'ssh-login-grace-time':
    path               => '/etc/ssh/sshd_config',
    line               => "LoginGraceTime ${ssh_login_grace_time}",
    match              => '^#?LoginGraceTime',
    append_on_no_match => true,
    notify             => Service['sshd'],
  }

  # X11 forwarding не нужен на серверах
  file_line { 'ssh-no-x11':
    path               => '/etc/ssh/sshd_config',
    line               => 'X11Forwarding no',
    match              => '^#?X11Forwarding',
    append_on_no_match => true,
    notify             => Service['sshd'],
  }

  service { 'sshd':
    ensure  => running,
    enable  => true,
    require => Package['openssh-server'],
  }

  # ════════════════════════════════════════════════════════════════
  # 5. FAIL2BAN
  # ════════════════════════════════════════════════════════════════
  file { '/etc/fail2ban/jail.local':
    ensure  => file,
    owner   => root,
    group   => root,
    mode    => '0644',
    content => @("EOF"),
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5
backend  = systemd

[sshd]
enabled = true
port    = ssh
| EOF
    require => Package['fail2ban'],
    notify  => Service['fail2ban'],
  }

  service { 'fail2ban':
    ensure  => running,
    enable  => true,
    require => File['/etc/fail2ban/jail.local'],
  }

  # ════════════════════════════════════════════════════════════════
  # 6. RESOLV.CONF (DNS — Yandex)
  # Критично для РФ: стабильный российский DNS
  # ════════════════════════════════════════════════════════════════
  # Примечание: если NetworkManager управляет resolv.conf,
  # изменить через: nmcli con mod ... ipv4.dns "77.88.8.8 77.88.8.1"
  # Этот блок работает для систем без systemd-resolved overlay.

  # ════════════════════════════════════════════════════════════════
  # 7. MOTD — Информационное сообщение при входе
  # ════════════════════════════════════════════════════════════════
  file { '/etc/motd':
    ensure  => file,
    owner   => root,
    group   => root,
    mode    => '0644',
    content => @("EOF"),

  ╔══════════════════════════════════════════════════════╗
  ║  Сервер управляется системой MSPShield               ║
  ║  Все изменения конфигурации отслеживаются Puppet.    ║
  ║  По вопросам: Telegram @msp_support                  ║
  ╚══════════════════════════════════════════════════════╝

| EOF
  }

  # ════════════════════════════════════════════════════════════════
  # 8. АВТОМАТИЧЕСКИЕ ОБНОВЛЕНИЯ БЕЗОПАСНОСТИ
  # ════════════════════════════════════════════════════════════════
  file { '/etc/apt/apt.conf.d/50unattended-upgrades-msp':
    ensure  => file,
    owner   => root,
    group   => root,
    mode    => '0644',
    content => @("EOF"),
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
| EOF
    require => Package['unattended-upgrades'],
  }
}
