# Testing

All checks live under `test/`, and `test/run.py` is the single entry point. No check changes the running shell, the bar, or the installed plugin.

## Run the checks

```sh
python3 test/run.py                          # portable checks
python3 test/run.py all                      # portable checks, then the QML compile, plugin validation and bar drift
python3 test/run.py all --omarchy ~/omarchy  # the same, against an Omarchy checkout
```

Run `all` before you commit a change to QML or JavaScript. It needs Node 22 or later, Python 3, and, for the QML compile, `quickshell` and an installed Omarchy.

The script finds `test/unit/*.test.*` by file name, so a new test file joins the run automatically.

## What each check proves

| Check | File | What it proves | What it does not prove |
| --- | --- | --- | --- |
| Unit tests | `test/unit/` | The logic in `BarModel.js` and in the island settings of `Bar.qml`, and that the README documents every `islands` setting | QML bindings, rendering, Hyprland |
| QML rules | `test/lint/qml-rules.py` | Plain-text sinks, `Style.duration()`, no ease-in or bounce curves, no Omarchy catalog keys, no hard-coded words | That the text reads well |
| i18n | `test/lint/i18n.py` | Skipped: Islands has no strings of its own yet | |
| Manifest | `test/lint/manifest.py` | The manifest fields, and that the version agrees with `CHANGELOG.md` | |
| Docs | `test/lint/docs.py` | Relative links and `#anchors` in Markdown resolve | That a document is true |
| Host API | `test/lint/host-api.py` | Every Omarchy module, type, property, singleton member and `omarchy-*` command Islands uses exists. Every member of `shell`, `barWidgetRegistry`, `pluginRegistry` and the plugin bar API that Islands uses exists. Islands declares what Omarchy's shell sets and calls on a bar. | Behavior of those APIs |
| QML compile | `test/lint/compile-qml.py` | `Bar.qml` compiles against the installed shell | Rendering, runtime errors |
| Plugin validation | `omarchy-plugin-validate` | The exported plugin passes Omarchy's own validator | Anything at runtime |
| Bar drift | `test/lint/bar-upstream.py` | Omarchy's own bar is one that Islands was compared with | That Islands has every upstream feature |

Two files configure the host API check:

- `test/host-objects.json` maps each object that Omarchy hands the bar to the shell file that defines it.
- `test/host-gaps.json` lists known gaps, each with a reason. A listed gap does not fail. A listed entry that is no longer a gap fails, so the list stays true.

The unit tests load the production functions with `test/helpers/qml-functions.cjs` and run them with fake inputs. Because they run the real function bodies, a change to the logic changes the test result.

The lint scripts and `test/run.py` are the same files as in [Omaspaces](https://github.com/DanielLob-o/OmaSpaces). When you change one, copy it to the other repository.

## Omarchy's bar

Islands is based on Omarchy's own bar, `shell/plugins/bar/Bar.qml` and `BarModel.js`. `test/omarchy-bar.json` records a SHA-256 hash of those files for each Omarchy version Islands was compared with. The bar drift check fails when the Omarchy it reads has other files.

When the bar drift check fails:

1. In an Omarchy checkout, show what changed since the last compared version:

   ```sh
   git diff v4.6.0-rc1 quattro -- shell/plugins/bar/
   ```

2. Port the changes that Islands needs to `Bar.qml` and `BarModel.js`.
3. Run `python3 test/run.py all --omarchy ~/omarchy`.
4. Record the new version:

   ```sh
   python3 test/lint/bar-upstream.py --record <version> --omarchy ~/omarchy
   ```

5. Remove versions from `test/omarchy-bar.json` that Islands no longer supports.

## Continuous integration

`.github/workflows/checks.yml` runs on every pull request, on pushes to `main`, and every Monday. It has three jobs:

1. **Portable checks** runs `test/run.py`.
2. **Omarchy v4.5.0** runs `test/run.py all` against the oldest supported release.
3. **Omarchy quattro** runs `test/run.py all` against Omarchy's development branch.

The Omarchy jobs check out Omarchy's `shell/`, `bin/` and `default/i18n/` into `.omarchy/`. CI has no `quickshell`, so the QML compile is skipped there. Run `test/run.py all` locally before a release.

When the `quattro` job fails and the others pass, the next Omarchy release changes something Islands depends on: an API, or its own bar. Fix Islands before that release ships.

When Islands drops support for an old Omarchy release, change the oldest release in three places:

1. The `ref` list in `.github/workflows/checks.yml`.
2. The Requirements section in `README.md`.
3. The compared versions in `test/omarchy-bar.json`.

## Manual checks

The checks do not open popups, click, or read the screen. Before a release:

1. Copy Islands into `~/.config/omarchy/plugins/lobo.islands` and run `omarchy bar use lobo.islands`.
2. Run `journalctl --user -b | grep lobo.islands` and look for errors.
3. Check each island, the tray drawer, a panel, a tooltip, and a widget drag.
4. Run `omarchy toggle animations` and check that the bar colors change without a fade.
