"""Контракт учебного комплекта: уникальные ID, существующие ссылки панелей и фикстуры."""
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[2] / "deploy/wazuh-lab/business"


def load(name):
    spec = importlib.util.spec_from_file_location("business_" + name, BASE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rule_ids_and_fixture_expectations():
    tree = ET.parse(BASE / "rules.xml")
    ids = [node.attrib["id"] for node in tree.findall("rule")]
    assert len(ids) == len(set(ids)) == 9
    scenarios = json.loads((BASE / "scenarios.json").read_text())
    assert len(scenarios) == 12
    assert all(item["expected_rule"] in ids for item in scenarios)
    assert sum(item["expected_rule"] == "100200" for item in scenarios) == 4


def test_saved_objects_have_resolvable_references():
    objects = load("dashboards").objects()
    keys = {(item["type"], item["id"]) for item in objects}
    assert len(keys) == len(objects)
    assert sum(item["type"] == "dashboard" for item in objects) == 3
    for item in objects:
        for ref in item.get("references", []):
            assert (ref["type"], ref["id"]) in keys
        if item["type"] == "dashboard":
            json.loads(item["attributes"]["panelsJSON"])
        if item["type"] == "visualization":
            # metricVis преобразует fontSize в число: отсутствие ломает рендер,
            # даже когда сохранение объекта и запрос к индексу успешны.
            state = json.loads(item["attributes"]["visState"])
            assert isinstance(state["params"]["metric"]["style"]["fontSize"], (int, float))


def test_generated_event_is_explicitly_synthetic():
    scenario = json.loads((BASE / "scenarios.json").read_text())[0]
    event = load("generate").make_event(scenario, "test-run")
    assert event["msp"]["synthetic"] == "true"
    assert event["msp"]["run_id"] == "test-run"
    assert event["msp"]["source"] == "training-fixture"
