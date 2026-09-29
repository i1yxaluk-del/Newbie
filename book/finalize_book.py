from pathlib import Path
import re
R=Path('/data/MSPShield_Academy_MD'); C=R/'chapters'
for f in sorted(C.glob('*.md')):
 t=f.read_text()
 t=t.replace('Разбирайте пример слева на��раво. Сначала определите программу или формат, затем входные данные, изменяемое состояние и способ наблюдения. Не переносите команду в production, пока не можете предсказать её side effects.\n\n','')
 t=t.replace('Практикум выполняется на lab VM, тестовой ветке или synthetic dataset. Перед командой с удалением, изменением firewall, DNS, volume, restore `--drop` или production credentials запишите rollback и получите согласование.\n\n','')
 scen=re.search(r'> \*\*Учебная ситуация\.\*\* (.+)',t).group(1)
 terms=re.findall(r'^### (.+)$',t.split('## Что происходит внутри')[0],re.M)
 failures=[]
 if '## Если результат не совпал' in t:
  sec=t.split('## Если результат не совпал')[1].split('## Самостоятельная работа')[0]
  failures=[x.split('|')[1].strip() for x in sec.splitlines() if x.startswith('| ') and '---' not in x and 'Наблюдение' not in x]
 independent=(f'Решите изменённый вариант исходной ситуации: **{scen}** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.')
 t=re.sub(r'## Самостоятельная работа\n\n.*?\n\n## Проверка понимания', '## Самостоятельная работа\n\n'+independent+'\n\n## Проверка понимания',t,flags=re.S)
 qs=[]
 for x in terms[:3]: qs.append(f'1. Объясните `{x}` через механизм и приведите пример из этой главы, а не словарную формулировку.')
 if failures: qs.append(f'1. Почему симптом «{failures[0]}» ещё не доказывает единственную причину?')
 qs.append('1. Какая независимая проверка отличает выполненную команду от достигнутого результата?')
 qtext='\n'.join(qs)
 t=re.sub(r'## Проверка понимания\n\n.*?\n\n## Источники проекта','## Проверка понимания\n\n'+qtext+'\n\n## Источники проекта',t,flags=re.S)
 finish=', '.join(f'`{x}`' for x in terms[:3])
 cond=f'Глава завершена, если вы можете связно объяснить {finish}, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.'
 t=re.sub(r'## Условие перехода\n\n.*?\n?$','## Условие перехода\n\n'+cond+'\n',t,flags=re.S)
 t=t.replace('\ufffd','')
 f.write_text(t)
# Other files corruption and central safety rule
for name in ['BOOK.md','INSTRUCTOR_NOTES.md','README.md','00_BOOK_MAP.md','00_AUTHORING_STANDARD.md']:
 p=R/name
 if p.exists(): p.write_text(p.read_text().replace('програм��ы','программы').replace('��справляет','исправляет').replace('\ufffd',''))
p=R/'BOOK.md'; t=p.read_text(); marker='6. Ведите `learning-log.md`: дата, задача, ошибка, механизм, исправление.\n'
t=t.replace(marker,marker+'7. Все destructive-действия, firewall/DNS changes, `--drop`, restore поверх данных и production credentials сначала отрабатываются на lab; перед production нужен change с rollback.\n')
p.write_text(t)
print('FINALIZED')
