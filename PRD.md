# Product Requirements Document: litestar-pagination

## 1. Summary

`litestar-pagination` is a standalone PyPI package that adds cursor/keyset pagination to the Litestar ecosystem.

The package provides a storage-independent cursor pagination model and a Litestar-native dependency contract. Its MVP ships SQLAlchemy 2 support powered by `sqlakeyset` and works with sessions supplied by Advanced Alchemy without patching or extending Advanced Alchemy.

The project intentionally does not replicate all of `fastapi-pagination`. Litestar and Advanced Alchemy already provide limit/offset pagination; this product fills the missing cursor-pagination capability.

## 2. Problem

Litestar exposes a basic `CursorPagination` container and abstract paginator classes, but it does not provide production-ready keyset query construction, opaque bidirectional bookmarks, total counting, or SQLAlchemy integration.

Advanced Alchemy provides mature repository and service support for limit/offset pagination, but no equivalent cursor/keyset workflow.

As a result, users must implement query paging, cursor serialization, backward navigation, counting, validation, response models, and framework integration themselves.

## 3. Goals

The MVP must:

1. Provide production-ready cursor/keyset pagination for SQLAlchemy 2 ORM entity selects.
2. Integrate through Litestar's native dependency injection, validation, DTO, serialization, and OpenAPI mechanisms.
3. Work with both synchronous and asynchronous SQLAlchemy sessions.
4. Work with sessions supplied by Advanced Alchemy without an additional plugin, mixin, or service base class.
5. Preserve the proven `fastapi-pagination` cursor response contract.
6. Keep cursor models and page construction independent of SQLAlchemy so additional storage adapters can be added later under `ext/`.
7. Follow the current code style, typing, testing, documentation, and contribution conventions of Litestar and Advanced Alchemy.

## 4. Non-goals

The MVP will not provide:

- classic page-number pagination;
- limit/offset pagination;
- an Advanced Alchemy plugin, repository mixin, or service mixin;
- automatic route patching or return-annotation inspection;
- automatic ordering or primary-key discovery;
- legacy SQLAlchemy `Query` support;
- raw SQL, `TextClause`, `FromStatement`, `CompoundSelect`, scalar selects, or multi-column row selects;
- item transformer callbacks;
- Pydantic- or msgspec-specific page models;
- inline/window-function total counting;
- signed or encrypted cursors;
- cursor links or HTTP `Link` headers;
- storage adapters other than SQLAlchemy.

These features require demonstrated demand before inclusion.

## 5. Target users

- Litestar applications using SQLAlchemy directly.
- Litestar applications using Advanced Alchemy for session lifecycle, repositories, services, DTOs, or serialization.
- Library authors who may later contribute cursor adapters for other storage systems.

## 6. Compatibility

| Component | Supported versions |
| --- | --- |
| Python | `>=3.12.0,<3.15.0` |
| Litestar | `>=2.24.0,<3.0` |
| SQLAlchemy | `>=2.0,<3.0` |
| Advanced Alchemy | `>=1.11.0,<2.0` |
| sqlakeyset | `>=2.0.1775222100,<3.0` |

Supported and tested database backends:

- SQLite, synchronous and asynchronous;
- PostgreSQL, synchronous and asynchronous.

Other SQLAlchemy dialects are unsupported until added to CI.

## 7. Distribution and installation

- PyPI distribution: `litestar-pagination`
- Python import package: `litestar_pagination`
- License: MIT

Installation groups:

```bash
pip install litestar-pagination
pip install 'litestar-pagination[sqlalchemy]'
pip install 'litestar-pagination[advanced-alchemy]'
```

The base package depends on Litestar. SQLAlchemy, `sqlakeyset`, database drivers, and Advanced Alchemy remain in the relevant optional or development dependency groups.

## 8. Public API

### 8.1 Core exports

```python
from litestar_pagination import CursorPage, CursorParams
```

Both types are standard-library dataclasses. The package must not require Pydantic or msgspec models for its public contract.

Conceptual parameter model:

```python
@dataclass
class CursorParams:
    cursor: Annotated[str | None, QueryParameter(name="cursor", required=False)] = None
    size: Annotated[int, QueryParameter(name="size", ge=1, le=100, required=False)] = 50
    include_total: ClassVar[bool] = True
```

The exact implementation may change to satisfy Litestar's documented typing conventions, but the resulting query and Python contracts must remain equivalent.

Conceptual response model:

```python
T = TypeVar("T")


@dataclass
class CursorPage(Generic[T]):
    items: Sequence[T]
    total: int | None
    current_page: str | None
    current_page_backwards: str | None
    previous_page: str | None
    next_page: str | None
```

`total` remains present in the serialized response. It is `null` when counting is disabled.

### 8.2 SQLAlchemy exports

