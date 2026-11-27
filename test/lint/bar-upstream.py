#!/usr/bin/env python3
"""Check whether Omarchy's own bar changed since Islands was last compared with it.

Islands is based on Omarchy's bar (shell/plugins/bar). When Omarchy changes that bar,
Islands may need the same change. test/omarchy-bar.json records a SHA-256 hash of each
upstream file for every Omarchy version Islands was compared with. This check fails
when the Omarchy it reads has other files.

    bar-upstream.py                          the installed Omarchy, or skip
    bar-upstream.py --omarchy DIR            an Omarchy checkout
    bar-upstream.py --record NAME --omarchy DIR
                                             add DIR's files as compared version NAME
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json

from common import ROOT, Report

PIN = ROOT / "test" / "omarchy-bar.json"
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--omarchy", type=Path)
parser.add_argument("--record", metavar="NAME")
args = parser.parse_args()

pin = json.loads(PIN.read_text())
omarchy = args.omarchy or Path("/usr/share/omarchy")
folder = omarchy / pin["path"]
if not folder.is_dir():
    if args.omarchy or args.record:
        raise SystemExit(f"bar upstream: {folder} not found")
    print("bar upstream: no installed Omarchy, skipped (pass --omarchy DIR)")
    raise SystemExit(0)

found = {}
for name in pin["files"]:
    path = folder / name
    found[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

if args.record:
    pin["compared"][args.record] = found
    pin["updated"] = datetime.date.today().isoformat()
    PIN.write_text(json.dumps(pin, indent=2) + "\n")
    print(f"bar upstream: recorded {args.record}")
    raise SystemExit(0)

report = Report("bar upstream")
match = next((version for version, hashes in pin["compared"].items() if hashes == found), None)
if match:
    print(f"bar upstream: {omarchy} has the bar of {match}, which Islands was compared with")
else:
    changed = sorted(name for name in pin["files"]
                     if all(hashes.get(name) != found[name] for hashes in pin["compared"].values()))
    report.fail(PIN, 0, f"Omarchy's bar in {omarchy} changed since the last comparison: {', '.join(changed)}. "
                        f"Compare it with Islands, port what Islands needs, then record it (docs/testing.md).")
report.finish()
