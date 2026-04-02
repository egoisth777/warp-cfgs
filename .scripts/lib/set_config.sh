#!/bin/sh
# Create symlink from warp-themes sub-repo to Warp's theme data directory.
# Usage: set_config.sh (no args — paths are relative to script location)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
THEMES_SOURCE="$(cd "$SCRIPT_DIR/../.." && pwd)/warp-themes"

# Detect Warp config path per platform
case "$(uname -s)" in
    Darwin)
        WARP_TARGET="$HOME/.warp/themes"
        ;;
    Linux)
        WARP_TARGET="${XDG_CONFIG_HOME:-$HOME/.config}/warp/themes"
        ;;
    *)
        echo "ERROR: unsupported platform: $(uname -s)"
        exit 1
        ;;
esac

if [ ! -d "$THEMES_SOURCE" ]; then
    echo "ERROR: warp-themes not found at $THEMES_SOURCE — run init.py first"
    exit 1
fi

if [ -e "$WARP_TARGET" ] || [ -L "$WARP_TARGET" ]; then
    echo "SKIP: $WARP_TARGET already exists"
    exit 0
fi

# Ensure parent directory exists
mkdir -p "$(dirname "$WARP_TARGET")"

ln -s "$THEMES_SOURCE" "$WARP_TARGET"
echo "Created symlink: $WARP_TARGET -> $THEMES_SOURCE"
