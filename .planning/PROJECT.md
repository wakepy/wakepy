# wakepy

## What This Is

wakepy is a cross-platform Python library and CLI tool that prevents system suspend/sleep via native OS and desktop environment APIs. It targets developers and end users who need to keep systems awake during long-running tasks. The library provides a clean, ergonomic API (context manager, decorator, explicit enter/exit) backed by platform-specific method plugins.

## Core Value

Reliably prevent system sleep across Windows, Linux, and macOS with a minimal, intuitive API — if the mode activation fails, the user must know clearly.

## Requirements

### Validated

- ✓ Context manager syntax (`with keep.running() as mode`) — existing
- ✓ Decorator syntax (`@keep.running()`) — existing
- ✓ Explicit enter/exit (`mode.enter()` / `mode.exit()`) — existing
- ✓ Plugin-based method registry (platform-specific implementations auto-discovered) — existing
- ✓ ActivationResult with detailed failure diagnostics — existing
- ✓ on_fail handling (error / warn / custom callback) — existing
- ✓ Thread-safe mode tracking via ContextVar — existing
- ✓ keep.running and keep.presenting modes — existing
- ✓ CLI interface — existing
- ✓ D-Bus integration for Linux DEs — existing
- ✓ Lifecycle hooks (before_enter, after_enter, before_exit, after_exit, on_success) — Validated in Phase 1: Complete Lifecycle Hooks

### Active

*(Set per milestone — see ROADMAP.md for current phase scope)*

### Out of Scope

- GUI application — library/CLI only
- Platform-specific sleep scheduling — only inhibition, not scheduling

## Context

- Python library distributed via PyPI; strict mypy, 100% test coverage required
- Plugin architecture: new platform Methods added without changing core
- Current branch: `lifecycle-hooks` — implementing issue #599 (lifecycle hooks) and related issues #598, #605
- Issues tracked at: https://github.com/wakepy/wakepy/issues
- One GSD phase per GitHub issue; milestones group related issues

## Constraints

- **Language**: Python — library target
- **Typing**: mypy strict mode — all code must be fully typed
- **Coverage**: 100% test coverage — enforced in CI
- **Testing**: pytest with classes, fixtures preferred
- **Build**: uv — `uv run python` not `python` directly

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| One GSD phase per GitHub issue | Issues are well-scoped, atomic units of work | — Pending |
| before_enter / after_enter / before_exit / after_exit / on_success hooks | Mirrors issue #599 specification | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-28 after Phase 1: Complete Lifecycle Hooks*
