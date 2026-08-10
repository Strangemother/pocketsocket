#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
OUTPUT_DIR=${OUTPUT_DIR:-"$ROOT_DIR/tools/socketspy-poc/output"}
PORT=${PORT:-18090}
TARGET=${TARGET:-"ws://127.0.0.1:${PORT}/ws/"}
MUTATIONS=${MUTATIONS:-4}
RESPONSE_TIMEOUT_MS=${RESPONSE_TIMEOUT_MS:-150}

mkdir -p "$OUTPUT_DIR"

find_cli() {
    local candidate
    for candidate in \
        "${POCKETSOCKET_CLI:-}" \
        "$ROOT_DIR/dist/pocketsocket-cli" \
        "$ROOT_DIR/dist/pocketsocket-cli-linux_amd64" \
        "$ROOT_DIR/dist/pocketsocket-cli.exe"; do
        if [[ -n "$candidate" && -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    printf 'No executable Pocketsocket CLI found under dist/.\n' >&2
    printf 'Build one with: (cd server && nimble build)\n' >&2
    exit 1
}

build_socketspy_command() {
    SOCKETSPY_CMD=("$ROOT_DIR/tools/socketspy-poc/prepare-socketspy.sh")
    SOCKETSPY_CMD=("$(${SOCKETSPY_CMD[0]})")
}

wait_for_port() {
    local deadline=$((SECONDS + 10))
    while (( SECONDS < deadline )); do
        if timeout 1 bash -c "</dev/tcp/127.0.0.1/${PORT}" 2>/dev/null; then
            return 0
        fi
        sleep 0.1
    done
    printf 'Pocketsocket did not listen on 127.0.0.1:%s.\n' "$PORT" >&2
    return 1
}

CLI=$(find_cli)
build_socketspy_command

SERVER_LOG="$OUTPUT_DIR/pocketsocket.log"
RUN_METADATA="$OUTPUT_DIR/run.txt"
: > "$SERVER_LOG"

cleanup() {
    if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

printf 'Pocketsocket CLI: %s\n' "$CLI" | tee "$RUN_METADATA"
printf 'SocketSpy command: %q ' "${SOCKETSPY_CMD[@]}" >> "$RUN_METADATA"
printf '\nTarget: %s\nMutations: %s\n\n' "$TARGET" "$MUTATIONS" >> "$RUN_METADATA"

"$CLI" --run --echo --print --template-dir "$ROOT_DIR/server/templates" \
    --address 127.0.0.1 --port "$PORT" \
    --max-message 65536 >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!
wait_for_port

formats=(text json html sarif junit)
for format in "${formats[@]}"; do
    case "$format" in
        text) extension=txt ;;
        json) extension=json ;;
        html) extension=html ;;
        sarif) extension=sarif ;;
        junit) extension=xml ;;
    esac

    output="$OUTPUT_DIR/fuzz-${format}.${extension}"
    printf 'Generating %s report: %s\n' "$format" "$output"
    set +e
    timeout 90 "${SOCKETSPY_CMD[@]}" fuzz \
        --target "$TARGET" \
        --mutations "$MUTATIONS" \
        --response-timeout "$RESPONSE_TIMEOUT_MS" \
        --format "$format" \
        --output "$output" \
        --quiet \
        --no-color
    status=$?
    set -e

    if (( status == 1 || status >= 124 )); then
        printf 'SocketSpy failed for %s (exit %s).\n' "$format" "$status" >&2
        exit "$status"
    fi
    if (( status == 2 )); then
        printf 'SocketSpy reported findings for %s; retaining the report.\n' "$format"
    fi
done

printf '\nReports written to %s\n' "$OUTPUT_DIR"
find "$OUTPUT_DIR" -maxdepth 1 -type f -printf '  %f (%s bytes)\n' | sort