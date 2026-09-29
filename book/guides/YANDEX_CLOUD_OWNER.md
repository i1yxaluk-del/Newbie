# Yandex Cloud для Owner MSPShield

## Карта ресурсов

Организация содержит clouds, cloud — folders, folder — VM, disks, networks, addresses и service accounts. IAM role всегда имеет subject, resource scope и набор разрешений. Роль editor на весь cloud удобна, но увеличивает blast radius.

## Сеть

VPC network объединяет подсети; subnet задаёт CIDR и availability zone. Public IP не означает открытый порт: путь дополнительно контролируют security group, firewall VM, listening socket и приложение. Проверяйте TCP из целевого региона, а не делайте вывод по одному ping.

## Минимальный deploy-путь

1. Создать отдельный folder для production.
2. Создать service account с минимальными ролями.
3. Спроектировать network/subnet и security group до VM.
4. Создать VM и boot disk нужного размера; не считать бесплатный ресурс бесконечным.
5. Зафиксировать public IP, если DNS и allowlist не должны меняться.
6. Проверить SSH host key до передачи секретов.
7. Запустить repository preflight, затем deploy runbook.
8. Проверить DNS → TCP → TLS → HTTP → application → dependencies.
9. Включить monitoring, backup и budget alerts.

## Cloud-init

Cloud-init выполняется при первом старте и годится для базовой подготовки, но не должен содержать долгоживущие production secrets. Его успешное завершение не доказывает готовность приложения. Проверяйте `/var/log/cloud-init-output.log`, systemd units и фактические sockets.

## Диски, snapshot и backup

Snapshot диска удобен для инфраструктурного rollback, но не гарантирует application-consistent Mongo/Vaultwarden/Stalwart state. Backup должен иметь manifest, encryption, независимое хранение и проверенный restore. RPO/RTO измеряются упражнением.

## Деньги

Перед созданием ресурса запишите owner, назначение, срок удаления и бюджет. После лабораторной удалите VM, unattached disks, snapshots и reserved IP, если они не нужны. Бесплатная VM снижает текущий cash cost, но не отменяет стоимость времени и risk reserve.

## Практикум

- создать lab folder, network, subnet, security group и VM;
- открыть только SSH с доверенного адреса и HTTPS;
- показать, чем отличаются timeout, refused и HTTP 503;
- остановить/запустить VM и проверить постоянство disk state;
- удалить лабораторию и убедиться, что не осталось платных ресурсов.

## Видео и источники

- [Как начать работу в Yandex Cloud](https://www.youtube.com/watch?v=u9PI_VncAd4) — официальный вводный вебинар.
- [Из чего состоит IAM](https://www.youtube.com/watch?v=JCu5WD1o9Is) — инженерная модель IAM.
- Сверяйте интерфейс и команды с актуальной документацией Yandex Cloud и runbook репозитория.
