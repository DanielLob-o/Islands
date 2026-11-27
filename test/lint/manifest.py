#!/usr/bin/env python3
"""Check manifest.json beyond what `omarchy plugin validate` checks.

- The fields a catalog listing shows are present, and the version is x.y.z.
- The top entry of CHANGELOG.md is the manifest version.
- For a bar widget with settings: the defaults match the schema, each default fits
  its type, the code reads every setting it declares and declares every setting it
  reads, and the README names every setting.
"""
import re

from common import ROOT, Report, code_only, manifest, runtime_files

report = Report("manifest")
path = ROOT / "manifest.json"
data = manifest()

for field in ("id", "name", "version", "author", "license", "description"):
    if not isinstance(data.get(field), str) or not data[field].strip():
        report.fail(path, 0, f"{field!r} must be a non-empty string")

version = str(data.get("version", ""))
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    report.fail(path, 0, f"version {version!r} is not x.y.z")

changelog = ROOT / "CHANGELOG.md"
if not changelog.is_file():
    report.fail(changelog, 0, "missing")
else:
    top = re.search(r"^## \[?(\d+\.\d+\.\d+)\]?", changelog.read_text(), re.M)
    if not top:
        report.fail(changelog, 0, "no '## [x.y.z]' release heading")
    elif top.group(1) != version:
        report.fail(changelog, 0, f"top release is {top.group(1)}, manifest version is {version}")

license_file = ROOT / "LICENSE"
if not license_file.is_file():
    report.fail(license_file, 0, "missing")
elif data.get("license") == "MIT" and "MIT License" not in license_file.read_text():
    report.fail(license_file, 0, "manifest says MIT, LICENSE is not the MIT license")


def fits(kind, value, field):
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        ok = isinstance(value, int) and not isinstance(value, bool)
        return ok and field.get("min", value) <= value <= field.get("max", value)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "enum":
        return value in field.get("options", [])
    if kind == "object":
        return isinstance(value, dict)
    if kind == "array":
        return isinstance(value, list)
    return isinstance(value, str)


widget = data.get("barWidget") if isinstance(data.get("barWidget"), dict) else {}
schema = widget.get("schema", [])
defaults = widget.get("defaults", {})
if schema:
    keys = [field.get("key") for field in schema]
    if len(keys) != len(set(keys)):
        report.fail(path, 0, "barWidget.schema has duplicate keys")
    if set(keys) != set(defaults):
        report.fail(path, 0, f"barWidget.defaults and schema differ: "
                             f"only in defaults {sorted(set(defaults) - set(keys))}, "
                             f"only in schema {sorted(set(keys) - set(defaults))}")
    for field in schema:
        key = field.get("key")
        for required in ("type", "label", "description"):
            if not field.get(required):
                report.fail(path, 0, f"setting {key!r} needs a {required!r}")
        if "defaultValue" in field:
            if key in defaults and defaults[key] != field["defaultValue"]:
                report.fail(path, 0, f"setting {key!r}: defaults has {defaults[key]!r}, "
                                     f"schema defaultValue is {field['defaultValue']!r}")
            if not fits(field.get("type"), field["defaultValue"], field):
                report.fail(path, 0, f"setting {key!r}: default {field['defaultValue']!r} "
                                     f"does not fit type {field.get('type')!r}")

    # Settings are read with setting("key", ...) or a helper whose name ends in Setting.
    read = set()
    for qml in runtime_files(".qml"):
        read.update(re.findall(r"\b(?:setting|\w+Setting)\(\s*\"(\w+)\"", code_only(qml.read_text())))
    for key in sorted(set(keys) - read):
        report.fail(path, 0, f"setting {key!r} is declared but the code never reads it")
    for key in sorted(read - set(keys)):
        report.fail(path, 0, f"the code reads setting {key!r}, which the schema does not declare")

    readme = (ROOT / "README.md").read_text() if (ROOT / "README.md").is_file() else ""
    for key in keys:
        if f"`{key}`" not in readme:
            report.fail(ROOT / "README.md", 0, f"setting `{key}` is not documented")

report.finish()
