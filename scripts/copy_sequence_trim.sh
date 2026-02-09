#!/usr/bin/env bash

set -euo pipefail

SRC_DEFAULT="$HOME/.tmp/external-context/blender-vse/sequence-trim.md"
SRC="${1:-$SRC_DEFAULT}"

if [ ! -f "$SRC" ]; then
    echo "Source file not found: $SRC" >&2
    echo "Pass the cached ExternalScout file path as the first argument." >&2
    exit 1
fi

DEST_DIR="$HOME/.config/opencode/context/project/blender-subtitle-editor/reference"
DEST_FILE="$DEST_DIR/sequence-trim.md"

mkdir -p "$DEST_DIR"
cp "$SRC" "$DEST_FILE"

cat <<'MSG'
Copied sequence-trim.md into the permanent context.

Next steps (manual):
  1. Edit the file to add required frontmatter + MVI structure.
  2. Update ~/.config/opencode/context/project/blender-subtitle-editor/navigation.md
     to reference reference/sequence-trim.md with an appropriate priority.
MSG
