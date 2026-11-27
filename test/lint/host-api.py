#!/usr/bin/env python3
"""Check that the Omarchy shell API the plugin uses exists in an Omarchy version.

Reads the plugin QML and an Omarchy source tree, and fails when the plugin uses
something that tree does not have:

- a module it imports (qs.Ui, qs.Commons, ...),
- a type, for every capitalized type that is not local and not a known Qt type,
- a property, signal handler, or member it uses on an Omarchy type,
- a member of an Omarchy singleton (Style.duration, Util.wheelSteps, ...),
- a member of an object Omarchy hands the plugin, as test/host-objects.json maps
  them (for a bar widget, `bar` is Ui/PluginBarApi.qml), unless the code guards it
  with `typeof x.member` or `"member" in x`,
- for a full bar (kind "bar"): a property Omarchy sets on the bar, or a member it
  reads or calls on it (shell.qml: configureBar and shell.bar.*),
- an omarchy-* command it runs.

test/host-gaps.json lists known gaps, as {"bar.name": "why"}: those do not fail, and an
entry that is no longer a gap fails, so the list stays true.

It runs without a desktop, so CI can point it at any Omarchy checkout:

    host-api.py                      the installed Omarchy (/usr/share/omarchy), or skip
    host-api.py --omarchy DIR        an Omarchy checkout (holds shell/ and bin/)
"""
from pathlib import Path
import argparse
import json
import re

from common import ROOT, Report, block_at, code_only, line_of, manifest, runtime_files

parser = argparse.ArgumentParser()
parser.add_argument("--omarchy", type=Path)
args = parser.parse_args()
omarchy = args.omarchy or Path("/usr/share/omarchy")
if not (omarchy / "shell").is_dir():
    if args.omarchy:
        raise SystemExit(f"host api: {omarchy}/shell not found")
    print("host api: no installed Omarchy, skipped (pass --omarchy DIR)")
    raise SystemExit(0)

report = Report(f"host api ({omarchy})")
SHELL = omarchy / "shell"

# Qt and Quickshell types the plugin may use. Add a type here when the plugin starts to use it.
QT_TYPES = {
    "Item", "Rectangle", "Text", "Image", "Column", "Row", "Grid", "Flow", "Repeater", "Loader",
    "MouseArea", "HoverHandler", "TapHandler", "WheelHandler", "Timer", "Connections", "Flickable",
    "Behavior", "ColorAnimation", "NumberAnimation", "QtObject", "Process", "StdioCollector",
    "FileView", "ShellRoot", "Variants", "PopupWindow", "PanelWindow", "GridLayout", "RowLayout",
    "ColumnLayout", "Component", "SplitParser", "Region", "IpcHandler", "Scope", "LazyLoader",
    "Instantiator", "SequentialAnimation", "ParallelAnimation", "PauseAnimation", "PropertyAnimation",
    "ScriptAction", "DragHandler", "PointHandler", "DropArea", "Canvas",
}

# Members of the Qt base types that Omarchy components are built on.
ITEM = {
    "id", "objectName", "parent", "x", "y", "z", "width", "height", "implicitWidth", "implicitHeight",
    "visible", "enabled", "opacity", "clip", "scale", "rotation", "focus", "activeFocus", "anchors",
    "states", "transitions", "layer", "children", "data", "smooth", "antialiasing", "transform",
    "transformOrigin", "baselineOffset", "Layout", "LayoutMirroring", "Component", "Keys", "QsWindow",
    "mapToItem", "mapFromItem", "forceActiveFocus", "childAt", "contains",
    "left", "right", "top", "bottom", "horizontalCenter", "verticalCenter", "baseline",
}
BASES = {
    "QtObject": {"id", "objectName", "Component"},
    "Item": ITEM,
    "Rectangle": ITEM | {"color", "radius", "border", "gradient"},
    "PopupWindow": ITEM | {"anchor", "color", "screen", "mask", "surfaceFormat"},
    "TextField": ITEM | {
        "text", "placeholderText", "placeholderTextColor", "font", "color", "readOnly", "echoMode",
        "validator", "inputMethodHints", "maximumLength", "selectByMouse", "horizontalAlignment",
        "verticalAlignment", "padding", "leftPadding", "rightPadding", "topPadding", "bottomPadding",
        "background", "cursorPosition", "selectedText", "accepted", "editingFinished", "textEdited",
        "selectAll", "clear", "hovered",
    },
}

