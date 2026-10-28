"""Set the package version everywhere it is recorded.

Usage: python scripts/bump_version.py X.Y.Z[-(alpha|beta|rc).N]

Updates pyproject.toml, headless/__init__.py and the client's
package.json and package-lock.json, and dates the
"## X.Y.Z (unreleased)" heading in CHANGELOG.md (which must exist).
"""

import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(-(alpha|beta|rc)\.\d+)?$")


def replace(path, pattern, repl, count=1):
    file = ROOT / path
    text = file.read_text()
    new, n = re.subn(pattern, repl, text, count=count, flags=re.MULTILINE)
    if n != count:
        sys.exit(f"Expected {count} match(es) for {pattern!r} in {path}, found {n}")
    file.write_text(new)


def main(version):
    if not VERSION_RE.match(version):
        sys.exit(f"Invalid version {version!r}: expected X.Y.Z or X.Y.Z-rc.N")

    # The changelog first: a missing heading fails before any file changes.
    today = datetime.date.today().isoformat()
    replace(
        "CHANGELOG.md",
        rf"^## {re.escape(version)} \(unreleased\)$",
        f"## {version} ({today})",
    )
    replace("pyproject.toml", r'^version = ".*"$', f'version = "{version}"')
    replace(
        "headless/__init__.py",
        r'^__version__ = ".*"$',
        f'__version__ = "{version}"',
    )
    # The package's own version: the first "version" key in package.json,
    # the top-level one and the root package's in package-lock.json.
    replace(
        "client/package.json",
        r'^  "version": ".*",$',
        f'  "version": "{version}",',
    )
    replace(
        "client/package-lock.json",
        r'^  "version": ".*",$',
        f'  "version": "{version}",',
    )
    replace(
        "client/package-lock.json",
        r'^(    "": \{\n      "name": "@django-headless/client",\n      "version": )".*",$',
        rf'\g<1>"{version}",',
    )
    print(f"Version set to {version}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
