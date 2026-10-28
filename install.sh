#!/bin/sh
set -eu

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ is required")'
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
target_dir=${PREFIX:-"$HOME/.local"}/bin
mkdir -p "$target_dir"
install -m 755 "$source_dir/codex-account" "$target_dir/codex-account"
printf 'Installed: %s/codex-account\n' "$target_dir"
printf 'Run: codex-account --help\n'
