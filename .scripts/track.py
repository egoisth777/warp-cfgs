"""Scan root for on-disk repos not yet in REPOS.json and register them."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".scripts"))

from lib.repos import load_repos, save_repos

SKIP_DIRS = {".scripts", ".git", ".github", "docs"}


def find_untracked(root: Path, repos: list[dict]) -> list[dict]:
    tracked = {e["path"] for e in repos}
    found = []

    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name in SKIP_DIRS:
            continue
        if child.name.startswith("."):
            continue
        if not (child / ".git").exists():
            continue
        if child.name in tracked:
            continue

        result = subprocess.run(
            ["git", "-C", str(child), "remote", "get-url", "origin"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  skip: {child.name} — no 'origin' remote")
            continue

        url = result.stdout.strip()
        found.append({"url": url, "path": child.name})

    return found


def main(root: Path = ROOT) -> None:
    repos_file = root / "REPOS.json"
    repos = load_repos(repos_file)

    print("Scanning for untracked repos...")
    new_entries = find_untracked(root, repos)

    if not new_entries:
        print("No untracked repos found.")
        return

    for entry in new_entries:
        print(f"  found: {entry['path']} ({entry['url']})")

    repos.extend(new_entries)
    save_repos(repos, repos_file)
    print(f"Added {len(new_entries)} repo(s) to REPOS.json.")

    print("Done.")


if __name__ == "__main__":
    main()
