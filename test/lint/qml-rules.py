#!/usr/bin/env python3
"""Check the plugin QML against the rules in Omarchy's plugin guide.

- plain-text: every Text or Label sets textFormat: Text.PlainText, or is a PlainText.
  AutoText reads markup in untrusted text, e.g. <img src="...">, as rich text.
- motion: animation durations go through Style.duration(), so they follow
  `omarchy toggle animations`, and no curve eases in or bounces.
- omarchy-catalog: the plugin does not read Omarchy's own catalog through I18n.t(),
  because Omarchy can rename or drop those keys in any update.
- hard-coded-text: user-facing properties get their words from the plugin catalog.
  An argument to a call, such as a setting key in setting("text", ""), is not text.
  Add `// i18n-ignore: <reason>` to a line that must stay as it is (a brand name).
"""
import re

from common import Report, block_at, code_only, line_of, runtime_files

report = Report("qml rules")

TEXT_TYPE = re.compile(r"(?<![\w.])(Text|Label)\s*\{")
PLAIN = re.compile(r"textFormat\s*:\s*Text\.PlainText")
DURATION = re.compile(r"\bduration\s*:(?!\s*Style\.duration\()")
EASE_IN = re.compile(r"\bEasing\.(In\w*|OutIn\w*|\w*(Bounce|Elastic|Back))\b")
OMARCHY_CATALOG = re.compile(r"\bI18n\.tn?\(")
TEXT_PROPERTY = re.compile(r"^\s*(text|tooltipText|placeholderText|iconText|label)\s*:(.*)$")
STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')
CALL_ARGUMENT = re.compile(r"[\w)]\(\s*$|,\s*$")
WORD = re.compile(r"[A-Za-z]{2,}")
ESCAPE = re.compile(r"\\u[0-9A-Fa-f]{4}|\\x[0-9A-Fa-f]{2}")

for path in runtime_files(".qml"):
    source = path.read_text()
    code = code_only(source)
    raw_lines = source.split("\n")

    for match in TEXT_TYPE.finditer(code):
        block = block_at(code, match.end() - 1)
        if not PLAIN.search(block):
            report.fail(path, line_of(code, match.start()),
                        f"plain-text: {match.group(1)} without textFormat: Text.PlainText; use PlainText")

    for match in DURATION.finditer(code):
        report.fail(path, line_of(code, match.start()), "motion: use duration: Style.duration(ms)")

    for match in EASE_IN.finditer(code):
        report.fail(path, line_of(code, match.start()),
                    f"motion: {match.group(0)} eases in or bounces; use Easing.OutCubic or Style.easeOut")

    for match in OMARCHY_CATALOG.finditer(code):
        report.fail(path, line_of(code, match.start()),
                    "omarchy-catalog: read strings from the plugin's i18n/ catalog, not Commons.I18n")

    for number, line in enumerate(code.split("\n"), start=1):
        prop = TEXT_PROPERTY.match(line)
        if not prop or "i18n-ignore" in raw_lines[number - 1]:
            continue
        value = prop.group(2)
        for literal in STRING.finditer(value):
            if WORD.search(ESCAPE.sub("", literal.group(1))) and not CALL_ARGUMENT.search(value[:literal.start()]):
                report.fail(path, number,
                            f'hard-coded-text: "{literal.group(1)}" in {prop.group(1)}; put it in i18n/en.json')

report.finish()
