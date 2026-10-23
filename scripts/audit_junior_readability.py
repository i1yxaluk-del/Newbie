#!/usr/bin/env python3
"""Составить воспроизводимую карту пояснений в отслеживаемых исходниках.

Запуск из корня: python scripts/audit_junior_readability.py --output <report.md>
Только читает Git-файлы; с --output создаёт отчёт. Секреты/содержимое кода не выводит.
Подсчёт комментариев — признак для ручной проверки, а не оценка понятности.
"""
import argparse
import ast
from collections import Counter
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = {".py", ".sh", ".ps1", ".js", ".jsx", ".ts", ".tsx", ".yml", ".yaml", ".conf", ".cfg", ".ini", ".tf", ".j2", ".json", ".xml", ".html", ".css", ".service", ".timer", ".pp"}


def inspect(path):
    """Вернуть только числа: строки, комментарии, функции и строки без docstring."""
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    comments = sum(line.lstrip().startswith(("#", "//", "/*", "*", "<!--", ";")) for line in lines)
    functions = 0
    undocumented = []
    docstrings = 0
    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return len(lines), comments, 0, ["ошибка разбора"], 0
        docstrings = sum(bool(ast.get_docstring(node)) for node in ast.walk(tree)
                         if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
                # Тесты тоже учитываются: говорящие имена не заменяют разбор фикстур.
                if not ast.get_docstring(node):
                    undocumented.append(str(node.lineno))
    return len(lines), comments, functions, undocumented, docstrings


def main():
    """Обойти только известные Git пути; архив и generated assets считать отдельно."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    args = parser.parse_args()
    paths = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT).decode().split("\0")
    rows = []
    areas = Counter()
    archived = 0
    for relative in sorted(set(filter(None, paths))):
        path = ROOT / relative
        if not path.is_file():
            continue
        if "arhive" in path.parts:
            archived += 1
            continue
        if any(part in {"node_modules", "build", ".git", "secrets"} for part in Path(relative).parts):
            continue
        if path.name in {"package-lock.json", "yarn.lock"} or path.suffix not in EXTENSIONS and not path.name.startswith("Dockerfile"):
            continue
        lines, comments, functions, missing, docstrings = inspect(path)
        areas[Path(relative).parts[0]] += 1
        flags = []
        if not comments and not docstrings:
            flags.append("нет комментариев/строк документации")
        if missing:
            flags.append("Python без docstring: " + ", ".join(missing))
        rows.append((relative, lines, comments, docstrings, functions, "; ".join(flags) or "ручная проверка смысла"))
    report = ["# Карта пояснений в исходниках", "", "Сформировано `scripts/audit_junior_readability.py`. Числа не доказывают понятность: комментарий может быть неверным, а JSON не поддерживает комментарии. Архив не входит в действующую выборку. Секреты и значения переменных не печатаются.", "", f"Проверено файлов: **{len(rows)}**; исключено архивных файлов: **{archived}**.", "", "## По каталогам", ""]
    report += [f"- `{area}`: {count}" for area, count in sorted(areas.items())]
    report += ["", "## Реестр файлов", "", "| Путь | Строк | Комментариев | Python docstring | Python-функций | Повод для разбора |", "|---|---:|---:|---:|---:|---|"]
    report += [f"| `{p}` | {n} | {c} | {d} | {f} | {flag} |" for p, n, c, d, f, flag in rows]
    text = "\n".join(report) + "\n"
    if args.output:
        output = ROOT / args.output
        output.write_text(text, encoding="utf-8")
        print(f"Отчёт: {args.output}; файлов: {len(rows)}")
    else:
        print(text)


if __name__ == "__main__":
    main()
