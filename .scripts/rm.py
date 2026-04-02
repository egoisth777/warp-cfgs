"""Remove a sub-repo."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".scripts"))
LIB = ROOT / ".scripts" / "lib"

from lib.repos import load_repos, save_repos


def _rmtree_cmd() -> list[str]:
    if sys.platform == "win32":
        return ["pwsh", "-NoProfile", "-File", str(LIB / "rmtree.ps1")]
    return [str(LIB / "rmtree.sh")]


def main(path: str, root: Path = ROOT) -> None:
    repos_file = root / "REPOS.json"
    repos = load_repos(repos_file)

    found = False
    remaining = []
    for entry in repos:
        if entry["path"] == path:
            found = True
        else:
            remaining.append(entry)

    if not found:
        print(f"Error: '{path}' not found in REPOS.json", file=sys.stderr)
        sys.exit(1)

    save_repos(remaining, repos_file)
    print(f"Removed '{path}' from REPOS.json")

    target = root / path
    if target.exists():
        subprocess.run(_rmtree_cmd() + [str(target)], check=True)
        print(f"Deleted {path}")

    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python rm.py <path>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
