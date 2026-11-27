#!/usr/bin/env python3
"""Check the translation catalogs in i18n/.

- en.json exists and holds every key the code asks for, and no key the code never names.
- Each catalog is named after an Omarchy language code, and holds only keys from en.json.
- Each value keeps the %1, %2 placeholders of the English value.
- Plural entries use CLDR categories and always have "other".

Usage: i18n.py [--locales PATH]   PATH is Omarchy's default/i18n/locales.json.
Without it, the installed copy is used, and file names are only checked for shape.
"""
from pathlib import Path
import argparse
import json
import re

from common import ROOT, Report, code_only, runtime_files

report = Report("i18n")
parser = argparse.ArgumentParser()
parser.add_argument("--locales", type=Path, default=Path("/usr/share/omarchy/default/i18n/locales.json"))
args = parser.parse_args()

CATALOGS = ROOT / "i18n"
CATEGORIES = {"zero", "one", "two", "few", "many", "other"}
CALL = re.compile(r"\b(?:tr|trn|t|tn)\(\s*\"([^\"]+)\"")
KEY_LITERAL = re.compile(r"\"([a-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)+)\"")
PLACEHOLDER = re.compile(r"%(\d)")
CODE_SHAPE = re.compile(r"^[a-z]{2,3}(-[A-Z][A-Za-z]{1,3})?$")


def load(path):
    try:
        value = json.loads(path.read_text())
    except ValueError as error:
        report.fail(path, 0, f"not valid JSON: {error}")
        return None
    if not isinstance(value, dict):
        report.fail(path, 0, "must be a JSON object")
        return None
    return value


def forms(path, key, value):
    """The strings in one entry, by plural category ('' for a plain string)."""
    if isinstance(value, str):
        return {"": value}
    if isinstance(value, dict) and value and all(isinstance(v, str) for v in value.values()):
        unknown = set(value) - CATEGORIES
        if unknown:
            report.fail(path, 0, f"{key}: unknown plural categories {sorted(unknown)}")
        if "other" not in value:
            report.fail(path, 0, f'{key}: a plural entry needs "other"')
        return value
    report.fail(path, 0, f"{key}: must be a string or an object of plural forms")
    return {}


def placeholders(text):
    return set(PLACEHOLDER.findall(text))


english_path = CATALOGS / "en.json"
if not CATALOGS.is_dir():
    print("i18n: no i18n/ directory, skipped")
    raise SystemExit(0)
english = load(english_path) if english_path.is_file() else None
if english is None:
    report.fail(english_path, 0, "missing or unreadable; it is the fallback for every language")
    report.finish()

english_forms = {key: forms(english_path, key, value) for key, value in english.items()}

# Keys the code asks for, and every dotted literal it names (a key passed through a helper).
asked, named = {}, set()
for path in runtime_files(".qml", ".js"):
    code = code_only(path.read_text())
    for match in CALL.finditer(code):
        asked.setdefault(match.group(1), f"{path.relative_to(ROOT)}:{code.count(chr(10), 0, match.start()) + 1}")
    named.update(KEY_LITERAL.findall(code))

for key, where in sorted(asked.items()):
    if key not in english:
        report.fail(english_path, 0, f"missing key {key!r}, used at {where}")
for key in sorted(set(english) - named - set(asked)):
    report.fail(english_path, 0, f"unused key {key!r}")

known = None
if args.locales.is_file():
    known = set(json.loads(args.locales.read_text()))
else:
    print(f"i18n: {args.locales} not found, checking only the shape of language codes")

for path in sorted(CATALOGS.glob("*.json")):
    code = path.stem
    if known is not None and code not in known:
        report.fail(path, 0, f"{code!r} is not an Omarchy language code")
    elif known is None and not CODE_SHAPE.match(code):
        report.fail(path, 0, f"{code!r} does not look like a language code")
    if path == english_path:
        continue
    catalog = load(path)
    if catalog is None:
        continue
    for key, value in catalog.items():
        if key not in english:
            report.fail(path, 0, f"key {key!r} is not in en.json")
            continue
        expected = english_forms[key]
        expected_all = set().union(*(placeholders(t) for t in expected.values())) if expected else set()
        for category, text in forms(path, key, value).items():
            found = placeholders(text)
            if found - expected_all:
                report.fail(path, 0, f"{key}: placeholders {sorted(found - expected_all)} are not in English")
            if category in ("", "other") and found != expected_all:
                report.fail(path, 0, f"{key}: needs placeholders {sorted(expected_all)}, has {sorted(found)}")
        if isinstance(value, str) != ("" in expected):
            report.fail(path, 0, f"{key}: English is {'a plain string' if '' in expected else 'a plural entry'}")

report.finish()
