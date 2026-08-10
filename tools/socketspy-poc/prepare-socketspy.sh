#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
OUTPUT_DIR=${OUTPUT_DIR:-"$ROOT_DIR/tools/socketspy-poc/output"}
DEST="$OUTPUT_DIR/socketspy-bin"

mkdir -p "$OUTPUT_DIR"

if [[ -x "$DEST" ]]; then
    printf '%s\n' "$DEST"
    exit 0
fi

if [[ -n "${SOCKETSPY_BIN:-}" && -x "$SOCKETSPY_BIN" ]]; then
    cp "$SOCKETSPY_BIN" "$DEST"
    chmod +x "$DEST"
    printf '%s\n' "$DEST"
    exit 0
fi

if [[ -n "${SOCKETSPY_REPO:-}" ]]; then
    command -v go >/dev/null 2>&1 || {
        printf 'SOCKETSPY_REPO requires Go on PATH.\n' >&2
        exit 1
    }
    (cd "$SOCKETSPY_REPO" && go build -o "$DEST" ./cmd/socketspy)
    printf '%s\n' "$DEST"
    exit 0
fi

if command -v socketspy >/dev/null 2>&1; then
    printf '%s\n' "$(command -v socketspy)"
    exit 0
fi

printf 'SocketSpy is unavailable. Provide one of:\n' >&2
printf '  SOCKETSPY_BIN=/path/to/socketspy %s\n' "$0" >&2
printf '  SOCKETSPY_REPO=/path/to/socketspy %s\n' "$0" >&2
printf '  install socketspy on PATH\n' >&2
exit 1