DECLARATION = re.compile(
    r"^\s*(?:(?:default|required|readonly)\s+)*(?:property\s+[\w<>.]+\s+(\w+)|property\s+alias\s+(\w+)"
    r"|signal\s+(\w+)|function\s+(\w+))")
ROOT_TYPE = re.compile(r"^((?:\w+\.)?[A-Z]\w*)\s*\{", re.M)
BLOCK = re.compile(r"(?<![\w.])((?:[A-Z]\w*\.)?[A-Z]\w*)\s*\{")
ASSIGNMENT = re.compile(r"^\s*((?:[A-Z]\w*\.)?[a-zA-Z_]\w*)(?:\.\w+)*\s*:(?!:)")
IMPORT = re.compile(r"^import\s+(qs\.[\w.]+)(?:\s+as\s+(\w+))?\s*$", re.M)


def depth_one(code):
    """Lines that sit directly inside the outermost block of code."""
    depth, out = 0, []
    for line in code_only(code, keep_strings=False).split("\n"):
        if depth == 1:
            out.append(line)
        depth += line.count("{") - line.count("}")
    return out


def declared(code):
    names = set()
    for line in depth_one(code):
        match = DECLARATION.match(line)
        if match:
            names.add(next(group for group in match.groups() if group))
    return names


class Module:
    def __init__(self, name):
        self.directory = SHELL / name.split(".", 1)[1].replace(".", "/")
        self.types, self.singletons = {}, set()
        qmldir = self.directory / "qmldir"
        if not qmldir.is_file():
            return
        for line in qmldir.read_text().split("\n"):
            parts = line.split()
            if len(parts) >= 3 and parts[-1].endswith(".qml"):
                self.types[parts[-3]] = self.directory / parts[-1]
                if parts[0] == "singleton":
                    self.singletons.add(parts[-3])


_members = {}


def host_members(path, seen=()):
    """Members a host type declares, with those of its root type and Qt base."""
    if path in _members:
        return _members[path]
    source = code_only(path.read_text())
    names = declared(source)
    root = ROOT_TYPE.search(source)
    base = root.group(1).split(".")[-1] if root else "QtObject"
    sibling = path.parent / f"{base}.qml"
    if sibling.is_file() and sibling != path and sibling not in seen:
        names |= host_members(sibling, seen + (path,))
    elif base in BASES:
        names |= BASES[base]
    else:
        names.add(f"?{base}")  # Unknown Qt base: members not declared above cannot be checked.
    _members[path] = names
    return names


def allows(members, name):
    if name in members:
        return True
    if name.startswith("on") and len(name) > 2:
        event = name[2].lower() + name[3:]
        return event in members or (event.endswith("Changed") and event[:-7] in members)
    return False


def unknown_base(members):
    return next((name[1:] for name in members if name.startswith("?")), None)


local_types = {path.stem for path in runtime_files(".qml")}
for path in runtime_files(".qml"):
    local_types.update(re.findall(r"^\s*component\s+(\w+)\s*:", path.read_text(), re.M))

# Objects Omarchy hands the plugin: variable name -> the shell file that defines it.
objects_file = ROOT / "test" / "host-objects.json"
host_objects = json.loads(objects_file.read_text()) if objects_file.is_file() else {}
object_members = {}
for name, relative in host_objects.items():
    if (SHELL / relative).is_file():
        object_members[name] = declared(code_only((SHELL / relative).read_text()))
    else:
        report.fail(objects_file, 0, f"{name}: {relative} does not exist in this Omarchy")


gaps_file = ROOT / "test" / "host-gaps.json"
known_gaps = json.loads(gaps_file.read_text()) if gaps_file.is_file() else {}
seen_gaps = set()


def known(key):
    if key in known_gaps:
        seen_gaps.add(key)
        return True
    return False


def guarded(code, owner, member):
    """True when the code checks for the member before it uses it."""
    owner = re.escape(owner)
    return bool(re.search(rf"typeof\s+(?:\w+\.)*{owner}\.{member}\b", code)
                or re.search(rf"[\"']{member}[\"']\s+in\s+(?:\w+\.)*{owner}\b", code))

