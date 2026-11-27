#!/usr/bin/env python3
"""Check that relative links and images in the Markdown files point at something.

A link to a file must name a tracked or present file, and a #fragment must name a
heading in the target document, using GitHub's heading anchors.
"""
from pathlib import Path
import re

from common import ROOT, Report

report = Report("docs")
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^```.*?^```", re.S | re.M)


def anchors(markdown):
    out = set()
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", FENCE.sub("", markdown), re.M):
        slug = re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")
        out.add(slug)
    return out


documents = [p for p in ROOT.rglob("*.md")
             if not any(part.startswith(".") or part == "node_modules" for part in p.relative_to(ROOT).parts[:-1])]
for document in sorted(documents):
    text = document.read_text()
    for number, line in enumerate(FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text).split("\n"), 1):
        for target in LINK.findall(line):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target):
                continue
            file_part, _, fragment = target.partition("#")
            resolved = (document.parent / file_part).resolve() if file_part else document
            if file_part and not resolved.exists():
                report.fail(document, number, f"link to missing {file_part}")
                continue
            if fragment and resolved.suffix == ".md" and fragment not in anchors(resolved.read_text()):
                report.fail(document, number, f"no heading for #{fragment} in {resolved.relative_to(ROOT)}")

report.finish()
