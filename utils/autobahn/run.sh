#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
SUITE_DIR="$ROOT_DIR/tools/autobahn"
OUTPUT_DIR=${OUTPUT_DIR:-"$SUITE_DIR/reports"}
CONFIG_DIR="$OUTPUT_DIR/config"
PORT=${PORT:-18091}
IMAGE=${AUTOBAHN_IMAGE:-crossbario/autobahn-testsuite:latest}
CONTAINER_NAME=${AUTOBAHN_CONTAINER_NAME:-pocketsocket-autobahn}

mkdir -p "$CONFIG_DIR" "$OUTPUT_DIR"

command -v docker >/dev/null 2>&1 || {
    printf 'Docker is required to run the Autobahn testsuite.\n' >&2
    exit 1
}

sed "s/__PORT__/${PORT}/g" "$SUITE_DIR/fuzzingclient.template.json" \
    > "$CONFIG_DIR/fuzzingclient.json"

cleanup() {
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

printf 'Target: ws://host.docker.internal:%s\n' "$PORT"
printf 'Autobahn image: %s\n' "$IMAGE"
printf 'Reports: %s\n' "$OUTPUT_DIR"

deadline=$((SECONDS + 15))
listening=false
while (( SECONDS < deadline )); do
    if timeout 1 bash -c "</dev/tcp/127.0.0.1/${PORT}" 2>/dev/null; then
        listening=true
        break
    fi
    sleep 0.1
done
if [[ "$listening" != true ]]; then
    printf 'Pocketsocket is not listening on 127.0.0.1:%s. Start it manually before running this suite.\n' "$PORT" >&2
    exit 1
fi

REPORT="$OUTPUT_DIR/index.html"
if docker run --rm --tty --name "$CONTAINER_NAME" \
    --add-host host.docker.internal:host-gateway \
    --env PYTHONUNBUFFERED=1 \
    -v "$CONFIG_DIR:/config:ro" \
    -v "$OUTPUT_DIR:/reports" \
    "$IMAGE" \
    wstest --mode fuzzingclient --spec /config/fuzzingclient.json; then
    STATUS=0
else
    STATUS=$?
fi

if [[ -f "$REPORT" ]]; then
    printf 'Opening report: %s\n' "$REPORT"
    if [[ -n "${BROWSER:-}" ]]; then
        "$BROWSER" "$REPORT" >/dev/null 2>&1 &
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$REPORT" >/dev/null 2>&1 &
    elif command -v open >/dev/null 2>&1; then
        open "$REPORT" >/dev/null 2>&1 &
    elif command -v explorer.exe >/dev/null 2>&1; then
        explorer.exe "$REPORT" >/dev/null 2>&1 &
    else
        printf 'No desktop browser opener found. Open the report manually: %s\n' "$REPORT"
    fi
else
    printf 'Autobahn report not found: %s\n' "$REPORT" >&2
fi

exit "$STATUS"