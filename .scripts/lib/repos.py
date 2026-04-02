"""REPOS.json read/write."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_REPOS_FILE = ROOT / "REPOS.json"


def load_repos(repos_file: Path = DEFAULT_REPOS_FILE) -> list[dict]:
    if not repos_file.exists():
        return []
    return json.loads(repos_file.read_text())


def save_repos(entries: list[dict], repos_file: Path = DEFAULT_REPOS_FILE) -> None:
    repos_file.write_text(json.dumps(entries, indent=2) + "\n")
