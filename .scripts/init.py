"""Initialize warp-cfgs on a fresh machine."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / ".scripts" / "lib"
sys.path.insert(0, str(ROOT / ".scripts"))

from lib.repos import load_repos


def _init_cmd() -> list[str]:
    if sys.platform == "win32":
        return ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(LIB / "init.ps1")]
    return [str(LIB / "init.sh")]


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

    # Set up Warp theme symlink
    print("Setting up Warp theme configuration...")
    subprocess.run(_init_cmd(), check=True)

    print("Done.")


if __name__ == "__main__":
    main()
