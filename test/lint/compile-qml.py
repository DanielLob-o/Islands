#!/usr/bin/env python3
"""Compile every plugin QML file against the installed Omarchy shell.

Starts a separate, short-lived Quickshell with a temporary config that links the
installed qs.Commons and qs.Ui. It does not touch the running shell, the bar, or the
installed plugin. Nothing is shown on screen: components are compiled, and only
PlainText is created, to check that markup in it stays plain text.

Needs quickshell and an installed Omarchy; skips without them.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import threading

from common import ROOT, Report, runtime_files

HOST = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
if not shutil.which("quickshell") or not (HOST / "Ui").is_dir():
    print("compile qml: needs quickshell and an installed Omarchy, skipped")
    raise SystemExit(0)

report = Report("compile qml")
names = [path.relative_to(ROOT).as_posix() for path in runtime_files(".qml")]
MARKUP = '<b>bold</b><img src="https://example.invalid/x.png">'

with tempfile.TemporaryDirectory(prefix="plugin-qml-") as directory:
    config = Path(directory)
    for module in ("Commons", "Ui"):
        (config / module).symlink_to(HOST / module, target_is_directory=True)
    # json.dumps writes the names and the markup as JavaScript string literals.
    (config / "shell.qml").write_text(f"""import QtQuick
import Quickshell
ShellRoot {{
  Component.onCompleted: {{
    // A file:// URL, as Omarchy loads a plugin, so the plugin's own folder types resolve.
    const base = {json.dumps(ROOT.as_uri() + "/")}
    for (const name of {json.dumps(names)}) {{
      const component = Qt.createComponent(base + name)
      if (component.status !== Component.Ready) console.error("COMPILE_FAILED " + name + ": " + component.errorString())
    }}
    const plain = Qt.createComponent(base + "PlainText.qml")
    if (plain.status === Component.Ready) {{
      const item = plain.createObject(null, {{ text: {json.dumps(MARKUP)} }})
      if (item.textFormat !== Text.PlainText || item.text !== {json.dumps(MARKUP)}) console.error("PLAIN_TEXT_FAILED")
      item.destroy()
    }}
    console.log("COMPILE_DONE")
  }}
}}
""")
    platform = "wayland" if os.environ.get("WAYLAND_DISPLAY") else "offscreen"
    # Quickshell keeps running after the probe, so stop it when the probe is done.
    process = subprocess.Popen(["quickshell", "--no-color", "-p", str(config)], text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               env=dict(os.environ, QT_QPA_PLATFORM=platform))
    lines = []
    timer = threading.Timer(30, process.kill)
    timer.start()
    try:
        for line in process.stdout:
            lines.append(line)
            if "COMPILE_DONE" in line:
                break
    finally:
        timer.cancel()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    output = "".join(lines)

for line in output.split("\n"):
    if "COMPILE_FAILED" in line or "PLAIN_TEXT_FAILED" in line or "plugins/" in line and " ERROR" in line:
        report.fail("quickshell", 0, line.strip())
if "COMPILE_DONE" not in output:
    print(output)
    report.fail("quickshell", 0, "the compile probe did not run")
print(f"compile qml: {len(names)} files")
report.finish()
