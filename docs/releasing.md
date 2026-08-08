# Releasing

Releases are built only from a prepared, clean commit on the default branch. The repository never
bumps versions or rewrites the changelog inside a privileged workflow.

## Repository configuration

Configure these GitHub environments before the first release:

- `release-operations`: restrict deployment to the default branch and require a maintainer review;
- `pypi`: require a maintainer review and configure the matching PyPI Trusted Publisher for
  `.github/workflows/3_release.yml`;
- `github-pages`: use the protected Pages environment created by GitHub.

Protect the default branch and require `Tests / Required checks`, `CodeQL analysis`, and dependency
review where the event supports it. Allow GitHub Actions to create attestations and deploy Pages.

## Prepare a release

1. Set the same stable semantic version in `pyproject.toml` and
   `litestar_pagination/__init__.py`.
2. Finalize the first `CHANGELOG.md` entry with that version and UTC date. Do not leave an
   `Unreleased` heading in the release commit.
3. Run the full local verification gate, build artifacts, and inspect their manifests.
4. Merge the prepared commit to the default branch.
5. Run `Tag prepared release` against the default branch and approve `release-operations`.

The workflow creates an immutable tag and a draft GitHub release, then dispatches Tests for that
tag. Only the exact successful Tests run can start the release workflow. The release workflow
builds twice, compares hashes, smoke-tests the wheel, emits a CycloneDX SBOM, creates GitHub build
attestations, uploads through PyPI Trusted Publishing, deploys documentation, and finally publishes
the draft GitHub release.

Published files are immutable. If a release is faulty, yank it on PyPI, document the reason, and
publish a corrected version. Do not delete tags or rewrite the default branch.
