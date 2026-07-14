---
name: python-pro
description: Python 3.12+ coding standards for litestar-pagination: modern typing, dataclass contracts, optional integration boundaries, Ruff ALL rules, cursor validation, and public API conventions. Use proactively when writing or reviewing Python code in this project.
---

# Python Pro — litestar-pagination

Use this skill for all Python implementation and review work in this repository.

## Evidence first

- Read `AGENTS.md`, `PRD.md`, `TECHSTACK.md`, and relevant code before editing.
- Use CodeGraph for flows and impact when `.codegraph/` exists.
- Use Context7 for current Litestar, Advanced Alchemy, SQLAlchemy, sqlakeyset, or pytest APIs.
- Do not infer behavior from `fastapi-pagination`; inspect it only as prior art and preserve this project's PRD.

## Python and typing

- Support Python 3.12–3.14 and use built-in generics, `X | None`, PEP 695 type aliases/generics, `Self`, and `override` where useful.
- Fully annotate every public function and method. Keep sync `paginate()` and async `apaginate()` return types precise.
- Use `collections.abc` for `Sequence`, `Callable`, and iterator interfaces.
- Prefer narrow helpers and explicit type guards over repeated `cast()`.
- Put import-only dependencies behind `TYPE_CHECKING` when that preserves optional-import boundaries.

## Public contracts

- Use standard-library dataclasses for `CursorParams` and `CursorPage`; do not add Pydantic.
- Keep root imports lightweight and stable. SQLAlchemy APIs live in `litestar_pagination.ext.sqlalchemy`.
- Do not import optional SQLAlchemy or Advanced Alchemy dependencies from the package root.
- Public query names, response fields, defaults, and cursor semantics come from `PRD.md`.

## Error handling and trust boundaries

- Catch the narrowest exception and chain translated errors with `raise ... from error`.
- Preserve SQLAlchemy execution errors; do not relabel database failures as client input failures.
- Invalid external cursors map to Litestar HTTP 400. Missing ordering and unsupported statement shapes are developer errors.
- Never place decoded bookmark values or sensitive query data in logs or error responses.
- Base64 is encoding, not encryption or signing; do not imply otherwise.

## Ruff and style

- Ruff uses `ALL`, preview mode, Google docstrings, 120-character lines, and Python 3.12 syntax.
- Use `msg = "..."; raise Error(msg)` when required by Ruff's exception-message rules.
- Use stdlib → third-party → local import order.
- Every `# pragma: no cover` must include a reason.
- Prefer deletion and direct code over factories, registries, protocols, and abstractions without two real consumers.

## Verification

Before completion claims, use `verification-before-completion`. For Python changes run the full verification block in `AGENTS.md`.
