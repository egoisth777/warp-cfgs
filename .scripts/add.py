"""Register and clone a new sub-repo."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".scripts"))

from lib.repos import load_repos, save_repos


def main(url: str, path: str, root: Path = ROOT) -> None:
    repos_file = root / "REPOS.json"
    repos = load_repos(repos_file)

    for entry in repos:
        if entry["path"] == path:
            print(f"Error: '{path}' already exists in REPOS.json", file=sys.stderr)
            sys.exit(1)

    entry = {"url": url, "path": path}
    repos.append(entry)
    save_repos(repos, repos_file)
    print(f"Added '{path}' to REPOS.json")

    target = root / path
    print(f"Cloning {url} -> {path}")
    subprocess.run(["git", "clone", url, str(target)], check=True)

    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python add.py <url> <path>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
