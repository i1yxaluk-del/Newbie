"""Объекты OpenSearch Dashboards для учебных задач; никаких записей напрямую в индексы.

Сохраняемые поиски/визуализации ссылаются на отдельное представление настоящего
wazuh-alerts-*. Данные поступают только после работы manager/штатных правил.
"""
import json

PATTERN = "msp-business-alerts-v1"
PREFIX = "msp-business-"
CUSTOM = 'rule.groups:"msp_business_lab"'
NATIVE = 'location:"/var/ossec/lab/business-native.log"'
FIM = 'syscheck.path:"/var/ossec/lab/fim/business-control.txt"'
ALL = f"({CUSTOM}) OR ({NATIVE}) OR ({FIM})"


def source(query):
    return {"query": {"language": "lucene", "query": query}, "filter": [],
            "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index"}


def references():
    return [{"name": "kibanaSavedObjectMeta.searchSourceJSON.index", "type": "index-pattern", "id": PATTERN}]


def metric(identifier, title, query):
    state = {"title": title, "type": "metric", "params": {"addTooltip": True, "addLegend": False,
             "type": "metric", "metric": {"percentageMode": False, "useRanges": False,
             "colorSchema": "Green to Red", "metricColorMode": "None",
             "colorsRange": [{"from": 0, "to": 10000}], "labels": {"show": True},
             "invertColors": False, "style": {"bgFill": "#000", "bgColor": False, "labelColor": False,
             "subText": "Учебные события", "fontSize": 48}}},
             "aggs": [{"id": "1", "enabled": True, "type": "count", "schema": "metric", "params": {"customLabel": "События"}}]}
    return {"type": "visualization", "id": PREFIX + identifier, "attributes": {"title": title,
            "visState": json.dumps(state, ensure_ascii=False), "uiStateJSON": "{}",
            "description": "Синтетические/контрольные данные лаборатории, не состояние клиента",
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps(source(query))}}, "references": references()}


def search(identifier, title, query, columns):
    return {"type": "search", "id": PREFIX + identifier, "attributes": {"title": title,
            "description": "Проверяйте run_id, объект, источник и время. Отсутствие строк не доказывает исправность.",
            "columns": columns, "sort": [["timestamp", "desc"]],
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps(source(query))}}, "references": references()}


def dashboard(identifier, title, children):
    panels, refs = [], []
    y = 0
    for i, child in enumerate(children):
        typ = child["type"]
        name = f"panel_{i}"
        wide = typ == "search"
        if wide and i % 3:
            y += 6
        panels.append({"version": "2.19.5", "type": typ, "panelIndex": str(i), "panelRefName": name,
                       "gridData": {"x": 0 if wide else (i % 3)*16, "y": y,
                                    "w": 48 if wide else 16, "h": 14 if wide else 6, "i": str(i)},
                       "embeddableConfig": {}})
        refs.append({"name": name, "type": typ, "id": child["id"]})
        if wide:
            y += 14
        elif i % 3 == 2:
            y += 6
    return {"type": "dashboard", "id": PREFIX + identifier, "attributes": {"title": title,
            "description": "УЧЕБНАЯ ПАНЕЛЬ. Два вымышленных клиента. Фильтр клиента не является разграничением доступа. Период 24 часа; включите msp.run_id для конкретного прогона.",
            "panelsJSON": json.dumps(panels), "optionsJSON": '{"useMargins":true,"hidePanelTitles":false}',
            "timeRestore": True, "timeFrom": "now-24h", "timeTo": "now",
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"query": {"language": "lucene", "query": ALL}, "filter": []})}}, "references": refs}


def objects():
    """Три прикладных панели с общими метриками и отдельными таблицами фактов."""
    index = {"type": "index-pattern", "id": PATTERN, "attributes": {"title": "wazuh-alerts-*", "timeFieldName": "timestamp"}}
    custom = metric("custom-count", "Учебные клиентские события", CUSTOM)
    native = metric("native-count", "Штатные правила SSH", NATIVE)
    fim = metric("fim-count", "Штатный контроль целостности", FIM)
    failures = metric("backup-count", "Ошибки копирования и восстановления", 'rule.id:(100201 OR 100202)')
    controls = metric("controls-count", "Контрольные штатные/согласованные операции", 'rule.id:100200')
    access = metric("access-count", "Доступы и защита узлов", 'rule.id:(100203 OR 100205)')
    cols = ["data.msp.tenant", "data.msp.asset", "data.msp.case", "rule.id", "rule.level", "rule.description", "data.msp.run_id"]
    all_search = search("all-events", "Учебные события клиентов и штатных правил", ALL, cols)
    backup_search = search("backup-events", "Резервные копии, восстановление, доступность приложения", 'data.msp.event:(backup_job OR restore_check OR application_service)', cols)
    access_search = search("access-events", "Доступ, защита, экспорт и изменения", 'data.msp.event:(privilege_change OR config_change OR endpoint_protection OR application_export OR collection_health)', cols)
    native_search = search("native-events", "Штатные сигналы SSH и FIM — исходные факты", f"({NATIVE}) OR ({FIM})", ["rule.id", "rule.description", "decoder.name", "data.srcip", "data.dstuser", "syscheck.path", "location"])
    children = [custom, native, fim, failures, controls, access, all_search, backup_search, access_search, native_search]
    return [index] + children + [dashboard("overview", "МСП · Учебная платформа клиентских задач", [custom,native,fim,all_search]),
           dashboard("continuity", "МСП · Непрерывность учёта и резервные копии", [failures,controls,custom,backup_search]),
           dashboard("security", "МСП · Доступы, изменения и защита", [access,native,fim,access_search,native_search])]
