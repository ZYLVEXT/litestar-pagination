"""Inventory and validate GitHub-hosted ``uses:`` entries under ``.github``."""  # noqa: INP001

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

FULL_SHA_PATTERN = re.compile(r"[0-9a-fA-F]{40}\Z")
USES_PATTERN = re.compile(
    r"^\s*(?:-\s*)?uses:\s*"
    r"(?P<slug>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[^\s@#]+)?)"
    r"@(?P<ref>[^\s#]+)"
    r"(?:\s*#\s*(?P<comment>.*?))?\s*$",
)
YAML_SUFFIXES = frozenset({".yml", ".yaml"})
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_GITHUB_DIR = DEFAULT_REPO_ROOT / ".github"


@dataclass(frozen=True, slots=True)
class WorkflowUse:
    """A GitHub-hosted ``uses:`` entry from a workflow-related YAML file."""

    file: str
    line: int
    slug: str
    ref: str
    comment: str | None


@dataclass(frozen=True, slots=True)
class PinnedAction:
    """A remote GitHub Action or reusable workflow pinned to a commit SHA."""

    file: str
    line: int
    repository: str
    subpath: str | None
    uses_target: str
    sha: str
    comment: str | None


@dataclass(frozen=True, slots=True)
class UnpinnedAction:
    """A remote GitHub Action or reusable workflow not pinned to a full SHA."""

    file: str
    line: int
    uses_target: str
    ref: str
    comment: str | None


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        The configured parser.
    """
    parser = argparse.ArgumentParser(
        description="List or validate remote GitHub-hosted uses: entries under .github.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Repository root used to relativize file paths.",
    )
    parser.add_argument(
        "--github-dir",
        type=Path,
        default=DEFAULT_GITHUB_DIR,
        help="Directory to scan for workflow YAML files.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit nonzero when a remote GitHub-hosted uses: entry is not pinned to a full SHA.",
    )
    return parser


def iter_yaml_files(github_dir: Path) -> list[Path]:
    """Return YAML files under a validated GitHub directory.

    Returns:
        Workflow-related YAML files in deterministic order.
    """
    return sorted(path for path in github_dir.rglob("*") if path.is_file() and path.suffix in YAML_SUFFIXES)


def display_path(path: Path, *, repo_root: Path) -> str:
    """Return a repo-relative display path when possible.

    Returns:
        A display path.
    """
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def parse_workflow_use(line: str, *, file: Path, line_number: int, repo_root: Path) -> WorkflowUse | None:
    """Parse one remote GitHub-hosted ``uses:`` line.

    Returns:
        The parsed entry, or ``None`` for local, Docker, and unrelated lines.
    """
    match = USES_PATTERN.match(line)
    if match is None:
        return None

    comment = match.group("comment")
    return WorkflowUse(
        file=display_path(file, repo_root=repo_root),
        line=line_number,
        slug=match.group("slug"),
        ref=match.group("ref"),
        comment=(comment.strip() or None) if comment is not None else None,
    )


def parse_pinned_action(line: str, *, file: Path, line_number: int, repo_root: Path) -> PinnedAction | None:
    """Parse one fully pinned remote GitHub-hosted ``uses:`` line.

    Returns:
        The parsed pinned entry, or ``None`` when the line is not a full-SHA pin.
    """
    workflow_use = parse_workflow_use(line, file=file, line_number=line_number, repo_root=repo_root)
    if workflow_use is None or FULL_SHA_PATTERN.fullmatch(workflow_use.ref) is None:
        return None

    owner, repository_name, *subpath_parts = workflow_use.slug.split("/")
    return PinnedAction(
        file=workflow_use.file,
        line=workflow_use.line,
        repository=f"{owner}/{repository_name}",
        subpath="/".join(subpath_parts) or None,
        uses_target=workflow_use.slug,
        sha=workflow_use.ref.lower(),
        comment=workflow_use.comment,
    )


def collect_pinned_actions(*, repo_root: Path, github_dir: Path) -> list[PinnedAction]:
    """Collect full-SHA pins from workflow-related YAML files.

    Returns:
        Parsed full-SHA pins.
    """
    pinned_actions: list[PinnedAction] = []
    for workflow_file in iter_yaml_files(github_dir):
        for line_number, line in enumerate(workflow_file.read_text(encoding="utf-8").splitlines(), start=1):
            if pinned_action := parse_pinned_action(
                line,
                file=workflow_file,
                line_number=line_number,
                repo_root=repo_root,
            ):
                pinned_actions.append(pinned_action)
    return pinned_actions


def collect_unpinned_actions(*, repo_root: Path, github_dir: Path) -> list[UnpinnedAction]:
    """Collect remote GitHub-hosted entries that are not full-SHA pins.

    Returns:
        Parsed mutable references.
    """
    unpinned_actions: list[UnpinnedAction] = []
    for workflow_file in iter_yaml_files(github_dir):
        for line_number, line in enumerate(workflow_file.read_text(encoding="utf-8").splitlines(), start=1):
            workflow_use = parse_workflow_use(line, file=workflow_file, line_number=line_number, repo_root=repo_root)
            if workflow_use is not None and FULL_SHA_PATTERN.fullmatch(workflow_use.ref) is None:
                unpinned_actions.append(
                    UnpinnedAction(
                        file=workflow_use.file,
                        line=workflow_use.line,
                        uses_target=workflow_use.slug,
                        ref=workflow_use.ref,
                        comment=workflow_use.comment,
                    ),
                )
    return unpinned_actions


def render_text(items: list[PinnedAction] | list[UnpinnedAction]) -> str:
    """Render action items in a concise, human-readable form.

    Returns:
        Rendered lines, or an empty string for an empty list.
    """
    if not items:
        return ""

    if isinstance(items[0], PinnedAction):
        lines = ["file:line | target | sha | comment"]
        lines.extend(
            f"{item.file}:{item.line} | {item.uses_target} | {item.sha} | {item.comment or '-'}" for item in items
        )
    else:
        lines = ["file:line | target | mutable ref | comment"]
        lines.extend(
            f"{item.file}:{item.line} | {item.uses_target} | {item.ref} | {item.comment or '-'}" for item in items
        )
    return "\n".join(lines)


def write_items(items: list[PinnedAction] | list[UnpinnedAction], *, output_format: str) -> None:
    """Write action items in the selected format."""
    if output_format == "json":
        json.dump([asdict(item) for item in items], sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    text_output = render_text(items)
    if text_output:
        sys.stdout.write(text_output)
        sys.stdout.write("\n")


def main() -> int:
    """Run the inventory or validation command.

    Returns:
        A process exit code.
    """
    parser = build_parser()
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    github_dir = args.github_dir.resolve()
    if not github_dir.is_dir():
        sys.stderr.write(f"[ERROR] GitHub directory does not exist or is not a directory: {github_dir}\n")
        return 2

    if args.check:
        unpinned_actions = collect_unpinned_actions(repo_root=repo_root, github_dir=github_dir)
        write_items(unpinned_actions, output_format=args.format)
        return int(bool(unpinned_actions))

    pinned_actions = collect_pinned_actions(repo_root=repo_root, github_dir=github_dir)
    write_items(pinned_actions, output_format=args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
