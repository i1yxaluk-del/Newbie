# Еженедельная проверка

## По каждому клиенту

- [ ] targets/dashboard без необъяснённых gaps;
- [ ] последний backup успешен, возраст и размер разумны;
- [ ] alert delivery MAX/email проверена по истории;
- [ ] P1/P2 закрыты либо имеют owner/status update;
- [ ] certificates и critical patches просмотрены;
- [ ] Kaiten tickets имеют next action и due date;
- [ ] доступы/секреты не появились в comments или Git.

## MSP

- [ ] monitoring VM, Postbox, MAX session и restic timer healthy;
- [ ] failed_alerts.log и backup metrics проверены;
- [ ] неоплаченные счета и перегруз команды вынесены owner;
- [ ] weekly journal содержит risks и capacity, не только выполненные задачи.

Каждая отметка ссылается на dashboard, ticket или snapshot ID.
