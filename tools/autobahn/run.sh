#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
SUITE_DIR="$ROOT_DIR/tools/autobahn"
OUTPUT_DIR=${OUTPUT_DIR:-"$SUITE_DIR/reports"}
CONFIG_DIR="$OUTPUT_DIR/config"
PORT=${PORT:-18091}
IMAGE=${AUTOBAHN_IMAGE:-crossbario/autobahn-testsuite:25.10.1}
CONTAINER_NAME=${AUTOBAHN_CONTAINER_NAME:-pocketsocket-autobahn}
CLI=${POCKETSOCKET_CLI:-$ROOT_DIR/dist/pocketsocket-cli}
SERVER_LOG="$OUTPUT_DIR/pocketsocket.log"

mkdir -p "$CONFIG_DIR" "$OUTPUT_DIR"

if [[ ! -x "$CLI" ]]; then
    printf 'Compiled Pocketsocket CLI not found or not executable: %s\n' "$CLI" >&2
    printf 'Build it first with: (cd server && nimble build)\n' >&2
    exit 1
fi
command -v docker >/dev/null 2>&1 || {
    printf 'Docker is required to run the Autobahn testsuite.\n' >&2
    exit 1
}

sed "s/__PORT__/${PORT}/g" "$SUITE_DIR/fuzzingclient.template.json" \
    > "$CONFIG_DIR/fuzzingclient.json"

cleanup() {
    if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

printf 'Pocketsocket CLI: %s\n' "$CLI"
printf 'Target: ws://host.docker.internal:%s\n' "$PORT"
printf 'Autobahn image: %s\n' "$IMAGE"
printf 'Reports: %s\n' "$OUTPUT_DIR"

"$CLI" --run --print --template-dir "$ROOT_DIR/server/templates" \
    --address 0.0.0.0 --port "$PORT" --max-message 65536 \
    >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

deadline=$((SECONDS + 15))
listening=false
while (( SECONDS < deadline )); do
    if timeout 1 bash -c "</dev/tcp/127.0.0.1/${PORT}" 2>/dev/null; then
        listening=true
        break
    fi
    sleep 0.1
done
if [[ "$listening" != true ]] || ! kill -0 "$SERVER_PID" 2>/dev/null; then
    printf 'Pocketsocket exited before listening. See %s\n' "$SERVER_LOG" >&2
    exit 1
fi

docker run --rm --name "$CONTAINER_NAME" \
    --add-host host.docker.internal:host-gateway \
    -v "$CONFIG_DIR:/config:ro" \
    -v "$OUTPUT_DIR:/reports" \
    "$IMAGE" \
    wstest --mode fuzzingclient --spec /config/fuzzingclient.json