```python
from litestar_pagination.ext.sqlalchemy import (
    SQLAlchemyAsyncCursorPaginator,
    SQLAlchemySyncCursorPaginator,
    apaginate,
    paginate,
)
```

The sync and async APIs are deliberately separate:

```python
page = paginate(session, statement, pagination)
page = await apaginate(async_session, statement, pagination)
```

Both functions accept:

- a compatible sync or async SQLAlchemy session;
- a SQLAlchemy 2 `Select` selecting exactly one mapped ORM entity;
- `CursorParams`;
- an optional caller-supplied `count_query`;
- a `unique` option defaulting to `True` where supported by `sqlakeyset`.

Both return `CursorPage[T]` with precise generic typing.

The package also provides `SQLAlchemyAsyncCursorPaginator[T]` and
`SQLAlchemySyncCursorPaginator[T]`. They implement Litestar's
`AbstractAsyncCursorPaginator[str, T]` and `AbstractSyncCursorPaginator[str, T]`, respectively,
and return the framework's forward-only `CursorPagination[str, T]`. This mode does not expose
backward bookmarks or totals; `CursorPage` remains the rich bidirectional contract.

## 9. Litestar integration

The package uses ordinary Litestar dependency injection. No application plugin is required.

```python
from litestar import Litestar, get
from litestar.di import NamedDependency, Provide
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from litestar_pagination import CursorPage, CursorParams
from litestar_pagination.ext.sqlalchemy import apaginate


@get("/users")
async def list_users(
    session: AsyncSession,
    pagination: NamedDependency[CursorParams],
) -> CursorPage[User]:
    statement = select(User).order_by(User.created_at, User.id)
    return await apaginate(session, statement, pagination)


app = Litestar(
    route_handlers=[list_users],
    dependencies={
        "pagination": Provide(CursorParams, sync_to_thread=False),
    },
)
```

The same dependency may be registered at application, router, controller, or handler scope using standard Litestar layering. Handlers use `NamedDependency[CursorParams]`, which is Litestar's non-deprecated named dependency annotation.

For a framework-native forward-only response, handlers may return the corresponding SQLAlchemy paginator:

```python
from litestar.pagination import CursorPagination


@get("/users")
async def list_users(
    session: AsyncSession,
    pagination: NamedDependency[CursorParams],
) -> CursorPagination[str, User]:
    paginator = SQLAlchemyAsyncCursorPaginator(
        session,
        select(User).order_by(User.created_at, User.id),
    )
    return await paginator(pagination.cursor, pagination.size)
```

The response must work with Litestar's generic-wrapper DTO handling. In particular, `SQLAlchemyDTO[User]` must transform the objects inside `CursorPage[User].items` without a package-specific transformer.

## 10. Advanced Alchemy integration

Advanced Alchemy remains responsible for engine and session lifecycle. The package consumes the injected session exactly as it would consume a directly configured SQLAlchemy session.

MVP integration is compatibility, documentation, and tests—not a new Advanced Alchemy plugin:

```python
@get("/users")
async def list_users(
    db_session: AsyncSession,
    pagination: NamedDependency[CursorParams],
) -> CursorPage[User]:
    return await apaginate(
        db_session,
        select(User).order_by(User.created_at, User.id),
        pagination,
    )
```

The documentation must include examples using:

- an Advanced Alchemy-provided session;
- `SQLAlchemyDTO` for response conversion;
- application- or controller-level `CursorParams` dependency registration.

## 11. Functional requirements

### 11.1 Query parameters

- Query parameter names are `cursor` and `size`.
- `cursor` is optional.
- `size` defaults to `50`.
- `size` must be at least `1` and at most `100`.
- Litestar must expose these constraints in OpenAPI and reject invalid values with its native HTTP 400 validation response.
- Total counting is controlled programmatically, not by a public query parameter.

Applications may customize parameter behavior by subclassing the dataclass and registering the subclass with Litestar DI. A no-total variant overrides `include_total` to `False`.

### 11.2 Ordering

- Every paginated statement must contain an explicit `ORDER BY`.
- The package must not infer or append a primary key.
- A statement without ordering raises a clear developer error equivalent to `ValueError("Cursor pagination requires ordering")`.
- Documentation must require a deterministic, unique tie-breaker, for example:

```python
select(User).order_by(User.created_at, User.id)
```

- Ascending, descending, mixed, and compound ordering supported by `sqlakeyset` must preserve their semantics.

### 11.3 Page navigation

- An absent cursor requests the first page.
- The same `cursor` query parameter is used for forward and backward bookmarks.
- `next_page` is set only when a next page exists.
- `previous_page` is set only when a previous page exists.
- `current_page` refetches the current page in forward order.
- `current_page_backwards` refetches the current page from its reverse bookmark.
- Empty result sets return an empty `items` sequence. `next_page` and `previous_page` are `None`; current-page bookmark behavior follows `sqlakeyset`.

