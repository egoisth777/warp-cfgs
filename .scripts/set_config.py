"""Set up Warp terminal theme configuration (create symlinks)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / ".scripts" / "lib"


def _set_config_cmd() -> list[str]:
    if sys.platform == "win32":
        return ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(LIB / "set_config.ps1")]
    return [str(LIB / "set_config.sh")]


def main() -> None:
    print("Setting up Warp theme configuration...")
    subprocess.run(_set_config_cmd(), check=True)
    print("Done.")


if __name__ == "__main__":
    main()
