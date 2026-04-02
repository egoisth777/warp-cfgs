"""Initialize warp-cfgs on a fresh machine."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".scripts"))

from lib.repos import load_repos


def main(root: Path = ROOT) -> None:
    repos = load_repos(root / "REPOS.json")

    for entry in repos:
        target = root / entry["path"]
        if target.exists():
            print(f"  skip (exists): {entry['path']}")
            continue
        print(f"  cloning {entry['url']} -> {entry['path']}")
        subprocess.run(
            ["git", "clone", entry["url"], str(target)],
            check=True,
        )

    # Set up pre-commit hook
    subprocess.run(
        ["git", "config", "core.hooksPath", ".scripts/hooks"],
        cwd=str(root),
        check=True,
    )
    print("Configured pre-commit hook.")

    print("Done.")


if __name__ == "__main__":
    main()
