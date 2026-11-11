"""Set the package version everywhere it is recorded.

Usage: python scripts/bump_version.py X.Y.Z[-(alpha|beta|rc).N]

Updates pyproject.toml, headless/__init__.py and the client's
package.json and package-lock.json, and dates the
"## X.Y.Z (unreleased)" heading in CHANGELOG.md (which must exist).

All files change or none does: every replacement is made in memory first,
and the files are only written when each of them matched.
"""

import datetime
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(-(alpha|beta|rc)\.\d+)?$")


def replace(texts, path, pattern, repl):
    """Replace the single match of a pattern in the text of a file, in memory."""
    if path not in texts:
        texts[path] = (ROOT / path).read_text()
    texts[path], n = re.subn(pattern, repl, texts[path], flags=re.MULTILINE)
    if n != 1:
        sys.exit(f"Expected 1 match for {pattern!r} in {path}, found {n}. No file was changed.")


def write(texts):
    """
    Write the files. Each one is written next to its target and then moved
    over it, so a failure halfway leaves every file either old or new.
    """
    temporary = []
    try:
        for path, text in texts.items():
            file = ROOT / path
            copy = file.with_name(f"{file.name}.bump")
            copy.write_text(text)
            temporary.append((copy, file))
    except OSError:
        for copy, _ in temporary:
            copy.unlink(missing_ok=True)
        raise

    for copy, file in temporary:
        os.replace(copy, file)


def main(version):
    if not VERSION_RE.match(version):
        sys.exit(f"Invalid version {version!r}: expected X.Y.Z or X.Y.Z-rc.N")

    texts = {}
    today = datetime.date.today().isoformat()
    replace(
        texts,
        "CHANGELOG.md",
        rf"^## {re.escape(version)} \(unreleased\)$",
        f"## {version} ({today})",
    )
    replace(texts, "pyproject.toml", r'^version = ".*"$', f'version = "{version}"')
    replace(
        texts,
        "headless/__init__.py",
        r'^__version__ = ".*"$',
        f'__version__ = "{version}"',
    )
    # The package's own version: the "version" key of package.json, and the
    # top-level one and the root package's in package-lock.json.
    replace(
        texts,
        "client/package.json",
        r'^  "version": ".*",$',
        f'  "version": "{version}",',
    )
    replace(
        texts,
        "client/package-lock.json",
        r'^  "version": ".*",$',
        f'  "version": "{version}",',
    )
    replace(
        texts,
        "client/package-lock.json",
        r'^(    "": \{\n      "name": "@django-headless/client",\n      "version": )".*",$',
        rf'\g<1>"{version}",',
    )

    write(texts)
    print(f"Version set to {version}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
