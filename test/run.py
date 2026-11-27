#!/usr/bin/env python3
"""Run the plugin's checks. See docs/testing.md.

    test/run.py                     portable checks: unit tests, lint, host API, docs, whitespace
    test/run.py all                 portable checks, then the QML compile, plugin validation and,
                                    for a plugin based on Omarchy's bar, the upstream drift check
    test/run.py --omarchy DIR ...   check against an Omarchy checkout instead of the installed one

Nothing here changes the running shell, the bar, or the installed plugin.
"""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LINT = ROOT / "test" / "lint"


def run(label, command):
    print(f"--- {label}", flush=True)
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.strip()
    if result.returncode:
        print(output)
        print(f"FAILED: {label}")
    else:
        for line in output.splitlines():
            if line.rstrip().endswith("skipped") or ", skipped" in line:
                print(line)
    return result.returncode == 0


def omarchy_args(omarchy):
    return ["--omarchy", str(omarchy)] if omarchy else []


def portable(omarchy):
    tests = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "test" / "unit").glob("*.test.*"))
    locales = ["--locales", str(omarchy / "default" / "i18n" / "locales.json")] if omarchy else []
    return [
        run("unit tests", ["node", "--test", *tests]),
        run("qml rules", [sys.executable, LINT / "qml-rules.py"]),
        run("i18n", [sys.executable, LINT / "i18n.py", *locales]),
        run("manifest", [sys.executable, LINT / "manifest.py"]),
        run("docs", [sys.executable, LINT / "docs.py"]),
        run("host api", [sys.executable, LINT / "host-api.py", *omarchy_args(omarchy)]),
        run("whitespace", ["git", "diff", "HEAD", "--check"]),
    ]


def validate(omarchy):
    """Validate a clean export: ignored local files are not part of a release."""
    validator = omarchy / "bin" / "omarchy-plugin-validate" if omarchy else shutil.which("omarchy-plugin-validate")
    if not validator or not Path(validator).exists():
        print("--- plugin validation\nplugin validation: no omarchy-plugin-validate, skipped")
        return True
    files = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                           cwd=ROOT, stdout=subprocess.PIPE, check=True).stdout.decode().split("\0")
    with tempfile.TemporaryDirectory(prefix="plugin-export-") as folder:
        for name in filter(None, files):
            if (ROOT / name).is_file():
                target = Path(folder) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, target)
        return run("plugin validation", ["bash", str(validator), folder])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", nargs="?", default="portable", choices=["portable", "all"])
    parser.add_argument("--omarchy", type=Path, help="an Omarchy checkout that holds shell/ and bin/")
    args = parser.parse_args()
    omarchy = args.omarchy.resolve() if args.omarchy else None

    results = portable(omarchy)
    if args.mode == "all":
        results += [run("compile qml", [sys.executable, LINT / "compile-qml.py"]), validate(omarchy)]
        if (LINT / "bar-upstream.py").exists():
            results.append(run("omarchy bar drift", [sys.executable, LINT / "bar-upstream.py", *omarchy_args(omarchy)]))
    print(f"{sum(results)}/{len(results)} checks passed")
    raise SystemExit(0 if all(results) else 1)


main()