### 11.4 Cursor encoding

- The internal bookmark is produced and consumed by `sqlakeyset`.
- The bookmark is Base64 encoded and URL escaped using the established `fastapi-pagination` behavior.
- The cursor is opaque by contract: clients must store and return it unchanged.
- Cursor contents and encoding are not a stable public schema.
- Malformed, undecodable, or incompatible cursors produce a Litestar HTTP 400 validation response.
- Cursors are not encrypted, signed, or confidential. This limitation must be documented.

### 11.5 Total counting

- Counting is enabled by default.
- `total` represents the full filtered result set, independent of the current cursor.
- The default count query removes ordering and counts over a subquery of the original filtered statement.
- Counting is executed separately from the keyset query.
- A caller may supply `count_query` for joins, distinct queries, performance tuning, or domain-specific counting.
- When `CursorParams.include_total` is false, no count query is executed and `CursorPage.total` is `None`.
- Inline/window-function counting is outside MVP scope.

### 11.6 ORM result behavior

- MVP accepts only `Select` statements selecting one mapped ORM entity.
- `items` contains entity instances, not SQLAlchemy `Row` wrappers.
- Result uniquification defaults to enabled.
- Count semantics follow the count query. Callers are responsible for a custom `count_query` when joins would otherwise count duplicate rows.

## 12. Response contract

Example response:

```json
{
  "items": [
    {"id": 42, "name": "Ada"}
  ],
  "total": 100,
  "current_page": "...",
  "current_page_backwards": "...",
  "previous_page": null,
  "next_page": "..."
}
```

The field names and meanings are stable public API. Cursor values themselves are opaque and unstable.

## 13. Architecture constraints

The minimum module boundary is:

```text
litestar_pagination/
  __init__.py
  cursor.py
  ext/
    __init__.py
    sqlalchemy.py
```

- `cursor.py` owns the storage-independent parameter/page contract and cursor codec.
- `ext/sqlalchemy.py` owns statement validation, counting, `sqlakeyset` interaction, and sync/async execution.
- Additional modules require a concrete responsibility; no plugin framework, adapter registry, flow engine, or abstract paginator hierarchy is required for MVP.
- A future storage integration should be addable under `ext/` while reusing `CursorParams`, `CursorPage`, and the cursor codec.
- Framework and dependency APIs must be public APIs documented by Litestar, Advanced Alchemy, SQLAlchemy, or `sqlakeyset` unless no public equivalent exists and the exception is isolated and tested.

## 14. Error behavior

| Condition | Required behavior |
| --- | --- |
| Invalid `size` | Litestar HTTP 400 validation response |
| Invalid Base64 cursor | Litestar HTTP 400 validation response |
| Invalid `sqlakeyset` bookmark | Litestar HTTP 400 validation response |
| Missing `ORDER BY` | Clear developer exception; not treated as client validation |
| Unsupported statement shape | Clear `TypeError` or package-specific developer exception |
| Database execution failure | Preserve the underlying SQLAlchemy exception |

The package must not swallow database exceptions or convert server/query configuration errors into HTTP 400 responses.

## 15. Quality requirements

The repository must follow Litestar and Advanced Alchemy conventions where applicable:

- `pyproject.toml`-based packaging;
- complete type annotations and a `py.typed` marker;
- Ruff formatting and linting;
- ty static type checks;
- pytest tests with sync and async coverage;
- coverage reporting with all core branches exercised;
- pre-commit configuration matching CI checks;
- Sphinx-compatible docstrings and public documentation;
- no undocumented public exports;
- no warnings during test collection or execution;
- changelog and semantic release notes for public API changes.

Implementation must prefer public framework APIs, native dataclasses, Litestar DI, and installed dependency capabilities over custom infrastructure.

## 16. Test requirements

### 16.1 Unit tests

- default and boundary `size` validation;
- cursor encode/decode round-trip;
- malformed Base64;
- no-total page behavior;
- response dataclass serialization;
- missing ordering;
- unsupported statement forms;
- default count-query construction;
- custom count-query selection.

### 16.2 SQLAlchemy integration tests

Run against SQLite and PostgreSQL, sync and async:

- first, middle, and final pages;
- forward navigation through all records without duplicates or omissions;
- backward navigation to the first page;
- current-page refetch bookmarks;
- empty result set;
- page size smaller than, equal to, and greater than the result count;
- ascending and descending ordering;
- compound ordering with a unique primary-key tie-breaker;
- duplicate leading sort values;
- filtered queries;
- total enabled and disabled;
- custom count query;
- entity uniquification;
- malformed and stale/incompatible cursor handling.

