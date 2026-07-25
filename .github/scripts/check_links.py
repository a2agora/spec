#!/usr/bin/env python3
"""Verify every internal Markdown link in the spec resolves.

Checks two things a reader would otherwise discover as a 404:

1. Relative links to other Markdown files point at a file that exists.
2. Links carrying an ``#anchor`` point at a heading that exists in the
   target file, using GitHub's heading-slug rules.

External (``http(s)://``, ``mailto:``) links are deliberately not fetched:
network checks make CI flaky and fail for reasons unrelated to the change
under review.

Exit code 0 when everything resolves, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories that hold generated output or vendored copies, not spec source.
SKIP_DIRS = {".git", "_site", ".jekyll-cache", "vendor", ".pytest_cache", "node_modules"}

# [link text](target) — link text may wrap across lines, the target may not.
# The negated class already spans newlines, so wrapped link text is covered.
LINK_RE = re.compile(r"\[[^\[\]]*?\]\(\s*([^)\s]+?)\s*\)")

# Lines opening or closing a fenced code block.
FENCE_RE = re.compile(r"^\s*(```|~~~)")

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")


def outside_fences(text: str) -> str:
    """The document with fenced code blocks removed.

    Both headings and links are only real outside a fence: a spec that
    documents Markdown syntax in a ```markdown block would otherwise have its
    example links checked as if they were live, failing CI on correct prose.
    """
    kept: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(line)
    return "\n".join(kept)


def slugify(heading: str) -> str:
    """Reproduce GitHub's heading-anchor slug.

    Lowercase, drop everything that is not alphanumeric / space / hyphen /
    underscore (which removes Markdown emphasis, backticks and punctuation),
    then turn spaces into hyphens.

    Each space becomes its own hyphen — runs are *not* collapsed, matching
    github-slugger. A heading like ``3.2 Heartbeat / liveness`` therefore
    anchors as ``32-heartbeat--liveness``: dropping the slash leaves two
    adjacent spaces, hence two hyphens.
    """
    text = heading.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def headings_of(path: Path) -> set[str]:
    """All anchor slugs a file offers."""
    body = outside_fences(path.read_text(encoding="utf-8"))
    return {
        slugify(match.group(2))
        for match in (HEADING_RE.match(line) for line in body.splitlines())
        if match
    }


def markdown_files() -> list[Path]:
    return sorted(
        p
        for p in REPO_ROOT.rglob("*.md")
        if not SKIP_DIRS.intersection(p.relative_to(REPO_ROOT).parts)
    )


def main() -> int:
    files = markdown_files()
    heading_cache: dict[Path, set[str]] = {}
    failures: list[str] = []

    for source in files:
        rel_source = source.relative_to(REPO_ROOT)
        body = outside_fences(source.read_text(encoding="utf-8"))
        for target in LINK_RE.findall(body):
            if target.startswith(("http://", "https://", "mailto:", "tel:")):
                continue

            path_part, _, anchor = target.partition("#")

            if path_part:
                resolved = (source.parent / path_part).resolve()
                if not resolved.exists():
                    failures.append(f"{rel_source}: missing target -> {target}")
                    continue
            else:
                # Pure "#anchor" link: same document.
                resolved = source

            if not anchor or resolved.suffix != ".md":
                continue

            if resolved not in heading_cache:
                heading_cache[resolved] = headings_of(resolved)
            if anchor not in heading_cache[resolved]:
                failures.append(f"{rel_source}: missing anchor -> {target}")

    if failures:
        print(f"Broken internal links ({len(failures)}):\n", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print(f"All internal links resolve ({len(files)} Markdown files checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
