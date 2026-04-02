"""Sync repos: commit+push local changes, pull remote, clone missing.

For each sub-repo, uses a hybrid strategy:
  - If the sub-repo has .scripts/sync.py, run it (delegate to sub-repo).
  - Otherwise, run fixed commands: git add -A, commit, push, pull.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".scripts"))

from lib.repos import load_repos


def sync_repo(target: Path) -> None:
    sub_sync = target / ".scripts" / "sync.py"
    if sub_sync.exists():
        print(f"    running {target.name}/.scripts/sync.py")
        subprocess.run([sys.executable, str(sub_sync)], cwd=str(target), check=True)
    else:
        subprocess.run(["git", "-C", str(target), "add", "-A"], check=True)
        result = subprocess.run(
            ["git", "-C", str(target), "diff", "--cached", "--quiet"]
        )
        if result.returncode != 0:
            print(f"    committing local changes")
            subprocess.run(
                ["git", "-C", str(target), "commit", "-m", "auto-sync"],
                check=True,
            )
        print(f"    pushing")
        subprocess.run(["git", "-C", str(target), "push"], check=True)
        print(f"    pulling")
        subprocess.run(["git", "-C", str(target), "pull"], check=True)


def main(root: Path = ROOT) -> None:
    repos = load_repos(root / "REPOS.json")

    for entry in repos:
        target = root / entry["path"]
        try:
            if target.exists():
                print(f"  syncing {entry['path']}")
                sync_repo(target)
            else:
                print(f"  cloning {entry['url']} -> {entry['path']}")
                subprocess.run(
                    ["git", "clone", entry["url"], str(target)],
                    check=True,
                )
        except (subprocess.CalledProcessError, OSError) as e:
            print(f"  ERROR syncing {entry['path']}: {e}")
            continue

    print("Done.")


if __name__ == "__main__":
    main()