### 16.3 Litestar integration tests

- `Provide(CursorParams, sync_to_thread=False)` resolves query parameters;
- OpenAPI describes `cursor`, `size`, constraints, and `CursorPage[Model]` fields;
- invalid query parameters and cursors return HTTP 400;
- dataclass response serialization matches the contract;
- `SQLAlchemyDTO` transforms entities inside `items`;
- dependencies work at application and controller/handler scope.

### 16.4 Advanced Alchemy integration tests

- sync and async sessions supplied by Advanced Alchemy work unchanged;
- no additional plugin or service subclass is required;
- `SQLAlchemyDTO` and Advanced Alchemy model bases work with `CursorPage`.

## 17. Documentation requirements

MVP documentation must include:

1. Installation for base, SQLAlchemy, and Advanced Alchemy extras.
2. A five-minute Litestar + SQLAlchemy quickstart.
3. An Advanced Alchemy session and `SQLAlchemyDTO` example.
4. Forward and backward navigation examples.
5. Deterministic ordering and unique tie-breaker guidance.
6. Total-count behavior and custom `count_query` examples.
7. Disabling total through a custom `CursorParams` subclass.
8. Cursor opacity, lack of signing/encryption, and HTTP 400 behavior.
9. Supported versions and database backends.
10. Explicit MVP limitations.

## 18. MVP acceptance criteria

The MVP is complete when:

- the public API shown in this document works for sync and async SQLAlchemy sessions;
- a Litestar application can register `CursorParams` directly through `Provide`;
- a user can navigate a deterministically ordered dataset forward and backward using opaque cursors without duplicates or omissions;
- totals are correct, overridable, and suppressible without changing the response schema;
- SQLite and PostgreSQL sync/async test matrices pass;
- Litestar OpenAPI, validation, serialization, and `SQLAlchemyDTO` integration tests pass;
- Advanced Alchemy-provided sessions pass without an additional plugin;
- linting, formatting, typing, tests, and documentation builds pass in CI;
- the package can be built and installed from its wheel with the declared extras;
- no non-goal feature is required to complete the documented quickstart.

## 19. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Non-unique ordering causes duplicates or omissions | Require explicit ordering and document a unique tie-breaker |
| Join-heavy queries produce incorrect totals | Support caller-supplied `count_query` and document row-count semantics |
| Cursor leaks ordered values | Document that Base64 is not encryption and add signing only on demonstrated demand |
| `sqlakeyset` bookmark behavior changes | Pin `<3.0`, isolate codec/query interaction, and test round-trips |
| Litestar DTO does not recognize the custom generic wrapper | Make `SQLAlchemyDTO` wrapper behavior an MVP integration test |
| Database dialect differences | Guarantee only SQLite and PostgreSQL until additional CI exists |
| Scope grows into a full `fastapi-pagination` port | Keep classic/offset, transformers, customization engine, and plugin system explicit non-goals |

## 20. Delivery phases

### Phase 1: Core contract

- Package metadata and dependency extras.
- `CursorParams`, `CursorPage`, cursor codec, validation, and unit tests.
- Litestar DI, serialization, and OpenAPI proof.

### Phase 2: SQLAlchemy adapter

- Sync `paginate` and async `apaginate`.
- Statement validation, count query, `sqlakeyset` navigation, and entity unwrapping.
- SQLite and PostgreSQL integration tests.

### Phase 3: Ecosystem validation and release

- Advanced Alchemy session and `SQLAlchemyDTO` tests.
- User documentation, security notes, and examples.
- Wheel/sdist verification and PyPI `0.1.0` release readiness.

## 21. Future considerations

The following are candidates only after MVP usage demonstrates need:

- signed cursor codecs;
- scalar and multi-column selects with an explicit result-shape contract;
- `CompoundSelect` support;
- additional database dialect guarantees;
- additional storage adapters;
- optional response headers or links;
- per-request item transformation;
- Litestar 3 compatibility after its stable release;
- Advanced Alchemy repository/service convenience APIs if standalone session calls prove insufficient.

## 22. References

- [Litestar pagination API](https://docs.litestar.dev/2/reference/pagination.html)
- [Litestar DTO pagination support](https://docs.litestar.dev/2/usage/dto/1-abstract-dto.html#working-with-litestar-s-pagination-types)
- [Advanced Alchemy Litestar integration](https://docs.advanced-alchemy.litestar.dev/latest/usage/frameworks/litestar.html)
- [Advanced Alchemy repositories and pagination](https://docs.advanced-alchemy.litestar.dev/latest/usage/repositories.html#pagination)
- [fastapi-pagination source](https://github.com/uriyyo/fastapi-pagination)
- [sqlakeyset](https://github.com/djrobstep/sqlakeyset)
