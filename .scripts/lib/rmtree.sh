#!/bin/sh
# Recursively delete a directory.
# Usage: rmtree.sh <absolute-dir-path>
set -e

DIR="$1"

if [ ! -d "$DIR" ]; then
    exit 0
fi

rm -rf "$DIR"
