#!/bin/zsh
cd -- "${0:A:h}"
set -e

if [[ ! -x restricted_companion/.venv/bin/python ]]; then
  display_python=''
  for candidate in /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 13) else 1)' 2>/dev/null; then
      display_python="$candidate"
      break
    fi
  done
  if [[ -z "$display_python" ]]; then
    print 'Install Python 3.13 on this Mac, then run this launcher again.'
    read 'reply?Press Return to close.'
    exit 1
  fi
  "$display_python" -m venv restricted_companion/.venv
fi

if [[ -z "${CODEX_BIN:-}" ]]; then
  if command -v codex >/dev/null 2>&1; then
    export CODEX_BIN="$(command -v codex)"
  else
    for apps_dir in /Applications "$HOME/Applications"; do
      for binary in "$apps_dir/Codex.app/Contents/Resources/codex" "$apps_dir/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex" "$apps_dir/ChatGPT.app/Contents/Resources/codex"; do
        if [[ -x "$binary" ]]; then
          export CODEX_BIN="$binary"
          break 2
        fi
      done
    done
  fi
fi
if [[ -z "${CODEX_BIN:-}" ]]; then
  print 'Codex CLI was not found. Install/sign in to Codex on this Mac, or set CODEX_BIN to its executable path.'
  read 'reply?Press Return to close.'
  exit 1
fi

restricted_companion/.venv/bin/python -m pip --disable-pip-version-check install --no-cache-dir --no-index --find-links runtime-wheels --only-binary=:all: --require-hashes -r restricted-requirements.txt

print 'Keep this Terminal window open for live usage updates. Press Control-C to stop.'
exec restricted_companion/.venv/bin/python -m restricted_companion "$@"
