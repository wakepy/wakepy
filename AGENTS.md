You MUST be concise in all messages. You SHOULD prefer brevity over grammatical correctness.

wakepy: Cross-platform Python library/CLI preventing system suspend via native OS/DE APIs.

See `.planning/codebase/` for detailed docs:
- `ARCHITECTURE.md` — layers, data flow, key abstractions
- `STRUCTURE.md` — directory layout, key files, where to add new code
- `CONVENTIONS.md` — naming, imports, error handling, type hints
- `TESTING.md` — fixtures, mocking, coverage, test patterns
- `STACK.md` — dependencies, tools, platform requirements

REQUIREMENTS:
- mypy strict mode (fully typed)
- 100% test coverage
- pytest with classes
- Top-level functions before subfunctions

ALWAYS:
- Instead of "python ARGS" run "uv run python ARGS". Instead of "python3 ARGS" run "uv run python ARGS"
- If changing a file, format and run tests to VERIFY. Does not apply to .md files.
- Prefer writing code that is easily TESTABLE (not requiring patching)
- Prefer using FIXTURES in tests
- When asserting the same attribute twice with different expected values (e.g. after a state change), use the `do_assert` fixture instead of `assert` to avoid mypy [unreachable] errors. Within a single test, do not mix `assert` and `do_assert`.
- Use "just test-cli ARGUMENTS" to run tests (not pytest directly)
- imports at top of file, not inside functions
- To build docs: "uv run sphinx-build -b html docs/source docs/build". Do NOT use "just docs" as it never returns!
