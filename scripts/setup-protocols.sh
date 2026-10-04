#!/bin/sh
# Download optional external skills into a gitignored directory.
#
# Run from anywhere:
#
#     ./scripts/setup-protocols.sh
#
# The coordinator can resolve installed protocols from the catalogs this writes.
# Nothing here is imported by the coordinator, and the published skills stay
# usable when these downloads are absent. Running the script again updates the
# same checkouts.

set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
DEST="$ROOT/.external"

MATT_URL="https://github.com/mattpocock/skills.git"
MATT_DIR="$DEST/mattpocock-skills"
MATT_CATALOG="$MATT_DIR/skills"

PLUGINS_URL="https://github.com/cursor/plugins.git"
PLUGINS_DIR="$DEST/cursor-plugins"
# SKILL.md files live at pstack/skills in cursor/plugins.
PSTACK_SPARSE="pstack/skills"
PSTACK_CATALOG="$PLUGINS_DIR/pstack/skills"

CATALOG_ENV="$DEST/catalog.env"

run() {
  printf '+ %s\n' "$*"
  "$@"
}

abs_dir() {
  (CDPATH= cd -- "$1" && pwd -P)
}

ensure_clone() {
  url=$1
  dest=$2
  sparse=$3

  if [ -d "$dest/.git" ]; then
    run git -C "$dest" fetch --depth 1 origin
    if [ -n "$sparse" ]; then
      run git -C "$dest" sparse-checkout set "$sparse"
    fi
    run git -C "$dest" reset --hard FETCH_HEAD
    return
  fi

  if [ -e "$dest" ]; then
    rm -rf "$dest"
  fi
  mkdir -p "$(dirname "$dest")"
  if [ -n "$sparse" ]; then
    run git clone --depth 1 --filter=blob:none --sparse "$url" "$dest"
    run git -C "$dest" sparse-checkout set "$sparse"
  else
    run git clone --depth 1 "$url" "$dest"
  fi
}

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi

ensure_clone "$PLUGINS_URL" "$PLUGINS_DIR" "$PSTACK_SPARSE"
ensure_clone "$MATT_URL" "$MATT_DIR" ""

missing=0
for path in "$PSTACK_CATALOG" "$MATT_CATALOG"; do
  if [ ! -d "$path" ]; then
    if [ "$missing" -eq 0 ]; then
      echo "expected catalog directory was not created:" >&2
    fi
    echo "  $path" >&2
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  exit 1
fi

# pstack first: its skill names are the protocols the coordinator looks up.
pstack_abs=$(abs_dir "$PSTACK_CATALOG")
matt_abs=$(abs_dir "$MATT_CATALOG")
value="$pstack_abs:$matt_abs"
mkdir -p "$DEST"
printf 'export COORDINATOR_PROTOCOL_CATALOG=%s\n' "$value" > "$CATALOG_ENV"

printf '\n'
echo "Downloaded skills are in:"
echo "  $pstack_abs"
echo "  $matt_abs"
echo "Catalog list written to $(abs_dir "$(dirname "$CATALOG_ENV")")/$(basename "$CATALOG_ENV")"
echo "COORDINATOR_PROTOCOL_CATALOG=$value"
