# Changelog

All notable changes to Islands. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version numbers follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Checks: `python3 test/run.py` runs unit tests and lint checks, and GitHub Actions runs them on every push and pull request. CI also checks Islands against the oldest supported Omarchy release and against Omarchy's development branch, and reports when Omarchy's own bar changes. See [docs/testing.md](docs/testing.md).
- The `centerBegin` and `centerEnd` bar sections, drawn on the center island.
- The `tray` section, drawn inside the tray's drawer.
- An `auto` island color that follows the Omarchy theme.
- Documentation of widgets that do not work under a third-party bar.

### Changed

- Animations follow `omarchy toggle animations`, and the bar colors change with Omarchy's ease-out curve.
- The center peek opens only over the center island.

### Fixed

- Islands loads on Omarchy 4.6, which removed `ScreenMoveRemap` and the center peek properties of the plugin bar API.
- The background of a collapsed tray island.
- Bar tooltips at fractional scales: they stay hidden until the popup scale matches the bar, and their border stays inside the surface.
- Unreadable popup panels on light themes.
- A click on a widget beside a collapsed tray drawer no longer opens a widget from the `tray` section. A click target now counts only where a clipping or hidden parent does not cut it off.

## [1.0.0] - 2026-09-29

### Added

- First release: the Omarchy bar split into floating islands for the left, center, and right sections.

[Unreleased]: https://github.com/DanielLob-o/Islands/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/DanielLob-o/Islands/releases/tag/v1.0.0
