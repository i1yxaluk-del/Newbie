#!/usr/bin/env python3
"""VM: исправить только параметры числовых карточек, сохранив данные и панели.

Перед каждым обновлением сохраняет прежний объект в закрытый каталог backup.
Не требует рестарта Wazuh и не изменяет источники/правила/представление индекса.
"""
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import ssl
from urllib.request import Request, urlopen

from dashboards import objects


def main():
    os.umask(0o077)
    root = Path('/home/service/wazuh-lab')
    credentials = json.loads((root / 'credentials.json').read_text())
    headers = {'Authorization': 'Basic ' + base64.b64encode(('admin:' + credentials['admin']).encode()).decode(),
               'osd-xsrf': 'true', 'Content-Type': 'application/json'}
    context = ssl._create_unverified_context()
    backup = root / 'business-backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-metrics')
    backup.mkdir(parents=True)
    for item in objects():
        if item['type'] != 'visualization':
            continue
        url = 'https://192.168.114.10/api/saved_objects/visualization/' + item['id']
        with urlopen(Request(url, headers=headers), context=context, timeout=20) as response:
            previous = json.load(response)
        (backup / (item['id'] + '.json')).write_text(json.dumps(previous, ensure_ascii=False, indent=2))
        attributes = previous['attributes']
        attributes['visState'] = item['attributes']['visState']
        request = Request(url, data=json.dumps({'attributes': attributes, 'references': previous['references']}).encode(),
                          headers=headers, method='PUT')
        with urlopen(request, context=context, timeout=20) as response:
            result = json.load(response)
        print('Исправлена карточка:', result['id'])
    print('Исходные объекты:', backup)


if __name__ == '__main__':
    main()
