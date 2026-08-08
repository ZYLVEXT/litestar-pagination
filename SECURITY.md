# Security policy

## Supported versions

Security fixes are provided for the latest released version of `litestar-pagination`.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private security advisory
flow for `ZYLVEXT/litestar-pagination` and include a minimal reproduction, affected versions, and
the expected impact. Maintainers will acknowledge a complete report and coordinate disclosure.

## Security boundary

Cursor values are untrusted HTTP input. The package validates and decodes them before passing
bookmarks to `sqlakeyset`; SQL is built only through SQLAlchemy expressions. Cursor encoding is not
encryption or signing, and applications must not place secrets in cursor ordering values.