for path in runtime_files(".qml"):
    source = path.read_text()
    code = code_only(source)
    bare_code = code_only(source, keep_strings=False)
    modules = []
    for match in IMPORT.finditer(code):
        module = Module(match.group(1))
        if not module.types:
            report.fail(path, line_of(code, match.start()), f"module {match.group(1)} does not exist")
        modules.append((match.group(2) or "", module))

    def resolve(type_name):
        alias, _, name = type_name.rpartition(".")
        for module_alias, module in modules:
            if module_alias == alias and name in module.types:
                return module.types[name]
        return None

    # Singletons, qualified (Commons.Style.x) or not (Style.x).
    for alias, module in modules:
        for singleton in module.singletons:
            prefix = (alias + r"\.") if alias else r"(?<![\w.])"
            for match in re.finditer(prefix + singleton + r"\.(\w+)", bare_code):
                if not allows(host_members(module.types[singleton]), match.group(1)):
                    report.fail(path, line_of(code, match.start()),
                                f"{singleton}.{match.group(1)} does not exist in {module.types[singleton].name}")

    for match in BLOCK.finditer(code):
        type_name = match.group(1)
        line = line_of(code, match.start())
        host = resolve(type_name)
        if host is None:
            bare = type_name.split(".")[-1]
            if bare not in local_types and bare not in QT_TYPES and not any(
                    bare in m.singletons for _, m in modules):
                report.fail(path, line, f"type {type_name} is not local, not a known Qt type, "
                                        f"and not in an imported Omarchy module")
            continue
        block = block_at(code, match.end() - 1)
        members = host_members(host) | declared(block)
        base = unknown_base(members)
        for offset, text in enumerate(depth_one(block)):
            assignment = ASSIGNMENT.match(text)
            if not assignment or assignment.group(1)[0].isupper() or allows(members, assignment.group(1)):
                continue
            if base:
                report.fail(path, line + offset + 1, f"{type_name}.{assignment.group(1)}: add Qt type "
                                                     f"{base} to BASES so its members can be checked")
            else:
                report.fail(path, line + offset + 1,
                            f"{type_name} has no property or signal {assignment.group(1)!r} in {host.name}")
        # Accesses through the block's id, e.g. root.setting(...) or profilesPopup.open.
        ident = re.search(r"^\s*id\s*:\s*(\w+)", "\n".join(depth_one(block)), re.M)
        if ident:
            for access in re.finditer(r"(?<![\w.])" + ident.group(1) + r"\.(\w+)", bare_code):
                if not allows(members, access.group(1)) and not base:
                    report.fail(path, line_of(code, access.start()),
                                f"{ident.group(1)}.{access.group(1)}: not declared here or in {host.name}")

    for name, members in object_members.items():
        for match in re.finditer(rf"(?<!\w){name}\.(\w+)", bare_code):
            member = match.group(1)
            if member not in members and not guarded(code, name, member) and not known(f"{name}.{member}"):
                report.fail(path, line_of(code, match.start()),
                            f"{name}.{member} does not exist in {host_objects[name]}")

# A full bar: what Omarchy's shell sets on it and reads or calls on it.
data = manifest()
bar_entry = data.get("entryPoints", {}).get("bar") if "bar" in data.get("kinds", []) else None
shell_qml = SHELL / "shell.qml"
if bar_entry and shell_qml.is_file():
    shell_code = code_only(shell_qml.read_text())
    configure = re.search(r"function configureBar\b", shell_code)
    wanted = set(re.findall(r"\bshell\.bar\.(\w+)", shell_code))
    if configure:
        wanted |= set(re.findall(r"\"(\w+)\"\s+in\s+target", block_at(shell_code, shell_code.index("{", configure.end()))))
    own = declared(code_only((ROOT / bar_entry).read_text()))
    for name in sorted(wanted - own):
        if known(f"bar.{name}"):
            continue
        report.fail(ROOT / bar_entry, 0, f"Omarchy's shell.qml uses bar.{name}, which this bar does not declare")

# Commands: the first word of a command line, or the first item of an argument list.
COMMAND = re.compile(r"(?:\[\s*|\brun\(\s*|\bexecDetached\(\s*)[\"'](omarchy-[a-z0-9-]+)[\"' ]|[\"'](omarchy-[a-z0-9-]+) ")
for path in runtime_files(".qml", ".js"):
    code = code_only(path.read_text())
    for match in COMMAND.finditer(code):
        command = match.group(1) or match.group(2)
        if not (omarchy / "bin" / command).exists():
            report.fail(path, line_of(code, match.start()), f"command {command} is not in {omarchy}/bin")

for key in sorted(set(known_gaps) - seen_gaps):
    report.fail(gaps_file, 0, f"{key} is no longer a gap in this Omarchy; remove it from the list")

report.finish()
