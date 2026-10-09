#!/usr/bin/env bash
# Symlink marketplace-agents Cursor skills into ~/.cursor/skills or .cursor/skills.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_SRC="${REPO_ROOT}/skills"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--project] [--uninstall] [--force]

  (default)     Symlink each skill under skills/ into ~/.cursor/skills/
  --project     Symlink into ${REPO_ROOT}/.cursor/skills/ instead
  --uninstall   Remove symlinks that point at this repo's skills/
  --force       Replace existing non-symlink or foreign symlinks at target names

Skills source: ${SKILLS_SRC}
EOF
}

TARGET_MODE="user"
UNINSTALL=0
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) TARGET_MODE="project" ;;
    --uninstall) UNINSTALL=1 ;;
    --force) FORCE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

if [[ ! -d "$SKILLS_SRC" ]]; then
  echo "Skills directory not found: $SKILLS_SRC" >&2
  exit 1
fi

if [[ "$TARGET_MODE" == "project" ]]; then
  TARGET_DIR="${REPO_ROOT}/.cursor/skills"
else
  TARGET_DIR="${HOME}/.cursor/skills"
fi

install_one() {
  local name="$1"
  local src="${SKILLS_SRC}/${name}"
  local dest="${TARGET_DIR}/${name}"

  if [[ ! -f "${src}/SKILL.md" ]]; then
    return 0
  fi

  if [[ "$UNINSTALL" == 1 ]]; then
    if [[ -L "$dest" ]]; then
      local link
      link="$(readlink "$dest")"
      if [[ "$link" == "$src" ]] || [[ "$link" == "../../skills/${name}" ]]; then
        rm "$dest"
        echo "Removed $dest"
      fi
    fi
    return 0
  fi

  mkdir -p "$TARGET_DIR"

  if [[ -e "$dest" && ! -L "$dest" ]]; then
    if [[ "$FORCE" != 1 ]]; then
      echo "Skip $dest (exists and is not a symlink; use --force)" >&2
      return 0
    fi
    rm -rf "$dest"
  fi

  if [[ -L "$dest" ]]; then
    local current
    current="$(readlink "$dest")"
    if [[ "$current" == "$src" ]]; then
      echo "Already linked: $dest -> $src"
      return 0
    fi
    if [[ "$FORCE" != 1 ]]; then
      echo "Skip $dest (symlink to $current; use --force)" >&2
      return 0
    fi
    rm "$dest"
  fi

  if [[ "$TARGET_MODE" == "project" ]]; then
    ln -s "../../skills/${name}" "$dest"
    echo "Linked $dest -> ../../skills/${name}"
  else
    ln -s "$src" "$dest"
    echo "Linked $dest -> $src"
  fi
}

if [[ "$UNINSTALL" == 1 ]]; then
  for dir in "$SKILLS_SRC"/*/; do
    [[ -d "$dir" ]] || continue
    install_one "$(basename "$dir")"
  done
  exit 0
fi

count=0
for dir in "$SKILLS_SRC"/*/; do
  [[ -d "$dir" ]] || continue
  name="$(basename "$dir")"
  [[ "$name" == "README.md" ]] && continue
  install_one "$name"
  count=$((count + 1))
done

if [[ "$count" -eq 0 ]]; then
  echo "No skills with SKILL.md found under $SKILLS_SRC" >&2
  exit 1
fi

echo "Installed $count skill(s) under $TARGET_DIR"
